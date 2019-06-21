"""A set of tasks to help upgrade Satellite and Capsule.

Many commands are affected by environment variables. Unless stated otherwise,
all environment variables are required.
"""
import os
import sys
import time
import requests
import socket

from automation_tools import (
    setup_alternate_capsule_ports,
    setup_fake_manifest_certificate,
)
from automation_tools import setup_foreman_discovery, setup_avahi_discovery
from automation_tools.repository import enable_repos
from automation_tools.utils import get_discovery_image
from nailgun import entities
from robozilla.decorators import bz_bug_is_open
from upgrade.helpers.constants import customcontents, rhelcontents
from upgrade.helpers.docker import (
    attach_subscription_to_host_from_content_host
)
from upgrade.helpers.logger import logger
from upgrade.helpers.tools import call_entity_method_with_timeout
from fabric.api import env, execute, put, run, warn_only
if sys.version_info[0] == 2:
    from StringIO import StringIO  # (import-error) pylint:disable=F0401
else:  # pylint:disable=F0401,E0611
    from io import StringIO

logger = logger()


class ProductNotFound(Exception):
    """Raise if the product you are searching is not found"""


def check_necessary_env_variables_for_upgrade(product):
    """Checks if necessary Environment Variables are provided

    :param string product: The product name to upgrade
    """
    failure = []
    # The upgrade product
    products = ['satellite', 'capsule', 'client', 'longrun', 'n-1']
    if product not in products:
        failure.append('Product name should be one of {0}.'.format(
            ', '.join(products)))
    # Check If OS is set for creating an instance name in rhevm
    if not os.environ.get('OS'):
        failure.append('Please provide OS version as rhel7 or rhel6, '
                       'And retry !')
    if failure:
        logger.warning('Cannot Proceed Upgrade as:')
        for msg in failure:
            logger.warning(msg)
        sys.exit(1)
    return True


def sync_capsule_repos_to_upgrade(capsules):
    """This syncs capsule repo in Satellite server and also attaches
    the capsule repo subscription to each capsule

    :param list capsules: The list of capsule hostnames to which new capsule
    repo subscription will be attached

    Following environment variable affects this function:

    CAPSULE_URL
        The url for capsule repo from latest satellite compose.
        If not provided, capsule repo from Red Hat repositories will be enabled
    TOOLS_URL_RHEL{}.format(os_ver)
        The url for capsuletools repo from latest satellite compose.
        If not provided, capsule repo from Red Hat repositories will be enabled
    FROM_VERSION
        Current Satellite version - to differentiate default organization.
        e.g. '6.1', '6.0'
    TO_VERSION
        Upgradable Satellite version - To enable capsule repo
        e.g '6.1', '6.2'
    OS
        OS version to enable next version capsule repo
        e.g 'rhel7', 'rhel6'

    Personal Upgrade Env Vars:

    CAPSULE_AK
        The AK name used in capsule subscription

    RHEV upgrade Env Vars:

    RHEV_CAPSULE_AK
        The AK name used in capsule subscription
    """
    command = "foreman-maintain health check --label " \
              "foreman-tasks-not-running -y"
    check_status_of_running_task(command, 3)
    logger.info('Syncing latest capsule repos in Satellite ...')
    to_version = os.environ.get('TO_VERSION')
    os_ver = os.environ.get('OS')[-1]
    capsule_repo = os.environ.get('CAPSULE_URL')
    capsuletools_url = os.environ.get('TOOLS_URL_RHEL{}'.format(os_ver))
    ak_name = os.environ.get(
        'CAPSULE_AK', os.environ.get('RHEV_CAPSULE_AK'))
    if ak_name is None:
        logger.warning(
            'The AK name is not provided for Capsule upgrade! Aborting...')
        sys.exit(1)
    org = entities.Organization(id=1).read()
    ak = entities.ActivationKey(organization=org).search(
        query={'search': 'name={}'.format(ak_name)})[0]
    cv = ak.content_view.read()
    lenv = ak.environment.read()
    # Fix dead pulp tasks
    if os_ver == '6':
        run('for i in pulp_resource_manager pulp_workers pulp_celerybeat; '
            'do service $i restart; done')
    _sync_capsule_subscription_to_capsule_ak(ak)
    if float(to_version) >= 6.3:
        _add_additional_subscription_for_capsule(ak, capsuletools_url)
    # Publishing and promoting the CV with all newly added capsule, capsuletools, rhscl and
    # server repos combine
    call_entity_method_with_timeout(cv.read().publish, timeout=2000)
    published_ver = entities.ContentViewVersion(
        id=max([cv_ver.id for cv_ver in cv.read().version])).read()
    published_ver.promote(data={'environment_id': lenv.id, 'force': False})
    # Add capsule and tools custom prod subscription to capsules
    if capsule_repo:
        add_custom_product_subscription_to_hosts(
            customcontents['capsule']['prod'], capsules)
    if float(to_version) >= 6.3:
        if capsuletools_url:
            add_custom_product_subscription_to_hosts(
                customcontents['capsule_tools']['prod'], capsules)


