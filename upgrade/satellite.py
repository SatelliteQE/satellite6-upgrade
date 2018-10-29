import os
import sys

from upgrade.helpers.tools import (
    host_pings,
    host_ssh_availability_check,
    reboot
)
from automation_tools import (
    enable_ostree,
    setup_satellite_firewall,
    subscribe,
    install_prerequisites
)
from automation_tools.satellite6.hammer import hammer, set_hammer_config
from automation_tools.repository import enable_repos, disable_repos
from automation_tools.utils import distro_info, update_packages
from datetime import datetime
from fabric.api import env, execute, put, run
from upgrade.helpers.logger import logger
from upgrade.helpers.rhevm4 import (
    create_rhevm4_instance,
    delete_rhevm4_instance
)
from upgrade.helpers.tasks import (
    setup_foreman_maintain,
    upgrade_using_foreman_maintain
)
if sys.version_info[0] is 2:
    from StringIO import StringIO  # (import-error) pylint:disable=F0401
else:  # pylint:disable=F0401,E0611
    from io import StringIO

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
                           'in jenkin environment: {0}.'.format(
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


def satellite6_upgrade():
    """Upgrades satellite from old version to latest version.

    The following environment variables affect this command:

    BASE_URL
        Optional, defaults to available satellite version in CDN.
        URL for the compose repository
    TO_VERSION
        Satellite version to upgrade to and enable repos while upgrading.
        e.g '6.1','6.2', '6.3'
    PERFORM_FOREMAN_MAINTAIN_UPGRADE
        use foreman-maintain for satellite upgrade
    """
    logger.highlight('\n========== SATELLITE UPGRADE =================\n')
    to_version = os.environ.get('TO_VERSION')
    base_url = os.environ.get('BASE_URL')
    if to_version not in ['6.1', '6.2', '6.3', '6.4', '6.5']:
        logger.warning('Wrong Satellite Version Provided to upgrade to. '
                       'Provide one of 6.1, 6.2, 6.3, 6.4, 6.5')
        sys.exit(1)
    major_ver = distro_info()[1]
    if os.environ.get('PERFORM_FOREMAN_MAINTAIN_UPGRADE') == 'true' \
            and os.environ.get('OS') == 'rhel7':
        if base_url is None:
            os.environ['DISTRIBUTION'] = "CDN"
        else:
            os.environ['DISTRIBUTION'] = "DOWNSTREAM"
        # setup foreman-maintain
        setup_foreman_maintain()
        preup_time = datetime.now().replace(microsecond=0)
        # perform upgrade using foreman-maintain
        upgrade_using_foreman_maintain()
        postup_time = datetime.now().replace(microsecond=0)
        logger.highlight('Time taken for Satellite Upgrade - {}'.format(
            str(postup_time - preup_time)))
    else:
        setup_satellite_firewall()
        run('rm -rf /etc/yum.repos.d/rhel-{optional,released}.repo')
        logger.info('Updating system packages ... ')
        # setup foreman-maintain
        setup_foreman_maintain()
        update_packages(quiet=True)
        # Following disables the old satellite repo and extra repos enabled
        # during subscribe e.g Load balancer Repo
        disable_repos('*', silent=True)
        enable_repos('rhel-{0}-server-rpms'.format(major_ver))
        enable_repos('rhel-server-rhscl-{0}-rpms'.format(major_ver))
        enable_repos('rhel-{0}-server-extras-rpms'.format(major_ver))
        # If CDN upgrade then enable satellite latest version repo
        if base_url is None:
            enable_repos('rhel-{0}-server-satellite-{1}-rpms'.format(
                major_ver, to_version))
            # Remove old custom sat repo
            for fname in os.listdir('/etc/yum.repos.d/'):
                if 'sat' in fname.lower():
                    os.remove('/etc/yum.repos.d/{}'.format(fname))
        # Else, consider this as Downstream upgrade
        else:
            # Add Sat6 repo from latest compose
            satellite_repo = StringIO()
            satellite_repo.write('[sat6]\n')
            satellite_repo.write('name=satellite 6\n')
            satellite_repo.write('baseurl={0}\n'.format(base_url))
            satellite_repo.write('enabled=1\n')
            satellite_repo.write('gpgcheck=0\n')
            put(local_path=satellite_repo,
                remote_path='/etc/yum.repos.d/sat6.repo')
            satellite_repo.close()
        # Check what repos are set
        run('yum repolist')
        # Stop katello services, except mongod
        run('katello-service stop')
        if to_version == '6.1':
            run('service-wait mongod start')
        run('yum clean all', warn_only=True)
        # Updating the packages again after setting sat6 repo
        logger.info('Updating satellite packages ... ')
        preyum_time = datetime.now().replace(microsecond=0)
        update_packages(quiet=False)
        postyum_time = datetime.now().replace(microsecond=0)
        logger.highlight('Time taken for satellite packages update- {}'.format(
            str(postyum_time-preyum_time)))
        # Running Upgrade
        preup_time = datetime.now().replace(microsecond=0)
        if to_version == '6.1':
            run('katello-installer --upgrade')
        else:
            run('satellite-installer --scenario satellite --upgrade')
        postup_time = datetime.now().replace(microsecond=0)
        logger.highlight('Time taken for Satellite Upgrade - {}'.format(
            str(postup_time-preup_time)))
    set_hammer_config()
    # Rebooting the satellite for kernel update if any
    reboot(180)
    host_ssh_availability_check(env.get('satellite_host'))
    # Test the Upgrade is successful
    hammer('ping')
    run('katello-service status', warn_only=True)
    # Enable ostree feature only for rhel7 and sat6.2
    if to_version == '6.2' and major_ver == 7:
        enable_ostree(sat_version='6.2')


def satellite6_zstream_upgrade():
    """Upgrades Satellite Server to its latest zStream version

    Note: For zstream upgrade both 'To' and 'From' version should be same

    FROM_VERSION
        Current satellite version which will be upgraded to latest version
    TO_VERSION
        Next satellite version to which satellite will be upgraded
    PERFORM_FOREMAN_MAINTAIN_UPGRADE
        use foreman-maintain for satellite upgrade
    """
    logger.highlight('\n========== SATELLITE UPGRADE =================\n')
    from_version = os.environ.get('FROM_VERSION')
    to_version = os.environ.get('TO_VERSION')
    if not from_version == to_version:
        logger.warning('zStream Upgrade on Satellite cannot be performed as '
                       'FROM and TO versions are not same!')
        sys.exit(1)
    base_url = os.environ.get('BASE_URL')
    major_ver = distro_info()[1]
    if os.environ.get('PERFORM_FOREMAN_MAINTAIN_UPGRADE') == "true" \
            and os.environ.get('OS') == 'rhel7':
        if base_url is None:
            os.environ['DISTRIBUTION'] = "CDN"
        else:
            os.environ['DISTRIBUTION'] = "DOWNSTREAM"
        # setup foreman-maintain
        setup_foreman_maintain()
        preup_time = datetime.now().replace(microsecond=0)
        # perform upgrade using foreman-maintain
        upgrade_using_foreman_maintain()
        postup_time = datetime.now().replace(microsecond=0)
        logger.highlight('Time taken for Satellite Upgrade - {}'.format(
            str(postup_time - preup_time)))
    else:
        setup_satellite_firewall()
        # Following disables the old satellite repo and extra repos enabled
        # during subscribe e.g Load balancer Repo
        disable_repos('*', silent=True)
        enable_repos('rhel-{0}-server-rpms'.format(major_ver))
        enable_repos('rhel-server-rhscl-{0}-rpms'.format(major_ver))
        enable_repos('rhel-{0}-server-extras-rpms'.format(major_ver))
        # If CDN upgrade then enable satellite latest version repo
        if base_url is None:
            enable_repos('rhel-{0}-server-satellite-{1}-rpms'.format(
                major_ver, to_version))
            # Remove old custom sat repo
            for fname in os.listdir('/etc/yum.repos.d/'):
                if 'sat' in fname.lower():
                    os.remove('/etc/yum.repos.d/{}'.format(fname))
        # Else, consider this as Downstream upgrade
        else:
            # Add Sat6 repo from latest compose
            satellite_repo = StringIO()
            satellite_repo.write('[sat6]\n')
            satellite_repo.write('name=satellite 6\n')
            satellite_repo.write('baseurl={0}\n'.format(base_url))
            satellite_repo.write('enabled=1\n')
            satellite_repo.write('gpgcheck=0\n')
            put(local_path=satellite_repo,
                remote_path='/etc/yum.repos.d/sat6.repo')
            satellite_repo.close()
        # Check what repos are set
        run('yum repolist')
        # Stop katello services, except mongod
        run('katello-service stop')
        if to_version == '6.1':
            run('service-wait mongod start')
        run('yum clean all', warn_only=True)
        # Updating the packages again after setting sat6 repo
        logger.info('Updating system and satellite packages... ')
        preyum_time = datetime.now().replace(microsecond=0)
        update_packages(quiet=False)
        postyum_time = datetime.now().replace(microsecond=0)
        logger.highlight('Time taken for system and satellite packages update'
                         ' - {}'.format(str(postyum_time-preyum_time)))
        # Running Upgrade
        preup_time = datetime.now().replace(microsecond=0)
        if to_version == '6.1':
            run('katello-installer --upgrade')
        else:
            run('satellite-installer --scenario satellite --upgrade')
        postup_time = datetime.now().replace(microsecond=0)
        logger.highlight('Time taken for Satellite Upgrade - {}'.format(
            str(postup_time-preup_time)))
    # Rebooting the satellite for kernel update if any
    reboot(180)
    host_ssh_availability_check(env.get('satellite_host'))
    # Test the Upgrade is successful
    set_hammer_config()
    hammer('ping')
    run('katello-service status', warn_only=True)
