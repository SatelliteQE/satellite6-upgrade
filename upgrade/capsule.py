import os
import sys

from automation_tools import setup_capsule_firewall
from automation_tools.utils import distro_info
from fabric.api import env, execute, run
from upgrade.helpers.logger import logger
from upgrade.helpers.rhevm4 import (
    create_rhevm4_instance,
    delete_rhevm4_instance
)
from upgrade.helpers.tasks import (
    sync_capsule_repos_to_upgrade,
    add_baseOS_repo,
    foreman_service_restart,
    nonfm_upgrade,
    upgrade_validation,
    setup_foreman_maintain_repo,

)
from upgrade.helpers.tools import (
    copy_ssh_key,
    disable_old_repos,
    reboot,
    host_pings,
    host_ssh_availability_check
)

logger = logger()


def satellite6_capsule_setup(sat_host, os_version, upgradable_capsule=True):
    """Setup all per-requisites for user provided capsule or auto created
    capsule on rhevm for capsule upgrade.

    :param string sat_host: Satellite hostname to which the capsule registered
    :param string os_version: The OS version onto which the capsule installed
        e.g: rhel6, rhel7
    :param bool upgradable_capsule: Whether to setup capsule to be able to
        upgrade in future
    """
    if os_version == 'rhel6':
        baseurl = os.environ.get('RHEL6_CUSTOM_REPO')
    elif os_version == 'rhel7':
        baseurl = os.environ.get('RHEL7_CUSTOM_REPO')
    else:
        logger.warning('No OS Specified. Terminating..')
        sys.exit(1)
    # For User Defined Capsule
    if os.environ.get('CAPSULE_HOSTNAMES'):
        cap_hosts = os.environ.get('CAPSULE_HOSTNAMES')
        if not os.environ.get('CAPSULE_AK'):
            logger.warning('CAPSULE_AK environment variable is not defined !')
            sys.exit(1)
    # Else run upgrade on rhevm capsule
    else:
        # Get image name and Hostname from Jenkins environment
        missing_vars = [
            var for var in (
                'RHEV_CAP_IMAGE',
                'RHEV_CAP_HOST',
                'RHEV_CAPSULE_AK')
            if var not in os.environ]
        # Check if image name and Hostname in jenkins are set
        if missing_vars:
            logger.warning('The following environment variable(s) must be '
                           'set: {0}.'.format(', '.join(missing_vars)))
            sys.exit(1)
        cap_image = os.environ.get('RHEV_CAP_IMAGE')
        cap_hosts = os.environ.get('RHEV_CAP_HOST')
        cap_instance = 'upgrade_capsule_auto_{0}'.format(os_version)
        execute(delete_rhevm4_instance, cap_instance)
        logger.info('Turning on Capsule Instance ....')
        execute(create_rhevm4_instance, cap_instance, cap_image)
        non_responsive_host = []
        env['capsule_hosts'] = cap_hosts
        if ',' in cap_hosts:
            cap_hosts = [cap.strip() for cap in cap_hosts.split(',')]
        else:
            cap_hosts = [cap_hosts]
        for cap_host in cap_hosts:
            if not host_pings(cap_host):
                non_responsive_host.append(cap_host)
            else:
                execute(host_ssh_availability_check, cap_host)
                execute(foreman_service_restart, host=cap_host)
        if non_responsive_host:
            logger.warning(str(non_responsive_host) + ' these are '
                                                      'non-responsive hosts')
            sys.exit(1)
    copy_ssh_key(sat_host, cap_hosts)
    # Dont run capsule upgrade requirements for n-1 capsule
    if upgradable_capsule:
        execute(sync_capsule_repos_to_upgrade, cap_hosts, host=sat_host)
        for cap_host in cap_hosts:
            execute(add_baseOS_repo, baseurl, host=cap_host)
        for cap_host in cap_hosts:
            logger.info('Capsule {} is ready for Upgrade'.format(cap_host))
    return cap_hosts


def satellite6_capsule_upgrade(cap_host, sat_host):
    """Upgrades capsule from existing version to latest version.

    :param string cap_host: Capsule hostname onto which the capsule upgrade
    will run
    :param string sat_host : Satellite hostname from which capsule certs are to
    be generated

    The following environment variables affect this command:

    CAPSULE_URL
        Optional, defaults to available capsule version in CDN.
        URL for capsule of latest compose to upgrade.
    FROM_VERSION
        Capsule current version, to disable repos while upgrading.
        e.g '6.1','6.0'
    TO_VERSION
        Capsule version to upgrade to and enable repos while upgrading.
        e.g '6.1','6.2'

    """
    logger.highlight('\n========== CAPSULE UPGRADE =================\n')
    from_version = os.environ.get('FROM_VERSION')
    setup_capsule_firewall()
    major_ver = distro_info()[1]
    ak_name = os.environ.get('CAPSULE_AK') if os.environ.get(
        'CAPSULE_AK') else os.environ.get('RHEV_CAPSULE_AK')
    run('subscription-manager register --org="Default_Organization" '
        '--activationkey={0} --force'.format(ak_name))
    disable_old_repos('rhel-{0}-server-satellite-capsule-{1}-rpms'.format(
        major_ver, from_version))
    # setup foreman-maintain
    setup_foreman_maintain_repo()
    # Check what repos are set

    nonfm_upgrade(satellite_upgrade=False,
                  cap_host=cap_host,
                  sat_host=sat_host)
    # Rebooting the capsule for kernel update if any
    reboot(160)
    host_ssh_availability_check(cap_host)
    # Check if Capsule upgrade is success
    upgrade_validation()


def satellite6_capsule_zstream_upgrade(cap_host):
    """Upgrades Capsule to its latest zStream version

    :param string cap_host: Capsule hostname onto which the capsule upgrade
    will run

    Note: For zstream upgrade both 'To' and 'From' version should be same

    FROM_VERSION
        Current satellite version which will be upgraded to latest version
    TO_VERSION
        Next satellite version to which satellite will be upgraded
    """
    logger.highlight('\n========== CAPSULE UPGRADE =================\n')
    from_version = os.environ.get('FROM_VERSION')
    to_version = os.environ.get('TO_VERSION')
    if not from_version == to_version:
        logger.warning('zStream Upgrade on Capsule cannot be performed as '
                       'FROM and TO versions are not same!')
        sys.exit(1)
    major_ver = distro_info()[1]
    if os.environ.get('CAPSULE_URL'):
        disable_old_repos('rhel-{0}-server-satellite-capsule-{1}-rpms'.format(
            major_ver, from_version))
    # Check what repos are set
    nonfm_upgrade(satellite_upgrade=False)
    # Rebooting the capsule for kernel update if any
    reboot(160)
    host_ssh_availability_check(cap_host)
    # Check if Capsule upgrade is success
    upgrade_validation()