def _sync_capsule_subscription_to_capsule_ak(ak):
    """Syncs to_version capsule contents, adds to the CV and attaches contents to the AK through
    which Capsule is registered

    :param ak: ```nailgun.entities.ActivationKey``` used for capsule subscription
    """
    cv = ak.content_view.read()
    org = ak.organization
    capsule_repo = os.environ.get('CAPSULE_URL')
    to_version = os.environ.get('TO_VERSION')
    os_ver = os.environ.get('OS')[-1]
    # If custom capsule repo is not given then
    # enable capsule repo from Redhat Repositories
    if capsule_repo:
        cap_product = entities.Product(
            name=customcontents['capsule']['prod'], organization=org).create()
        cap_repo = entities.Repository(
            name=customcontents['capsule']['repo'], product=cap_product, url=capsule_repo,
            organization=org, content_type='yum').create()
    else:
        cap_product = entities.Product(
            name=rhelcontents['capsule']['prod'],
            organization=org
        ).search(query={'per_page': 100})[0]
        cap_reposet = entities.RepositorySet(
            name=rhelcontents['capsule']['repo'].format(cap_ver=to_version, os_ver=os_ver),
            product=cap_product
        ).search()[0]
        try:
            cap_reposet.enable(
                data={'basearch': 'x86_64', 'releasever': '7Server', 'organization_id': org.id})
        except requests.exceptions.HTTPError as exp:
            logger.warn(exp)
        cap_repo = entities.Repository(
            name=rhelcontents['capsule']['repofull'].format(
                cap_ver=to_version, os_ver=os_ver, arch='x86_64')
        ).search(query={'organization_id': org.id, 'per_page': 100})[0]
    call_entity_method_with_timeout(entities.Repository(id=cap_repo.id).sync, timeout=2500)
    # Add repos to CV
    cv.repository += [cap_repo]
    cv.update(['repository'])
    ak = ak.read()
    if capsule_repo:
        cap_sub = entities.Subscription().search(
            query={'search': 'name={0}'.format(customcontents['capsule']['prod'])})[0]
        ak.add_subscriptions(data={
            'quantity': 1,
            'subscription_id': cap_sub.id,
        })
    else:
        ak.content_override(
            data={
                'content_override': {
                    'content_label': rhelcontents['capsule']['label'].format(
                        cap_ver=to_version, os_ver=os_ver),
                    'value': '1'}
            }
        )


