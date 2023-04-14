import sys

from fabric.api import env
from fabric.api import execute
from fabric.api import hide

from upgrade.helpers import settings
from upgrade.helpers.constants.constants import OS_REPOS
from upgrade.helpers.logger import logger
from upgrade.helpers.tasks import enable_disable_repo
from upgrade.helpers.tasks import foreman_maintain_self_upgrade
from upgrade.helpers.tasks import foreman_maintain_upgrade
from upgrade.helpers.tasks import hammer_config
from upgrade.helpers.tasks import satellite_backup
from upgrade.helpers.tasks import setup_maintenance_repo
from upgrade.helpers.tasks import setup_satellite_repo
from upgrade.helpers.tasks import subscribe
from upgrade.helpers.tasks import upgrade_validation
from upgrade.helpers.tasks import yum_repos_cleanup
from upgrade.helpers.tools import host_ssh_availability_check
from upgrade.helpers.tools import reboot

logger = logger()


def satellite_setup(satellite_host):
    """
    The purpose of this method to make the satellite ready for upgrade.
    :param satellite_host:
    :return: satellite_host
    """
    execute(host_ssh_availability_check, satellite_host)
    execute(yum_repos_cleanup, host=satellite_host)
    execute(subscribe, host=satellite_host)
    env['satellite_host'] = satellite_host
    settings.upgrade.satellite_hostname = satellite_host
    execute(hammer_config, host=satellite_host)
    logger.info(f'Satellite {satellite_host} is ready for Upgrade!')
    return satellite_host


def satellite_upgrade(zstream=False):
    """This function is used to perform the satellite upgrade of two type based on
    their passed parameter.
    :param zstream:
    """
    logger.highlight('\n========== SATELLITE UPGRADE =================\n')
    if zstream:
        if not settings.upgrade.from_version == settings.upgrade.to_version:
            logger.highlight('Z-Stream Satellite upgrade cannot be performed '
                             'when FROM and TO versions differ. Aborting...')
            sys.exit(1)

    # disable all repos and enable OS repos
    with hide('stdout'):
        enable_disable_repo(disable_repos_name='*')
    enable_disable_repo(enable_repos_name=[repo['label'] for repo in OS_REPOS.values()])

    # Update foreman_maintain by self-upgrade
    setup_maintenance_repo()
    foreman_maintain_self_upgrade(zstream=zstream)

    # Upgrade the Satellite
    setup_satellite_repo()
    foreman_maintain_upgrade()

    # Rebooting the satellite for kernel update if any
    if settings.upgrade.satellite_capsule_setup_reboot:
        reboot(180)
    host_ssh_availability_check(env.get('satellite_host'))

    # Test the Upgrade is successful
    upgrade_validation()
    if settings.upgrade.satellite_backup:
        satellite_backup()
