import sys

from fabric.api import execute
from fabric.api import run

from upgrade.helpers import settings
from upgrade.helpers.logger import logger
from upgrade.helpers.tasks import add_baseOS_repos
from upgrade.helpers.tasks import capsule_sync
from upgrade.helpers.tasks import create_capsule_ak
from upgrade.helpers.tasks import foreman_maintain_self_upgrade
from upgrade.helpers.tasks import foreman_maintain_upgrade
from upgrade.helpers.tasks import http_proxy_config
from upgrade.helpers.tasks import setup_capsule_maintenance_repo
from upgrade.helpers.tasks import setup_capsule_repo
from upgrade.helpers.tasks import sync_capsule_repos_to_satellite
from upgrade.helpers.tasks import update_capsules_to_satellite
from upgrade.helpers.tasks import upgrade_validation
from upgrade.helpers.tasks import wait_untill_capsule_sync
from upgrade.helpers.tasks import yum_repos_cleanup
from upgrade.helpers.tools import copy_ssh_key
from upgrade.helpers.tools import host_pings
from upgrade.helpers.tools import host_ssh_availability_check
from upgrade.helpers.tools import reboot

logger = logger()


def satellite_capsule_setup(satellite_host, capsule_hosts, os_version,
                            upgradable_capsule=True):
    """
    Setup all pre-requisites for user provided capsule

    :param satellite_host: Satellite hostname to which the capsule registered
    :param capsule_hosts: List of capsule which mapped with satellite host
    :param os_version: The OS version onto which the capsule installed e.g: rhel6, rhel7, rhel8
    :param upgradable_capsule:Whether to setup capsule to be able to upgrade in future
    :return: capsule_hosts
    """
    os_repos = settings.repos[f'{os_version}_os']
    if isinstance(os_repos, str):
        os_repos = {os_version: os_repos}
    non_responsive_hosts = []
    for cap_host in capsule_hosts:
        if not host_pings(cap_host):
            non_responsive_hosts.append(cap_host)
        else:
            execute(host_ssh_availability_check, cap_host)
        if non_responsive_hosts:
            logger.highlight(f'{non_responsive_hosts} these are non-responsive hosts. Aborting...')
            sys.exit(1)
        copy_ssh_key(satellite_host, capsule_hosts)
    if upgradable_capsule:
        if settings.upgrade.distribution == "cdn":
            settings.repos.capsule_repo = None
            settings.repos.satclient_repo[settings.upgrade.os] = None
            settings.repos.satmaintenance_repo = None
        new_ak_status = execute(create_capsule_ak, host=satellite_host)
        execute(update_capsules_to_satellite, capsule_hosts, host=satellite_host)
        if settings.upgrade.upgrade_with_http_proxy:
            execute(http_proxy_config, capsule_hosts, host=satellite_host)
        if False in new_ak_status.values():
            execute(sync_capsule_repos_to_satellite, capsule_hosts, host=satellite_host)
            for cap_host in capsule_hosts:
                settings.upgrade.capsule_hostname = cap_host
                execute(add_baseOS_repos, **os_repos, host=cap_host)
                execute(yum_repos_cleanup, host=cap_host)
                logger.info(f'Capsule {cap_host} is ready for Upgrade')
        return capsule_hosts


def satellite_capsule_upgrade(cap_host, sat_host, zstream=False):
    """Upgrades capsule from existing version to latest version.

    :param string cap_host: Capsule hostname onto which the capsule upgrade
    will run
    :param string sat_host : Satellite hostname from which capsule certs are to
    be generated

    """
    logger.highlight('\n========== CAPSULE UPGRADE =================\n')
    if zstream:
        if not settings.upgrade.from_version == settings.upgrade.to_version:
            logger.highlight('Z-Stream Capsule Upgrade cannot be performed '
                             'when FROM and TO versions differ. Aborting...')
            sys.exit(1)
    # Check the capsule sync before upgrade.
    logger.info("Checking the capsule sync after satellite upgrade to verify sync operation ")
    execute(capsule_sync, cap_host, host=sat_host)
    wait_untill_capsule_sync(cap_host)

    ak_name = settings.upgrade.capsule_ak[settings.upgrade.os]
    run(f'subscription-manager register '
        f'--org="Default_Organization" --activationkey={ak_name} --force')
    logger.info(f'Activation key {ak_name} enabled all capsule repositories')
    run('subscription-manager repos --list')

    # Update foreman_maintain by self-upgrade
    setup_capsule_maintenance_repo()
    foreman_maintain_self_upgrade(zstream=zstream, fetch_content_from_sat=True)

    # Upgrade the Capsule
    setup_capsule_repo()
    foreman_maintain_upgrade(satellite=False)

    # Rebooting the capsule for kernel update if any
    reboot(160)
    host_ssh_availability_check(cap_host)

    # Check if Capsule upgrade is success
    upgrade_validation(upgrade_type="capsule", satellite_services_action="restart")
    # Check the capsule sync after upgrade.
    logger.info("Checking the capsule sync after capsule upgrade")
    execute(capsule_sync, cap_host, host=sat_host)
    wait_untill_capsule_sync(cap_host)