def _sync_rh_repos_to_satellite(org):
    """Task to sync Redhat Repositories to latest required during upgrade

    :param org: ```nailgun.entities.Organization``` entity of capsule
    :returns tuple: RHSCL and Redhat 7 Server repo name, label name and
        product name
    """
    rhelver = '7'
    arch = 'x86_64'
    # Enable rhscl repository
    scl_product = entities.Product(
        name=rhelcontents['rhscl_sat64']['prod'], organization=org
    ).search(query={'per_page': 100})[0]
    scl_reposet = entities.RepositorySet(
        name=rhelcontents['rhscl']['repo'].format(os_ver=rhelver), product=scl_product
    ).search()[0]
    try:
        scl_reposet.enable(
            data={'basearch': arch, 'releasever': '7Server', 'organization_id': org.id})
    except requests.exceptions.HTTPError as exp:
        logger.warn(exp)
    time.sleep(20)
    # Sync enabled Repo from cdn
    scl_repo = entities.Repository(
        name=rhelcontents['rhscl']['repofull'].format(os_ver=rhelver, arch=arch)
    ).search(query={'organization_id': org.id, 'per_page': 100})[0]
    call_entity_method_with_timeout(entities.Repository(id=scl_repo.id).sync, timeout=2500)
    # Enable RHEL 7 Server repository
    server_product = entities.Product(
        name=rhelcontents['server']['prod'], organization=org).search(query={'per_page': 100})[0]
    server_reposet = entities.RepositorySet(
        name=rhelcontents['server']['repo'].format(os_ver=rhelver), product=server_product
    ).search()[0]
    try:
        server_reposet.enable(
            data={'basearch': arch, 'releasever': '7Server', 'organization_id': org.id})
    except requests.exceptions.HTTPError as exp:
        logger.warn(exp)
    time.sleep(20)
    # Sync enabled Repo from cdn
    server_repo = entities.Repository(
        name=rhelcontents['server']['repofull'].format(os_ver=rhelver, arch=arch)
    ).search(query={'organization_id': org.id, 'per_page': 100})[0]
    call_entity_method_with_timeout(entities.Repository(id=server_repo.id).sync, timeout=3600)
    scl_repo.repo_id = rhelcontents['rhscl']['label'].format(os_ver=rhelver)
    server_repo.repo_id = rhelcontents['server']['label'].format(os_ver=rhelver)
    return scl_repo, server_repo


def _sync_sattools_repos_to_satellite_for_capsule(capsuletools_url, org):
    """Creates custom / Enables RH Tools repo on satellite and syncs for capsule upgrade

    :param str capsuletools_url: The capsule tools repo url
    :param org: ```nailgun.entities.Organization``` entity of capsule

    :returns: ```nailgun.entities.repository``` entity for capsule
    """
    to_ver = os.environ.get('TO_VERSION')
    rhelver = '7'
    arch = 'x86_64'
    if capsuletools_url:
        captools_product = entities.Product(
            name=customcontents['capsule_tools']['prod'], organization=org).create()
        captools_repo = entities.Repository(
            name=customcontents['capsule_tools']['repo'],
            product=captools_product, url=capsuletools_url, organization=org, content_type='yum'
        ).create()
    else:
        captools_product = entities.Product(
            name=rhelcontents['tools']['prod'], organization=org
        ).search(query={'per_page': 100})[0]
        cap_reposet = entities.RepositorySet(
            name=rhelcontents['tools']['repo'].format(sat_ver=to_ver, os_ver=rhelver),
            product=captools_product).search()[0]
        try:
            cap_reposet.enable(data={'basearch': arch, 'organization_id': org.id})
        except requests.exceptions.HTTPError as exp:
            logger.warn(exp)
        time.sleep(5)
        captools_repo = entities.Repository(
            name=rhelcontents['tools']['repofull'].format(
                sat_ver=to_ver, os_ver=rhelver, arch=arch)
        ).search(query={'organization_id': org.id, 'per_page': 100})[0]
    call_entity_method_with_timeout(entities.Repository(id=captools_repo.id).sync, timeout=2500)
    captools_repo.repo_id = rhelcontents['tools']['label'].format(
        os_ver=rhelver, sat_ver=to_ver)
    return captools_repo


def _add_additional_subscription_for_capsule(ak, capsuletools_url):
    """Adds rhscl, rhel server and tools subscription to capsule ak

    Required only for satellite version 6.3 and higher

    :param ak: ```nailgun.entities.ActivationKey``` of capsule
    :param capsuletools_repo: If None then enables redhat tools repo else,
        creates custom repo with this url
    """
    cv = ak.content_view.read()
    org = ak.organization
    scl_repo, server_repo = _sync_rh_repos_to_satellite(org)
    captools_repo = _sync_sattools_repos_to_satellite_for_capsule(capsuletools_url, org)
    cv.repository += [scl_repo, server_repo, captools_repo]
    cv.update(['repository'])
    ak = ak.read()
    ak.content_override(
        data={'content_override': {'content_label': scl_repo.repo_id, 'value': '1'}}
    )
    ak.content_override(
        data={'content_override': {'content_label': server_repo.repo_id, 'value': '1'}}
    )
    if not capsuletools_url:
        ak.content_override(
            data={
                'content_override': {'content_label': captools_repo.repo_id, 'value': '1'}
            })
    else:
        captools_sub = entities.Subscription().search(
            query={'search': 'name={0}'.format(customcontents['capsule_tools']['prod'])})[0]
        ak.add_subscriptions(data={
            'quantity': 1,
            'subscription_id': captools_sub.id,
        })


