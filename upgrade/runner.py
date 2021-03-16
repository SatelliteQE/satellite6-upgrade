"""A set of upgrade tasks for upgrading Satellite, Capsule and Client.

Many commands are affected by environment variables. Unless stated otherwise,
all environment variables are required.
"""
import sys
from distutils.version import LooseVersion

from automation_tools import foreman_debug
from automation_tools.satellite6.log import LogAnalyzer
from fabric.api import env
from fabric.api import execute

from upgrade.capsule import satellite_capsule_setup
from upgrade.capsule import satellite_capsule_upgrade
from upgrade.capsule import satellite_capsule_zstream_upgrade
from upgrade.client import satellite6_client_setup
from upgrade.client import satellite6_client_upgrade
from upgrade.helpers import settings
from upgrade.helpers.logger import logger
from upgrade.helpers.tasks import check_necessary_env_variables_for_upgrade
from upgrade.helpers.tasks import post_upgrade_test_tasks
from upgrade.helpers.tasks import pre_upgrade_system_checks
from upgrade.helpers.tools import create_setup_dict
from upgrade.helpers.tools import get_sat_cap_version
from upgrade.helpers.tools import get_setup_data
from upgrade.satellite import satellite_setup
from upgrade.satellite import satellite_upgrade


# =============================================================================
# Satellite, Capsule and Client Upgrade
# =============================================================================

logger = logger()


def product_setup_for_upgrade_on_brokers_machine(product, os_version, satellite, capsule=None):
    """
    Sets up product(s) to perform upgrade on Satellite, Capsule and content host
    :param string product: The product name to setup before upgrade
    :param string os_version: The os version on which product is installed e.g: rhel6, rhel7
    :param satellite: brokers/users provided satellite
    :param capsule: brokers/users provided capsules, if the capsules count more than one then
     we keep them separate by a semicolon examplet: test1.xyz.com;test2.xyz.com
    """
    cap_hosts = None
    clients6 = clients7 = puppet_clients7 = puppet_clients6 = None
    env.disable_known_hosts = True
    check_necessary_env_variables_for_upgrade(product)

    clients6 = clients7 = puppet_clients7 = puppet_clients6 = None
    logger.info('Setting up Satellite ....')
    sat_host = satellite_setup(satellite)
    if product == 'capsule' or product == 'n-1' or product == 'longrun':
        cap_hosts = capsule.split()
        if len(cap_hosts) > 0:
            logger.info('Setting up Capsule ....')
            cap_hosts = satellite_capsule_setup(
                sat_host, cap_hosts, os_version, False if product == 'n-1' else True)
        else:
            logger.info(f'No capsule is available for capsule setup .... {cap_hosts}')
            sys.exit(1)
    if product == 'client' or product == 'longrun':
        logger.info('Setting up Clients ....')
        clients6, clients7, puppet_clients7, puppet_clients6 = satellite6_client_setup()

    setups_dict = {
        'sat_host': sat_host,
        'capsule_hosts': cap_hosts,
        'clients6': clients6,
        'clients7': clients7,
        'puppet_clients7': puppet_clients7,
        'puppet_clients6': puppet_clients6
    }
    create_setup_dict(setups_dict)


