import sys

from fabric.api import env
from fabric.api import execute
from packaging.version import Version

from upgrade.helpers import settings
from upgrade.helpers.constants.constants import CUSTOM_SAT_REPO
from upgrade.helpers.constants.constants import OS_REPOS
from upgrade.helpers.constants.constants import RH_CONTENT
from upgrade.helpers.logger import logger
from upgrade.helpers.tasks import enable_disable_repo
from upgrade.helpers.tasks import foreman_maintain_package_update
from upgrade.helpers.tasks import hammer_config
from upgrade.helpers.tasks import repository_setup
from upgrade.helpers.tasks import satellite_backup
from upgrade.helpers.tasks import subscribe
from upgrade.helpers.tasks import upgrade_using_foreman_maintain
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
            logger.highlight('zStream Upgrade on Satellite cannot be performed as FROM and TO'
                             ' versions are not same. Aborting...')
            sys.exit(1)

    # disable all repos and enable OS repos
    enable_disable_repo(disable_repos_name=['*'])
    enable_disable_repo(enable_repos_name=[repo['label'] for repo in OS_REPOS.values()])

    if settings.upgrade.distribution != 'cdn':
        settings.upgrade.whitelist_param = ', repositories-validate, repositories-setup'

    if settings.upgrade.distribution == 'cdn':
        enable_disable_repo(enable_repos_name=[RH_CONTENT['maintenance']['label']])
    else:
        for repo, repodata in CUSTOM_SAT_REPO.items():
            if Version(settings.upgrade.to_version) < Version('6.11'):
                if repo == 'satclient':
                    continue
            else:
                if repo == 'sattools':
                    continue
            repository_setup(**repodata)
        foreman_maintain_package_update()

    upgrade_using_foreman_maintain()

    # Rebooting the satellite for kernel update if any
    if settings.upgrade.satellite_capsule_setup_reboot:
        reboot(180)
    host_ssh_availability_check(env.get('satellite_host'))
    # Test the Upgrade is successful
    upgrade_validation()
    if settings.upgrade.satellite_backup:
        satellite_backup()