def sync_tools_repos_to_upgrade(client_os, hosts):
    """This syncs tools repo in Satellite server and also attaches
    the new tools repo subscription onto each client

    :param string client_os: The client OS of which tools repo to be synced
        e.g: rhel6, rhel7
    :param list hosts: The list of capsule hostnames to which new capsule
        repo subscription will be attached

    Following environment variable affects this function:

    TOOLS_URL_{client_os}
        The url of tools repo from latest satellite compose.
    FROM_VERSION
        Current Satellite version - to differentiate default organization.
        e.g. '6.1', '6.0'

    Personal Upgrade Env Vars:

    CLIENT_AK
        The ak_name attached to subscription of client

    Rhevm upgrade Env Vars:

    RHEV_CLIENT_AK
        The AK name used in client subscription
    """
    client_os = client_os.upper()
    tools_repo_url = os.environ.get('TOOLS_URL_{}'.format(client_os))
    if tools_repo_url is None:
        logger.warning('The Tools Repo URL for {} is not provided '
                       'to perform Client Upgrade !'.format(client_os))
        sys.exit(1)
    ak_name = os.environ.get(
        'CLIENT_AK_{}'.format(client_os),
        os.environ.get('RHEV_CLIENT_AK_{}'.format(client_os))
    )
    if ak_name is None:
        logger.warning('The AK details are not provided for {0} Client '
                       'upgrade!'.format(client_os))
        sys.exit(1)
    org = entities.Organization(id=1).read()
    ak = entities.ActivationKey(organization=org).search(
        query={'search': 'name={}'.format(ak_name)})[0]
    cv = ak.content_view.read()
    lenv = ak.environment.read()
    toolsproduct_name = customcontents['tools']['prod'].format(client_os=client_os)
    toolsrepo_name = customcontents['tools']['repo'].format(client_os=client_os)
    # adding sleeps in between to avoid race conditions
    tools_product = entities.Product(name=toolsproduct_name, organization=org).create()
    tools_repo = entities.Repository(
        name=toolsrepo_name, product=tools_product, url=tools_repo_url,
        organization=org, content_type='yum').create()
    entities.Repository(id=tools_repo.id).sync()
    cv.repository += [tools_repo]
    cv.update(['repository'])
    call_entity_method_with_timeout(cv.read().publish, timeout=2500)
    published_ver = entities.ContentViewVersion(
        id=max([cv_ver.id for cv_ver in cv.read().version])).read()
    published_ver.promote(data={'environment_id': lenv.id, 'force': False})
    tools_sub = entities.Subscription().search(
        query={'search': 'name={0}'.format(toolsproduct_name)})[0]
    ak.add_subscriptions(data={
        'quantity': 1,
        'subscription_id': tools_sub.id,
    })
    # Add this latest tools repo to hosts to upgrade
    sub = entities.Subscription().search(
        query={'search': 'name={0}'.format(toolsproduct_name)})[0]
    for host in hosts:
        if float(os.environ.get('FROM_VERSION')) <= 6.1:
            # If not User Hosts then, attach sub to dockered clients
            if not all([
                os.environ.get('CLIENT6_HOSTS'),
                os.environ.get('CLIENT7_HOSTS')
            ]):
                docker_vm = os.environ.get('DOCKER_VM')
                execute(
                    attach_subscription_to_host_from_content_host,
                    sub.cp_id,
                    True,
                    host,
                    host=docker_vm)
            # Else, Attach subs to user hosts
            else:
                execute(
                    attach_subscription_to_host_from_content_host,
                    sub.cp_id,
                    host=host)
        else:
            host = entities.Host().search(query={'search': 'name={}'.format(host)})[0]
            entities.HostSubscription(host=host).add_subscriptions(
                data={'subscriptions': [{'id': sub.id, 'quantity': 1}]})


