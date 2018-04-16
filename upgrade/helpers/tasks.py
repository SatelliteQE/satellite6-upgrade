"""A set of tasks to help upgrade Satellite and Capsule.

Many commands are affected by environment variables. Unless stated otherwise,
all environment variables are required.
"""
import os
import sys
import time
import socket

from automation_tools import (
    foreman_debug,
    setup_alternate_capsule_ports,
    setup_fake_manifest_certificate,
)
from automation_tools import setup_foreman_discovery
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
from automation_tools.satellite6.log import LogAnalyzer
from automation_tools.utils import get_discovery_image
from robozilla.decorators import bz_bug_is_open
from upgrade.helpers.logger import logger
from upgrade.helpers.docker import (
    attach_subscription_to_host_from_content_host
)
from fabric.api import env, execute, put, run
if sys.version_info[0] is 2:
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
    if os.environ.get('FROM_VERSION') not in ['6.3', '6.2', '6.1', '6.0']:
        failure.append('Wrong FROM_VERSION provided to upgrade from. '
                       'Provide one of 6.3, 6.2, 6.1, 6.0')
    # To which version to upgrade
    if os.environ.get('TO_VERSION') not in ['6.1', '6.2', '6.3']:
        failure.append('Wrong TO_VERSION provided to upgrade to. '
                       'Provide one of 6.1, 6.2, 6.3')
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


def capsule_sync(cap_host):
    """Run Capsule Sync as a part of job

    :param list cap_host: List of capsules to perform sync
    """
    set_hammer_config()
    if os.environ.get('TO_VERSION') in ['6.2', '6.3']:
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
    if os.environ.get('DISTRIBUTION') == 'CDN':
        enable_repos('rhel-7-server-satellite-maintenance-6-rpms')
    else:
        satellite_repo = StringIO()
        satellite_repo.write('[foreman-maintain]\n')
        satellite_repo.write('name=foreman-maintain\n')
        satellite_repo.write('baseurl={0}\n'.format(
            os.environ.get('MAINTAIN_REPO')
        ))
        satellite_repo.write('enabled=1\n')
        satellite_repo.write('gpgcheck=0\n')
        put(local_path=satellite_repo,
            remote_path='/etc/yum.repos.d/foreman-maintain.repo')
        satellite_repo.close()

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
    try:
        with LogAnalyzer(os.environ.get('SATELLITE_HOSTNAME')):
            if os.environ.get('FROM_VERSION') != os.environ.get('TO_VERSION'):
                run('foreman-maintain upgrade run --target-version {}'
                    ' -y'.format(os.environ.get('TO_VERSION')))
            else:
                run('foreman-maintain upgrade run --target-version {}'
                    ' -y'.format(os.environ.get('TO_VERSION') + ".z"))
            # Generate foreman debug on satellite after upgrade
            execute(foreman_debug, 'satellite_{}'.format(
                os.environ.get('SATELLITE_HOSTNAME')),
                host=os.environ.get('SATELLITE_HOSTNAME'))
    except Exception:
        # Generate foreman debug on failed satellite upgrade
        execute(foreman_debug, 'satellite_{}'.format(
            os.environ.get('SATELLITE_HOSTNAME')),
            host=os.environ.get('SATELLITE_HOSTNAME'))
        raise
    if os.environ.get('FROM_VERSION') == os.environ.get('TO_VERSION'):
        # z stream upgrade
        run('foreman-maintain upgrade run --target-version {} -y'.format(
            os.environ.get('TO_VERSION') + ".z"))
    else:
        run('foreman-maintain upgrade run --target-version {} -y'.format(
            os.environ.get('TO_VERSION')))


def get_osp_hostname(ipaddr):
    """The openstack has floating ip and we need to fetch the hostname from DNS
    :param ipaddr : IP address of the osp box
    """
    try:
        return socket.gethostbyaddr(ipaddr)[0]
    except Exception as ex:
        logger.error(ex)