def product_upgrade(product, upgrade_type):
    """
    Used to drive the satellite, Capsule and Content-host upgrade based on their
    product type and upgrade type

    :param product: Product can be satellite, capsule, longrun and n-1

        1- If product is satellite then upgrade only satellite
        2- If product is capsule then upgrade satellite and capsule
        3- If product is client then upgrade satellite and client
        4- If product is longrun then upgrade satellite, capsule and client
        5- If product is n-1 then upgrades only satellite by keeping capsule at last
        z-stream released version

    :param upgrade_type: Upgrade_type can be satellite, capsule and client


    """
    def product_upgrade_satellite(sat_host):
        try:
            with LogAnalyzer(sat_host):
                current = execute(
                    get_sat_cap_version, 'sat', host=sat_host)[sat_host]
                if settings.upgrade.from_version != settings.upgrade.to_version:
                    execute(satellite_upgrade, host=sat_host)
                else:
                    execute(satellite_upgrade, True, host=sat_host)
                upgraded = execute(
                    get_sat_cap_version, 'sat', host=sat_host)[sat_host]
                check_upgrade_compatibility(upgrade_type, current, upgraded)
                execute(foreman_debug, f'satellite_{sat_host}', host=sat_host)
        except Exception:
            execute(foreman_debug, f'satellite_{sat_host}', host=sat_host)
            raise

    def product_upgrade_capsule(cap_host):
        try:
            with LogAnalyzer(cap_host):
                current = execute(get_sat_cap_version, 'cap', host=cap_host)[cap_host]
                if settings.upgrade.from_version != settings.upgrade.to_version:
                    execute(satellite_capsule_upgrade,
                            cap_host, sat_host, host=cap_host)
                elif settings.upgrade.from_version == settings.upgrade.to_version:
                    execute(satellite_capsule_zstream_upgrade,
                            cap_host, host=cap_host)
                upgraded = execute(
                    get_sat_cap_version, 'cap', host=cap_host)[cap_host]
                check_upgrade_compatibility(upgrade_type, current, upgraded)
                # Generate foreman debug on capsule postupgrade
                execute(foreman_debug, f'capsule_{cap_host}', host=cap_host)
                # Execute tasks as post upgrade tier1 tests
                # are dependent
            if product == 'longrun':
                post_upgrade_test_tasks(sat_host, cap_host)
        except Exception:
            execute(foreman_debug, f'capsule_{cap_host}', host=cap_host)
            raise

    def product_upgrade_client():
        clients6 = setup_dict['clients6']
        clients7 = setup_dict['clients7']
        puppet_clients7 = setup_dict['puppet_clients7']
        puppet_clients6 = setup_dict['puppet_clients6']
        satellite6_client_upgrade('rhel6', clients6)
        satellite6_client_upgrade('rhel7', clients7)
        satellite6_client_upgrade(
            'rhel7', puppet_clients7, puppet=True)
        satellite6_client_upgrade(
            'rhel6', puppet_clients6, puppet=True)

    env.disable_known_hosts = True
    check_necessary_env_variables_for_upgrade(product)
    logger.info(f'Performing UPGRADE FROM {settings.upgrade.from_version} TO '
                f'{settings.upgrade.to_version}')
    # Get the setup dict returned by setup_products_for_upgrade
    setup_dict = get_setup_data()
    sat_host = setup_dict['sat_host']
    cap_hosts = setup_dict['capsule_hosts']
    pre_upgrade_system_checks(cap_hosts)
    env['satellite_host'] = sat_host

    if upgrade_type == "satellite":
        product_upgrade_satellite(sat_host)
    elif (product == 'capsule' or product == 'longrun')\
            and upgrade_type == 'capsule':
        for cap_host in cap_hosts:
            settings.upgrade.capsule_hostname = cap_host
            product_upgrade_capsule(cap_host)
    elif (product == 'client' or product == 'longrun') and upgrade_type == 'client':
        product_upgrade_client()


def check_upgrade_compatibility(upgrade_type, base_version, target_version):
    """
    Use to check the setup is compatible with the selected version or not.
    :param upgrade_type: Upgrade type could be satellite, capsule.
    :param base_version: base version of the satellite, capsule.
    :param target_version: target version of the satellite or capsule.
    """
    if base_version:
        if LooseVersion(target_version) > LooseVersion(base_version):
            logger.highlight(f'The {upgrade_type} is upgraded from {base_version}'
                             f' to {target_version}')
        else:
            logger.highlight(
                f'The {upgrade_type} is NOT upgraded to next version. Now its {target_version}')
    else:
        logger.highlight(
            f'Unable to fetch previous version from {upgrade_type} but after upgrade capsule'
            f' is {target_version}.')