def post_upgrade_test_tasks(sat_host, cap_host=None):
    """Run set of tasks for post upgrade tests

    :param string sat_host: Hostname to run the tasks on
    :param list cap_host: Capsule hosts to run sync on
    """
    # Execute tasks as post upgrade tests are dependent
    certificate_url = os.environ.get('FAKE_MANIFEST_CERT_URL')
    if certificate_url is not None:
        execute(
            setup_fake_manifest_certificate,
            certificate_url,
            host=sat_host
        )
    sat_version = os.environ.get('TO_VERSION')
    execute(setup_alternate_capsule_ports, host=sat_host)
    if float(sat_version) > 6.1:
        # Update the Default Organization name, which was updated in 6.2
        logger.info("Update the Default Organization name, which was updated "
                    "in 6.2")
        org = entities.Organization().search(query={'search': 'label=Default_Organization'})[0]
        org.name = "Default Organization"
        org.update(['name'])
        # Update the Default Location name, which was updated in 6.2
        logger.info("Update the Default Location name, which was updated in "
                    "6.2")
        loc = entities.Location().search(query={'search': 'name="Default Location"'})[0]
        loc.name = "Default Location"
        loc.update(['name'])
        if bz_bug_is_open(1502505):
            logger.info(
                "Update the default_location_puppet_content value with "
                "updated location name.Refer BZ:1502505")
            puppet_location = entities.Setting().search(
                query={'search': 'name=default_location_puppet_content'}
            )[0]
            puppet_location.value = 'Default Location'
            puppet_location.update(['value'])
    # Increase log level to DEBUG, to get better logs in foreman_debug
    execute(lambda: run('sed -i -e \'/:level: / s/: .*/: '
                        'debug/\' /etc/foreman/settings.yaml'), host=sat_host)
    execute(lambda: run('katello-service restart'), host=sat_host)
    # Execute task for template changes required for discovery feature
    execute(
        setup_foreman_discovery,
        sat_version=sat_version,
        host=sat_host
    )
    # Execute task for creating latest discovery iso required for unattended
    #  test
    env.disable_known_hosts = True
    execute(
        get_discovery_image,
        host=os.environ.get('LIBVIRT_HOSTNAME')
    )
    # Commenting out until GH issue:#135
    # Removing the original manifest from Default Organization (Org-id 1),
    # to allow test-cases to utilize the same manifest.
    # logger.info("Removing the Original Manifest from Default Organization")
    # execute(hammer, 'subscription delete-manifest --organization-id 1',
    #         host=sat_host)

    # Run Avahi Task on upgrade boxes for REX tests to run
    execute(lambda: run('yum remove -y epel*'), host=sat_host)
    execute(setup_avahi_discovery, host=sat_host)


def capsule_sync(cap_host):
    """Run Capsule Sync as a part of job

    :param list cap_host: List of capsules to perform sync
    """
    capsule = entities.SmartProxy().search(
        query={'search': 'name={}'.format(cap_host)})[0]
    if float(os.environ.get('TO_VERSION')) >= 6.2:
        logger.info('Refreshing features for capsule host {0}'.
                    format(cap_host))
        capsule.refresh()
    logger.info('Running Capsule sync for capsule host {0}'.
                format(cap_host))
    capsule = entities.Capsule().search(
        query={'search': 'name={}'.format(cap_host)})[0]
    capsule.content_sync()


def katello_restart():
    """Restarts the katello services"""
    services = run('katello-service restart')
    if services.return_code > 0:
        logger.error('Unable to re-start the Satellite Services')
        sys.exit(1)


def check_ntpd():
    """Check if ntpd is running else start the service"""
    ntpd_check = run("service ntpd status", warn_only=True)
    if ntpd_check.return_code > 0:
        run("service ntpd start")
        run("chkconfig ntpd on")


