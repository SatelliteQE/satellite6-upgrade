import sys

from automation_tools import setup_capsule_firewall
from fabric.api import execute
from fabric.api import run
from fabric.api import settings as fabric_settings
from packaging.version import Version

from upgrade.helpers import settings
from upgrade.helpers.constants.constants import RH_CONTENT
from upgrade.helpers.logger import logger
from upgrade.helpers.tasks import add_baseOS_repos
from upgrade.helpers.tasks import capsule_certs_update
from upgrade.helpers.tasks import capsule_sync
from upgrade.helpers.tasks import create_capsule_ak
from upgrade.helpers.tasks import enable_disable_repo
from upgrade.helpers.tasks import foreman_maintain_package_update
from upgrade.helpers.tasks import http_proxy_config
from upgrade.helpers.tasks import sync_capsule_repos_to_satellite
from upgrade.helpers.tasks import update_capsules_to_satellite
from upgrade.helpers.tasks import upgrade_using_foreman_maintain
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
            settings.repos.sattools_repo[settings.upgrade.os] = None
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


def satellite_capsule_upgrade(cap_host, sat_host):
    """Upgrades capsule from existing version to latest version.

    :param string cap_host: Capsule hostname onto which the capsule upgrade
    will run
    :param string sat_host : Satellite hostname from which capsule certs are to
    be generated

    """
    logger.highlight('\n========== CAPSULE UPGRADE =================\n')
    # Check the capsule sync before upgrade.
    logger.info("Check the capsule sync after satellite upgrade to verify sync operation "
                "with n-1 combination")
    execute(capsule_sync, cap_host, host=sat_host)
    wait_untill_capsule_sync(cap_host)
    setup_capsule_firewall()
    os_ver = int(settings.upgrade.os.strip('rhel'))
    ak_name = settings.upgrade.capsule_ak[settings.upgrade.os]
    run(f'subscription-manager register '
        f'--org="Default_Organization" --activationkey={ak_name} --force')
    logger.info(f'Activation key {ak_name} enabled all capsule repositories')
    run('subscription-manager repos --list')
    maintenance_repo = RH_CONTENT['maintenance']['label']
    capsule_repo = RH_CONTENT['capsule']['label']
    client = 'client' if Version(settings.upgrade.to_version) > Version('6.10') else 'tools'
    client_repo = RH_CONTENT[client]['label']

    with fabric_settings(warn_only=True):
        if os_ver == 7:
            enable_disable_repo(enable_repos_name=[RH_CONTENT['ansible']['label']])
        if settings.upgrade.distribution == 'cdn':
            enable_disable_repo(enable_repos_name=[capsule_repo, maintenance_repo, client_repo])
        else:
            enable_disable_repo(disable_repos_name=[maintenance_repo])

        if settings.upgrade.from_version != settings.upgrade.to_version:
            enable_disable_repo(disable_repos_name=[capsule_repo])

    foreman_maintain_package_update()
    if settings.upgrade.from_version == '6.10':
        # capsule certs regeneration required prior 6.11 ystream capsule upgrade BZ#2049893
        execute(capsule_certs_update, cap_host, host=sat_host)
    upgrade_using_foreman_maintain(satellite=False)
    # Rebooting the capsule for kernel update if any
    reboot(160)
    host_ssh_availability_check(cap_host)
    # Check if Capsule upgrade is success
    upgrade_validation(upgrade_type="capsule", satellite_services_action="restart")
    # Check the capsule sync after upgrade.
    logger.info("check the capsule sync after capsule upgrade")
    execute(capsule_sync, cap_host, host=sat_host)
    wait_untill_capsule_sync(cap_host)


def satellite_capsule_zstream_upgrade(cap_host):
    """Upgrades Capsule to its latest zStream version

    :param string cap_host: Capsule hostname onto which the capsule upgrade
    will run

    """
    logger.highlight('\n========== CAPSULE UPGRADE =================\n')
    if settings.upgrade.from_version != settings.upgrade.to_version:
        logger.highlight('Z-stream Capsule Upgrade cannot be performed '
                         'when FROM and TO versions differ. Aborting...')
        sys.exit(1)
    os_ver = int(settings.upgrade.os.strip('rhel'))
    ak_name = settings.upgrade.capsule_ak[settings.upgrade.os]
    run(f'subscription-manager register --org="Default_Organization" --activationkey={ak_name} '
        '--force')
    logger.info(f'Activation key {ak_name} enabled all capsule repositories')
    run('subscription-manager repos --list')

    client = 'client' if Version(settings.upgrade.to_version) > Version('6.10') else 'tools'
    capsule_repos = [
        RH_CONTENT[client]['label'],
        RH_CONTENT['capsule']['label'],
        RH_CONTENT['maintenance']['label']
    ]
    with fabric_settings(warn_only=True):
        if os_ver == 7:
            enable_disable_repo(enable_repos_name=[RH_CONTENT['ansible']['label']])
        if settings.upgrade.distribution == "cdn":
            enable_disable_repo(enable_repos_name=capsule_repos)
        else:
            enable_disable_repo(disable_repos_name=capsule_repos)
    # Check what repos are set
    # setup_foreman_maintain_repo()
    upgrade_using_foreman_maintain(satellite=False)
    # Rebooting the capsule for kernel update if any
    if settings.upgrade.satellite_capsule_setup_reboot:
        reboot(160)
    host_ssh_availability_check(cap_host)
    # Check if Capsule upgrade is success
    upgrade_validation(upgrade_type="capsule", satellite_services_action="restart")
