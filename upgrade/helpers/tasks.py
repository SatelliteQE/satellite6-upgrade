"""A set of tasks to help upgrade Satellite and Capsule.

Many commands are affected by environment variables. Unless stated otherwise,
all environment variables are required.
"""
import os
import sys
import time
import socket

from automation_tools import (
    setup_alternate_capsule_ports,
    setup_fake_manifest_certificate,
)
from automation_tools import setup_foreman_discovery, setup_avahi_discovery
from automation_tools.repository import enable_repos
from automation_tools.satellite6.hammer import (
    attach_subscription_to_host_from_satellite,
    get_attribute_value,
    get_product_subscription_id,
    hammer,
    hammer_activation_key_add_subscription,
    hammer_activation_key_content_override,
    hammer_content_view_add_repository,
    hammer_content_view_promote_version,
    hammer_content_view_publish,
    hammer_determine_cv_and_env_from_ak,
    hammer_product_create,
    hammer_repository_create,
    hammer_repository_set_enable,
    hammer_repository_synchronize,
    set_hammer_config
)
from automation_tools.utils import get_discovery_image
from nailgun import entities
from robozilla.decorators import bz_bug_is_open
from upgrade.helpers.logger import logger
from upgrade.helpers.docker import (
    attach_subscription_to_host_from_content_host
)
from fabric.api import env, execute, put, run, warn_only
if sys.version_info[0] == 2:
    from StringIO import StringIO  # (import-error) pylint:disable=F0401
else:  # pylint:disable=F0401,E0611
    from io import StringIO