def setup_foreman_maintain():
    """Task which install foreman-maintain tool.

    Environment Variables necessary to proceed Setup:
    -----------------------------------------------------

    DISTRIBUTION
        The satellite upgrade using internal or CDN distribution.
        e.g 'CDN','DOWNSTREAM'

    MAINTAIN_REPO
        URL of repo if distribution is DOWNSTREAM

    BASE_URL
        URL for the compose repository if distribution is DOWNSTREAM

    TOOLS_RHEL7
        URL for the satellite tools repo if distribution is DOWNSTREAM
    """
    env.disable_known_hosts = True
    # setting up foreman-maintain repo
    setup_foreman_maintain_repo()
    if os.environ.get('DISTRIBUTION') != 'CDN':
        # Add Sat6 repo from latest compose
        satellite_repo = StringIO()
        satellite_repo.write('[sat6]\n')
        satellite_repo.write('name=satellite 6\n')
        satellite_repo.write('baseurl={0}\n'.format(
            os.environ.get('BASE_URL')
        ))
        satellite_repo.write('enabled=1\n')
        satellite_repo.write('gpgcheck=0\n')
        put(local_path=satellite_repo,
            remote_path='/etc/yum.repos.d/sat6.repo')
        satellite_repo.close()
        # Add sattools repo from latest compose
        tools_repo = StringIO()
        tools_repo.write('[sat6tools7]\n')
        tools_repo.write('name=satellite6-tools7\n')
        tools_repo.write('baseurl={0}\n'.format(
            os.environ.get('TOOLS_RHEL7')
        ))
        tools_repo.write('enabled=1\n')
        tools_repo.write('gpgcheck=0\n')
        put(local_path=tools_repo,
            remote_path='/etc/yum.repos.d/sat6tools7.repo')
        tools_repo.close()
    # repolist
    run('yum repolist')
    # install foreman-maintain
    run('yum install rubygem-foreman_maintain -y')


def setup_foreman_maintain_repo():
    """Task which setup repo for foreman-maintain.

    Environment Variables necessary to proceed Setup:
    -----------------------------------------------------

    DISTRIBUTION
        The satellite upgrade using internal or CDN distribution.
        e.g 'CDN','DOWNSTREAM'

    MAINTAIN_REPO
        URL of repo if distribution is DOWNSTREAM
    """
    # setting up foreman-maintain repo
    if os.environ.get('DISTRIBUTION') == 'CDN':
        enable_repos('rhel-7-server-satellite-maintenance-6-rpms')
    else:
        maintain_repo = StringIO()
        maintain_repo.write('[foreman-maintain]\n')
        maintain_repo.write('name=foreman-maintain\n')
        maintain_repo.write('baseurl={0}\n'.format(
            os.environ.get('MAINTAIN_REPO')
        ))
        maintain_repo.write('enabled=1\n')
        maintain_repo.write('gpgcheck=0\n')
        put(local_path=maintain_repo,
            remote_path='/etc/yum.repos.d/foreman-maintain.repo')
        maintain_repo.close()


def upgrade_using_foreman_maintain():
    """Task which upgrades the product using foreman-maintain tool.

    Environment Variables necessary to proceed Upgrade:
    -----------------------------------------------------
    FROM_VERSION
        Current satellite version which will be upgraded to latest version

    TO_VERSION
        To which Satellite version to upgrade.
        e.g '6.2','6.3'
    """
    env.disable_known_hosts = True
    # setup hammer config
    if os.environ.get('FROM_VERSION') != "6.3":
        run('mkdir -p /root/.hammer/cli.modules.d')
        hammer_file = StringIO()
        hammer_file.write('--- \n')
        hammer_file.write(' :foreman: \n')
        hammer_file.write('  :username: admin\n')
        hammer_file.write('  :password: changeme \n')
        put(local_path=hammer_file,
            remote_path='/root/.hammer/cli.modules.d/foreman.yml')
        hammer_file.close()

    with warn_only():
        if os.environ.get('FROM_VERSION') == os.environ.get('TO_VERSION'):
            # z stream upgrade
            run('foreman-maintain upgrade check --target-version {}'
                ' -y'.format(os.environ.get('TO_VERSION') + ".z"))
        else:
            run('foreman-maintain upgrade check --target-version {}'
                ' -y'.format(os.environ.get('TO_VERSION')))

    # whitelist disk-performance check
    if os.environ.get('FROM_VERSION') == os.environ.get('TO_VERSION'):
        # z stream upgrade
        run('foreman-maintain upgrade run '
            '--whitelist="disk-performance" '
            '--target-version {} '
            '-y'.format(os.environ.get('TO_VERSION') + ".z"))
    else:
        run('foreman-maintain upgrade run '
            '--whitelist="disk-performance" '
            '--target-version {} -y'.format(os.environ.get('TO_VERSION')))


