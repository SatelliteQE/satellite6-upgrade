import os
import sys

from upgrade.helpers.tools import (
    host_pings,
    host_ssh_availability_check,
    reboot
)
from automation_tools import (
    setup_satellite_firewall,
    subscribe,
    install_prerequisites
)
from automation_tools.utils import distro_info, update_packages
from datetime import datetime
from fabric.api import env, execute, run
from upgrade.helpers.logger import logger
from upgrade.helpers.rhevm4 import (
    create_rhevm4_instance,
    delete_rhevm4_instance
)
from upgrade.helpers.tasks import (
    enable_disable_repo,
    foreman_maintain_upgrade,
    repository_setup,
    repository_cleanup,
    setup_foreman_maintain
)

logger = logger()


def satellite6_setup(os_version):
    """Sets up required things on upgrade running machine and on Satellite to
    perform satellite upgrade later

    :param string os_version: The OS version onto which the satellite installed
        e.g: rhel6, rhel7
    """
    # If Personal Satellite Hostname provided
    if os.environ.get('SATELLITE_HOSTNAME'):
        sat_host = os.environ.get('SATELLITE_HOSTNAME')
    # Else run upgrade on rhevm satellite
    else:
        # Get image name and Hostname from Jenkins environment
        missing_vars = [
            var for var in ('RHEV_SAT_IMAGE', 'RHEV_SAT_HOST')
            if var not in os.environ]
        # Check if image name and Hostname in jenkins are set
        if missing_vars:
            logger.warning('The following environment variable(s) must be set '
                           'in jenkins environment: {0}.'.format(
                                ', '.join(missing_vars)))
            sys.exit(1)
        sat_image = os.environ.get('RHEV_SAT_IMAGE')
        sat_host = os.environ.get('RHEV_SAT_HOST')
        sat_instance = 'upgrade_satellite_auto_{0}'.format(os_version)
        execute(delete_rhevm4_instance, sat_instance)
        execute(create_rhevm4_instance, sat_instance, sat_image)
        if not host_pings(sat_host):
            sys.exit(1)
        execute(host_ssh_availability_check, sat_host)
        # start's/enables/install's ntp
        # Check that hostname and localhost resolve correctly
        execute(install_prerequisites, host=sat_host)
        # Subscribe the instance to CDN
        execute(subscribe, host=sat_host)
        execute(lambda: run('katello-service restart'), host=sat_host)
    # Set satellite hostname in fabric environment
    env['satellite_host'] = sat_host
    logger.info('Satellite {} is ready for Upgrade!'.format(sat_host))
    return sat_host


def satellite6_upgrade(zstream=False):
    """This function is used to perform the satellite upgrade of two type based on
    their passed parameter.
    :param zstream:

    if upgrade_type==None:
        - Upgrades Satellite Server from old version to latest
            The following environment variables affect this command:

            BASE_URL
                Optional, defaults to available satellite version in CDN.
                URL for the compose repository
            FROM_VERSION
                Current satellite version which will be upgraded to latest version
            TO_VERSION
                Satellite version to upgrade to and enable repos while upgrading.
                e.g '6.1','6.2', '6.3'
            PERFORM_FOREMAN_MAINTAIN_UPGRADE
                use foreman-maintain for satellite upgrade

    else:
        - Upgrades Satellite Server to its latest zStream version
            Note: For zstream upgrade both 'To' and 'From' version should be same

            FROM_VERSION
                Current satellite version which will be upgraded to latest version
            TO_VERSION
                Next satellite version to which satellite will be upgraded
            PERFORM_FOREMAN_MAINTAIN_UPGRADE
                use foreman-maintain for satellite upgrade

    """
    logger.highlight('\n========== SATELLITE UPGRADE =================\n')
    to_version = os.environ.get('TO_VERSION')
    from_version = os.environ.get('FROM_VERSION')
    if zstream:
        if not from_version == to_version:
            logger.warning('zStream Upgrade on Satellite cannot be performed as '
                           'FROM and TO versions are not same!')
            sys.exit(1)
    base_url = os.environ.get('BASE_URL')
    major_ver = distro_info()[1]
    disable_repo_name = ["*"]
    enable_repos_name = ['rhel-{0}-server-rpms'.format(major_ver),
                         'rhel-server-rhscl-{0}-rpms'.format(major_ver)]
    if os.environ.get('PERFORM_FOREMAN_MAINTAIN_UPGRADE') == 'true' \
            and os.environ.get('OS') == 'rhel7':
        foreman_maintain_upgrade(base_url)
    else:
        setup_satellite_firewall()
        if not zstream:
            run('rm -rf /etc/yum.repos.d/rhel-{optional,released}.repo')
            logger.info('Updating system packages ... ')
            setup_foreman_maintain()
            update_packages(quiet=True)
        # Following disables the old satellite repo and extra repos enabled
        # during subscribe e.g Load balancer Repo
        enable_disable_repo(disable_repo_name, enable_repos_name)
        if base_url is None:
            enable_disable_repo([], ['rhel-{0}-server-satellite-{1}-rpms'.format(
                major_ver, to_version)])
            # Remove old custom sat repo
            repository_cleanup('sat')
        else:
            repository_setup("sat6",
                             "satellite 6",
                             base_url, 1, 0)
        nonfm_upgrade()
    # Rebooting the satellite for kernel update if any
    reboot(180)
    host_ssh_availability_check(env.get('satellite_host'))
    # Test the Upgrade is successful
    upgrade_validation()


def nonfm_upgrade():
    """
    The purpose of this module to perform the upgrade task without foreman-maintain.
    In this function we setup the repository, stop the katello services,
    cleanup, and execute satellite upgrade task"
    """
    # Check what repos are set
    run('yum repolist')
    # Stop katello services, except mongod
    run('katello-service stop')
    run('yum clean all', warn_only=True)
    # Updating the packages again after setting sat6 repo
    logger.info('Updating system and satellite packages... ')
    preyum_time = datetime.now().replace(microsecond=0)
    update_packages(quiet=False)
    postyum_time = datetime.now().replace(microsecond=0)
    logger.highlight('Time taken for system and satellite packages update'
                     ' - {}'.format(str(postyum_time - preyum_time)))
    # Running Upgrade
    preup_time = datetime.now().replace(microsecond=0)
    run('satellite-installer --scenario satellite --upgrade')
    postup_time = datetime.now().replace(microsecond=0)
    logger.highlight('Time taken for Satellite Upgrade - {}'.format(
        str(postup_time - preup_time)))


def upgrade_validation():
    """
    In this function we check the system states after upgrade.
    """
    run('hammer ping', warn_only=True)
    run('katello-service status', warn_only=True)