logger = logger()


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
    # From which version to upgrade
    supported_vers = ['6.4', '6.3', '6.2', '6.1', '6.0']
    if os.environ.get('FROM_VERSION') not in supported_vers:
        failure.append('Wrong FROM_VERSION provided to upgrade from. '
                       'Provide one of 6.4, 6.3, 6.2, 6.1, 6.0')
    # To which version to upgrade
    if os.environ.get('TO_VERSION') not in ['6.4', '6.1', '6.2', '6.3']:
        failure.append('Wrong TO_VERSION provided to upgrade to. '
                       'Provide one of 6.4, 6.1, 6.2, 6.3')
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

    Rhevm upgrade Env Vars:

    RHEV_CAPSULE_AK
        The AK name used in capsule subscription
    """
    logger.info('Syncing latest capsule repos in Satellite ...')
    capsule_repo = os.environ.get('CAPSULE_URL')
    from_version = os.environ.get('FROM_VERSION')
    to_version = os.environ.get('TO_VERSION')
    os_ver = os.environ.get('OS')[-1]
    tools_repo_url = os.environ.get('TOOLS_URL_RHEL7') if to_version in [
        '6.4', '6.3'] else None
    activation_key = os.environ.get(
        'CAPSULE_AK', os.environ.get('RHEV_CAPSULE_AK'))
    if activation_key is None:
        logger.warning(
            'The AK name is not provided for Capsule upgrade! Aborting...')
        sys.exit(1)
    # Set hammer configuration
    set_hammer_config()
    cv_name, env_name = hammer_determine_cv_and_env_from_ak(
        activation_key, '1')
    # Fix dead pulp tasks
    if os_ver == '6':
        run('for i in pulp_resource_manager pulp_workers pulp_celerybeat; '
            'do service $i restart; done')
    # If custom capsule repo is not given then
    # enable capsule repo from Redhat Repositories
    product_name = 'capsule6_latest' if capsule_repo \
        else 'Red Hat Satellite Capsule'
    repo_name = 'capsule6_latest_repo' if capsule_repo \
        else 'Red Hat Satellite Capsule {0} (for RHEL {1} Server) ' \
        '(RPMs)'.format(to_version, os_ver)
    try:
        if capsule_repo:
            # Check if the product of latest capsule repo is already created,
            # if not create one and attach the subscription to existing AK
            get_attribute_value(hammer(
                'product list --organization-id 1'), product_name, 'name')
            # If keyError is not thrown as if the product is created already
            logger.info(
                'The product for latest Capsule repo is already created!')
            logger.info('Attaching that product subscription to capsule ....')
        else:
            # In case of CDN Upgrade, the capsule repo has to be resynced
            # and needs to publich/promote those contents
            raise KeyError
    except KeyError:
        # If latest capsule repo is not created already(Fresh Upgrade),
        # So create new....
        if to_version in ['6.4', '6.3']:
            (
                rhscl_prd,
                rhscl_repo_name,
                rhscl_label,
                rh7server_prd,
                rh7server_repo_name,
                rh7server_label
            ) = sync_rh_repos_to_satellite()
            if tools_repo_url:
                capsule_tools = 'Capsule Tools Product'
                capsule_tools_repo = 'Capsule Tools Repo'
                hammer_product_create(capsule_tools, '1')
                tools_label = None
                time.sleep(2)
                hammer_repository_create(
                    capsule_tools_repo, '1', capsule_tools, tools_repo_url)
            else:
                capsule_tools = 'Red Hat Enterprise Linux Server'
                capsule_tools_repo = 'Red Hat Satellite Tools {0} '
                '(for RHEL {1} Server) (RPMs)'.format(to_version, os_ver)
                tools_label = 'rhel-{0}-server-satellite-tools-{1}-' \
                              'rpms'.format(os_ver, to_version)
                hammer_repository_set_enable(
                    capsule_tools_repo, capsule_tools, '1', 'x86_64')
                time.sleep(5)
            hammer_repository_synchronize(capsule_tools_repo,
                                          '1',
                                          capsule_tools
                                          )
            hammer_content_view_add_repository(
                cv_name, '1', rhscl_prd, rhscl_repo_name)
            hammer_content_view_add_repository(
                cv_name, '1', rh7server_prd, rh7server_repo_name)
            hammer_content_view_add_repository(
                cv_name, '1', capsule_tools, capsule_tools_repo)
            hammer_activation_key_content_override(
                activation_key, rhscl_label, '1', '1')
            hammer_activation_key_content_override(
                activation_key, rh7server_label, '1', '1')
            if tools_repo_url:
                hammer_activation_key_add_subscription(
                    activation_key, '1', capsule_tools)
            else:
                hammer_activation_key_content_override(
                    activation_key, tools_label, '1', '1')
        if capsule_repo:
            hammer_product_create(product_name, '1')
            time.sleep(2)
            hammer_repository_create(
                repo_name, '1', product_name, capsule_repo)
        else:
            hammer_repository_set_enable(
                repo_name, product_name, '1', 'x86_64')
            repo_name = repo_name.replace('(', '').replace(')', '') + ' x86_64'
        hammer_repository_synchronize(repo_name, '1', product_name)
        # Add repos to CV
        hammer_content_view_add_repository(
            cv_name, '1', product_name, repo_name)
        hammer_content_view_publish(cv_name, '1')
        # Promote cv
        lc_env_id = get_attribute_value(
            hammer('lifecycle-environment list --organization-id 1 '
                   '--name {}'.format(env_name)), env_name, 'id')
        cv_version_data = hammer(
            'content-view version list --content-view {} '
            '--organization-id 1'.format(cv_name))
        latest_cv_ver = sorted([float(data['name'].split(
            '{} '.format(cv_name))[1]) for data in cv_version_data]).pop()
        cv_ver_id = get_attribute_value(cv_version_data, '{0} {1}'.format(
            cv_name, latest_cv_ver), 'id')
        hammer_content_view_promote_version(
            cv_name, cv_ver_id, lc_env_id, '1',
            False if from_version == '6.0' else True)
        if capsule_repo:
            hammer_activation_key_add_subscription(
                activation_key, '1', product_name)
        else:
            label = 'rhel-{0}-server-satellite-capsule-{1}-rpms'.format(
                os_ver, to_version)
            hammer_activation_key_content_override(
                activation_key, label, '1', '1')
    # Add this latest capsule repo to capsules to perform upgrade later
    # If downstream capsule, Update AK with latest capsule repo subscription
    if capsule_repo:
        for capsule in capsules:
            if from_version == '6.1':
                subscription_id = get_product_subscription_id(
                    '1', product_name)
                execute(
                    attach_subscription_to_host_from_content_host,
                    subscription_id,
                    host=capsule)
            else:
                attach_subscription_to_host_from_satellite(
                    '1', product_name, capsule)
    else:
        # In upgrade to CDN capsule, the subscription will be already attached
        pass


def sync_rh_repos_to_satellite():
    """Task to sync Redhat Repositories to latest required during upgrade

    :returns tuple: RHSCL and Redhat 7 Server repo name, label name and
        product name
    """
    # RHSCL
    rhscl_repo = 'Red Hat Software Collections RPMs for Red Hat ' \
                 'Enterprise Linux 7 Server'
    rhscl_prd = 'Red Hat Software Collections for RHEL Server'
    rhscl_label = 'rhel-server-rhscl-7-rpms'
    rhscl_repo_name = 'Red Hat Software Collections RPMs for Red ' \
                      'Hat Enterprise Linux 7 Server x86_64 7Server'
    # Red Hat Enterprise Linux 7 Server
    rh7server_repo = 'Red Hat Enterprise Linux 7 Server (RPMs)'
    rh7server_prd = 'Red Hat Enterprise Linux Server'
    rh7server_label = 'rhel-7-server-rpms'
    rh7server_repo_name = 'Red Hat Enterprise Linux 7 Server RPMs x86_64 ' \
                          '7Server'
    # Enable rhscl repository
    hammer('repository-set enable --name "{0}" '
           '--product "{1}" '
           '--organization-id 1 '
           '--basearch "x86_64" '
           '--releasever 7Server'.format(rhscl_repo,
                                         rhscl_prd)
           )
    time.sleep(20)
    # Sync enabled Repo from cdn
    hammer_repository_synchronize(rhscl_repo_name,
                                  '1',
                                  rhscl_prd
                                  )
    # Enable RHEL 7 Server repository
    hammer('repository-set enable --name "{0}" '
           '--product "{1}" '
           '--organization-id 1 '
           '--basearch "x86_64" '
           '--releasever 7Server'.format(rh7server_repo,
                                         rh7server_prd)
           )
    time.sleep(20)
    # Sync enabled Repo from cdn
    hammer_repository_synchronize(rh7server_repo_name,
                                  '1',
                                  rh7server_prd
                                  )
    # FixMe: If number of repository to be synced from CDN increases use dict
    return {
        rhscl_prd,
        rhscl_repo_name,
        rhscl_label,
        rh7server_prd,
        rh7server_repo_name,
        rh7server_label
    }


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
    activation_key = os.environ.get(
        'CLIENT_AK_{}'.format(client_os),
        os.environ.get('RHEV_CLIENT_AK_{}'.format(client_os))
    )
    if activation_key is None:
        logger.warning('The AK details are not provided for {0} Client '
                       'upgrade!'.format(client_os))
        sys.exit(1)
    # Set hammer configuration
    set_hammer_config()
    cv_name, env_name = hammer_determine_cv_and_env_from_ak(
        activation_key, '1')
    tools_product = 'tools6_latest_{}'.format(client_os)
    tools_repo = 'tools6_latest_repo_{}'.format(client_os)
    # adding sleeps in between to avoid race conditions
    time.sleep(20)
    hammer_product_create(tools_product, '1')
    time.sleep(10)
    hammer_repository_create(tools_repo, '1', tools_product, tools_repo_url)
    time.sleep(10)
    hammer_repository_synchronize(tools_repo, '1', tools_product)
    hammer_content_view_add_repository(cv_name, '1', tools_product, tools_repo)
    hammer_content_view_publish(cv_name, '1')
    # Promote cv
    lc_env_id = get_attribute_value(
        hammer('lifecycle-environment list --organization-id 1 '
               '--name {}'.format(env_name)), env_name, 'id')
    cv_version_data = hammer(
        'content-view version list --content-view {} '
        '--organization-id 1'.format(cv_name))
    latest_cv_ver = sorted([float(data['name'].split(
        '{} '.format(cv_name))[1]) for data in cv_version_data]).pop()
    cv_ver_id = get_attribute_value(cv_version_data, '{0} {1}'.format(
        cv_name, latest_cv_ver), 'id')
    hammer_content_view_promote_version(cv_name, cv_ver_id, lc_env_id, '1')
    # Add new product subscriptions to AK
    hammer_activation_key_add_subscription(activation_key, '1', tools_product)
    # Add this latest tools repo to hosts to upgrade
    for host in hosts:
        if os.environ.get('FROM_VERSION') in ['6.0', '6.1']:
            subscription_id = get_product_subscription_id('1', tools_product)
            # If not User Hosts then, attach sub to dockered clients
            if not all([
                os.environ.get('CLIENT6_HOSTS'),
                os.environ.get('CLIENT7_HOSTS')
            ]):
                docker_vm = os.environ.get('DOCKER_VM')
                execute(
                    attach_subscription_to_host_from_content_host,
                    subscription_id,
                    True,
                    host,
                    host=docker_vm)
            # Else, Attach subs to user hosts
            else:
                execute(
                    attach_subscription_to_host_from_content_host,
                    subscription_id,
                    host=host)
        else:
            attach_subscription_to_host_from_satellite(
                '1', tools_product, host)


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
    if sat_version not in ['6.0', '6.1']:
        # Update the Default Organization name, which was updated in 6.2
        logger.info("Update the Default Organization name, which was updated "
                    "in 6.2")
        execute(hammer, 'organization update --name "Default_Organization" '
                '--new-name "Default Organization" ',
                host=sat_host)
        # Update the Default Location name, which was updated in 6.2
        logger.info("Update the Default Location name, which was updated in "
                    "6.2")
        execute(hammer, 'location update --name "Default_Location" '
                        '--new-name "Default Location" ',
                host=sat_host)
        if bz_bug_is_open(1502505):
            logger.info(
                "Update the default_location_puppet_content value with "
                "updated location name.Refer BZ:1502505")
            execute(hammer, 'settings set --name '
                            '"default_location_puppet_content" --value '
                            '"Default Location"', host=sat_host)
    # Increase log level to DEBUG, to get better logs in foreman_debug
    execute(lambda: run('sed -i -e \'/:level: / s/: .*/: '
                        'debug/\' /etc/foreman/settings.yaml'), host=sat_host)
    execute(lambda: run('katello-service restart'), host=sat_host)
    # Execute capsule sync task , after the upgrade is completed
    if cap_host:
        execute(capsule_sync, cap_host, host=sat_host)
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
    set_hammer_config()
    if os.environ.get('TO_VERSION') in ['6.2', '6.3', '6.4']:
        logger.info('Refreshing features for capsule host {0}'.
                    format(cap_host))
        print hammer('capsule refresh-features --name "{0}"'.
                     format(cap_host))
    logger.info('Running Capsule sync for capsule host {0}'.
                format(cap_host))
    print hammer('capsule content synchronize --name {0}'.format(cap_host))


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
    # for 6.4 and 6.4.z upgrade.
    if os.environ.get('TO_VERSION') in ['6.3', '6.4']:
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
    else:
        if os.environ.get('FROM_VERSION') == os.environ.get('TO_VERSION'):
            # z stream upgrade
            run('foreman-maintain upgrade run --target-version {} -y'.format(
                os.environ.get('TO_VERSION') + ".z"))
        else:
            run('foreman-maintain upgrade run --target-version {} -y'.format(
                os.environ.get('TO_VERSION')))


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