def upgrade_puppet3_to_puppet4():
    """Task which upgrade satellite 6.3 from puppet3 to puppet4.

    Environment Variables necessary to proceed Setup:
    -----------------------------------------------------

    DISTRIBUTION
        The satellite upgrade using internal or CDN distribution.
        e.g 'CDN','DOWNSTREAM'

    PUPPET4_REPO
        URL of puppet4 repo if distribution is DOWNSTREAM
    """
    env.disable_known_hosts = True
    # setting up puppet4 repo
    if os.environ.get('DISTRIBUTION') == 'CDN':
        enable_repos('rhel-7-server-satellite-6.3-puppet4-rpms')
    else:
        satellite_repo = StringIO()
        satellite_repo.write('[Puppet4]\n')
        satellite_repo.write('name=puppet4\n')
        satellite_repo.write('baseurl={0}\n'.format(
            os.environ.get('PUPPET4_REPO')
        ))
        satellite_repo.write('enabled=1\n')
        satellite_repo.write('gpgcheck=0\n')
        put(local_path=satellite_repo,
            remote_path='/etc/yum.repos.d/puppet4.repo')
        satellite_repo.close()

    # repolist
    run('yum repolist')
    # upgrade puppet
    run('satellite-installer --upgrade-puppet')


def get_osp_hostname(ipaddr):
    """The openstack has floating ip and we need to fetch the hostname from DNS
    :param ipaddr : IP address of the osp box
    """
    try:
        return socket.gethostbyaddr(ipaddr)[0]
    except Exception as ex:
        logger.error(ex)


def add_baseOS_repo(base_url):
    """This adds the latest repo to the host to fetch latest available packages

    :param base_url: Url of the latest baseos repo to be added.
    """
    rhel_repo = StringIO()
    rhel_repo.write('[rhel]\n')
    rhel_repo.write('name=rhel\n')
    rhel_repo.write('baseurl={0}\n'.format(base_url))
    rhel_repo.write('enabled=1\n')
    rhel_repo.write('gpgcheck=0\n')
    put(local_path=rhel_repo,
        remote_path='/etc/yum.repos.d/rhel.repo')
    rhel_repo.close()


def setup_satellite_clone():
    """Task which install satellite-clone tool.

    Environment Variables necessary to proceed Setup:
    -----------------------------------------------------

    DISTRIBUTION
        The satellite upgrade using internal or CDN distribution.
        e.g 'CDN','DOWNSTREAM'

    MAINTAIN_REPO
        URL of repo if distribution is DOWNSTREAM

    BASE_URL
        URL for the compose repository if distribution is DOWNSTREAM
    """
    env.disable_known_hosts = True
    # setting up foreman-maintain repo
    if os.environ.get('DISTRIBUTION') == 'CDN':
        enable_repos('rhel-7-server-satellite-maintenance-6-rpms')
    else:
        satellite_repo = StringIO()
        satellite_repo.write('[maintainrepo]\n')
        satellite_repo.write('name=maintain\n')
        satellite_repo.write('baseurl={0}\n'.format(
            os.environ.get('MAINTAIN_REPO')
        ))
        satellite_repo.write('enabled=1\n')
        satellite_repo.write('gpgcheck=0\n')
        put(local_path=satellite_repo,
            remote_path='/etc/yum.repos.d/maintain.repo')
        satellite_repo.close()

    # repolist
    run('yum repolist')
    # install foreman-maintain
    run('yum install satellite-clone -y')


def puppet_autosign_hosts(version, hosts, append=True):
    """Appends host entries to puppet autosign conf file

    :param str version: The current satellite version
    :param list hosts: The list of hosts to be added for autoconf
    :param bool append: Whether to add or append
    """
    append = '>>' if append else '>'
    puppetver = 'ver1' if version in ['6.1', '6.2'] else 'ver2'
    puppetfile = {
        'ver1': '/etc/puppet/autosign.conf',
        'ver2': '/etc/puppetlabs/puppet/autosign.conf'}
    for host in hosts:
        run('echo "{0}" {1} {2}'.format(host, append, puppetfile[puppetver]))


def get_satellite_host():
    """Get the satellite hostname depending on which jenkins variables are set

    :return string : Returns the satellite hostname

    Environment Variable:

    RHEV_SAT_HOST
        This is set, if we are using internal RHEV Templates and VM for
        upgrade.
    SATELLITE_HOSTNAME
        This is set, in case user provides his personal satellite for
        upgrade.
        """
    return os.environ.get(
        'RHEV_SAT_HOST',
        os.environ.get('SATELLITE_HOSTNAME')
    )


def wait_untill_capsule_sync(capsule):
    """The polling function that waits for capsule sync task to finish

    :param capsule: A capsule hostname
    """
    cap = entities.Capsule().search(
        query={'search': 'name={}'.format(capsule)})[0]
    active_tasks = cap.content_get_sync()['active_sync_tasks']
    if len(active_tasks) >= 1:
        logger.info(
            'Wait for background capsule sync to finish on '
            'capsule: {}'.format(cap.name))
        for task in active_tasks:
            entities.ForemanTask(id=task['id']).poll(timeout=2700)


def pre_upgrade_system_checks(capsules):
    """The preupgrade system checks necessary for smooth upgrade experience

    :param capsules: The list of capsules
    """
    # Check and wait if the capsule sync task is running before upgrade
    if capsules:
        for capsule in capsules:
            wait_untill_capsule_sync(capsule)


def generate_custom_certs():
    """ Task to generate custom certs for satellite
    Environment Variable:
    SERVER_HOSTNAME
        The satellite server hostname
    """
    certs_script = StringIO()
    certs_script.write(
        "#! /bin/bash\n"
        "name={hostname}\n"
        "mkdir ownca\n"
        "pushd ownca\n"
        "wget https://raw.githubusercontent.com/ntkathole/ownca/master/openssl.cnf\n"
        "wget https://raw.githubusercontent.com/ntkathole/ownca/master/generate-ca.sh\n"
        "wget https://raw.githubusercontent.com/ntkathole/ownca/master/generate-crt.sh\n"
        "echo 100001 >> serial\n"
        "chmod 744 *.sh\n"
        'yes "" | ./generate-ca.sh\n'
        'yes | ./generate-crt.sh $name\n'
        'cp cacert.crt $name/\n'
        .format(hostname=os.environ.get('SERVER_HOSTNAME'))
    )
    put(local_path=certs_script,
        remote_path='/root/certs_script.sh')
    certs_script.close()
    run("sh /root/certs_script.sh")


def add_custom_product_subscription_to_hosts(product, hosts):
    """Adds custom product subscription to given list of hosts

    :param str product: The custom product name
    :param list hosts: List of content host names
    """
    from_version = os.environ.get('FROM_VERSION')
    for host in hosts:
        sub = entities.Subscription().search(
            query={'search': 'name={0}'.format(product)})[0]
        if float(from_version) <= 6.1:
            execute(
                attach_subscription_to_host_from_content_host, sub.cp_id, host=host)
        else:
            host = entities.Host().search(query={'search': 'name={}'.format(host)})[0]
            entities.HostSubscription(host=host).add_subscriptions(
                data={'subscriptions': [{'id': sub.id, 'quantity': 1}]})


def check_status_of_running_task(command, attempt):
    """
        This function is used to check the running tasks status via foreman-maintain,
        If task is running then wait for their completion otherwise move to
        the next step.
    """
    retry = 0
    while retry <= attempt:
        status = run("{} >/dev/null 2>&1; echo $?".format(command))
        if status:
            logger.info("Attempt{}: Command: {}\n"
                        "Task is still in running state".
                        format(retry, command))
            retry += 1
        else:
            logger.info("Command: {}\n "
                        "Check for running tasks:: [OK]".format(command))
            return 0
    else:
        logger.info("Command: {}\n"
                    "Exceeded the maximum attempt to check the "
                    "tasks running status".format(command))
