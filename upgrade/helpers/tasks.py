"""A set of tasks to help upgrade Satellite and Capsule.

Many commands are affected by environment variables. Unless stated otherwise,
all environment variables are required.
"""
import os
import re
import socket
import sys
import time
from datetime import datetime
from random import randrange

import requests
from automation_tools import setup_alternate_capsule_ports
from automation_tools import setup_avahi_discovery
from automation_tools import setup_capsule_firewall
from automation_tools import setup_fake_manifest_certificate
from automation_tools import setup_foreman_discovery
from automation_tools import setup_rhv_ca
from automation_tools.repository import disable_repos
from automation_tools.repository import enable_repos
from automation_tools.satellite6.capsule import generate_capsule_certs
from automation_tools.utils import get_discovery_image
from automation_tools.utils import update_packages
from fabric.api import env
from fabric.api import execute
from fabric.api import hide
from fabric.api import put
from fabric.api import run
from fabric.api import settings as fabric_settings
from fabric.api import warn_only
from fabric.context_managers import shell_env
from fauxfactory import gen_string
from nailgun import entities

from upgrade.helpers import nailgun_conf
from upgrade.helpers import settings
from upgrade.helpers.constants.constants import CAPSULE_SUBSCRIPTIONS
from upgrade.helpers.constants.constants import CUSTOM_CONTENTS
from upgrade.helpers.constants.constants import CUSTOM_SAT_REPO
from upgrade.helpers.constants.constants import DEFAULT_LOCATION
from upgrade.helpers.constants.constants import DEFAULT_ORGANIZATION
from upgrade.helpers.constants.constants import DEFAULT_ORGANIZATION_LABEL
from upgrade.helpers.constants.constants import RHEL_CONTENTS
from upgrade.helpers.docker import (
    attach_subscription_to_host_from_content_host
)
from upgrade.helpers.logger import logger
from upgrade.helpers.tools import call_entity_method_with_timeout
from upgrade.helpers.tools import host_pings
if sys.version_info[0] == 2:
    from StringIO import StringIO  # (import-error) pylint:disable=F0401
else:  # pylint:disable=F0401,E0611
    from io import StringIO

logger = logger()


class ProductNotFound(Exception):
    """Raise if the product you are searching is not found"""


def update_capsules_to_satellite(capsules):
    """
    This function used to update the required details of the capsule.
    :param capsules:
    """
    for capsule in capsules:
        for attempt in range(0, 4):
            try:
                smart_proxy = (
                    entities.SmartProxy(nailgun_conf).search(query={
                        'search': f'name={capsule}'
                    })[0].read()
                )
                logger.info(f"object {smart_proxy}")
                break
            except IndexError as exp:
                # listing the all available capsule
                run("hammer capsule list")
                logger.warn(f"No capsule availble in the capsule list retry {attempt} "
                            f"after exception: {exp}")
                if attempt == 3:
                    logger.highlight("The searched capsule unavailable in the capsule list. "
                                     "Aborting...")
                    sys.exit(1)
                time.sleep(10)
        loc = entities.Location(nailgun_conf).search(
            query={'search': f'name="{DEFAULT_LOCATION}"'}
        )[0]
        org = entities.Organization(nailgun_conf).search(
            query={'search': f'name="{DEFAULT_ORGANIZATION}"'}
        )[0]
        try:
            smart_proxy.location.append(entities.Location(nailgun_conf, id=loc.id))
            smart_proxy.update(['location'])
            smart_proxy.organization.append(entities.Organization(nailgun_conf, id=org.id))
            smart_proxy.update(['organization'])
            logger.info("for Capsule default location and organization updated successfully")
        except requests.exceptions.HTTPError as err:
            logger.warn(err)
        with fabric_settings(warn_only=True):
            result = run(f"hammer capsule content add-lifecycle-environment --organization-id "
                         f"{org.id} --lifecycle-environment 'Dev'  --name {capsule}")
            if result.return_code == 0:
                logger.info("for Capsule 'Dev' lifecycle environment added successfully")
            else:
                logger.warn(result)


def http_proxy_config(capsule_hosts):
    """
    Set the http-proxy on the satellite server.
    :param capsule_hosts: list of capsule host
    """
    loc = entities.Location(nailgun_conf).search(
        query={'search': f'name="{DEFAULT_LOCATION}"'})[0]
    org = entities.Organization(nailgun_conf).search(
        query={'search': f'name="{DEFAULT_ORGANIZATION}"'})[0]
    name = gen_string('alpha', 15)
    proxy_url = settings.http_proxy.un_auth_proxy_url
    entities.HTTPProxy(
        nailgun_conf,
        name=f"{name}", url=f"{proxy_url}",
        organization=f"{org.id}", location=f"{loc.id}").create()
    prop_name = {
        'http_proxy': f"{proxy_url}",
        'content_default_http_proxy': f"{name}"
    }
    for key, value in prop_name.items():
        setting_object = entities.Setting(nailgun_conf).search(query={'search': f'name={key}'})[0]
        setting_object.value = f"{value}"
        setting_object.update({'value'})

    for capsule in capsule_hosts:
        with fabric_settings(warn_only=True):
            result = run(f"hammer setting set --name "
                         f"http_proxy_except_list --value '[\"{capsule}\"]'")
            if result.return_code == 0:
                logger.info(f"{capsule} capsule added in http-proxy-except-host-list for")
            else:
                logger.warn(result)


def check_necessary_env_variables_for_upgrade(product):
    """Checks if necessary Environment Variables are provided
    :param string product: The product name to upgrade
    """
    failure = []
    # The upgrade product
    if product not in settings.upgrade.products:
        failure.append('Product name should be one of {0}.'.format(
            ', '.join(settings.upgrade.products)))
    # Check If OS is set for creating an instance name in rhevm
    if not settings.upgrade.os:
        failure.append('Please provide OS version as rhel7 or rhel6, '
                       'And retry !')
    if failure:
        logger.highlight("The provided information to perform the upgrade is in-sufficient. "
                         "Aborting...")
        logger.warning('Cannot Proceed Upgrade as:')
        for msg in failure:
            logger.warning(msg)
        sys.exit(1)
    return True


def sync_capsule_repos_to_satellite(capsules):
    """This syncs capsule repo in Satellite server and also attaches
    the capsule repo subscription to each capsule
    :param list capsules: The list of capsule hostnames to which new capsule
    repo subscription will be attached
    Following environment variable affects this function:
    CAPSULE_RPO
        capsule repo from latest satellite compose.
        If not provided, capsule repo from Red Hat repositories will be enabled
    CAPSULE_TOOLS_REPO
        capsule_tools_repo repo from latest satellite compose.
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
    RHEV upgrade Env Vars:
    RHEV_CAPSULE_AK
        The AK name used in capsule subscription
    """
    logger.info('Syncing latest capsule repos in Satellite ...')
    os_ver = settings.upgrade.os[-1]
    capsule_repo = settings.repos.capsule_repo
    sat_tools_repo = settings.repos.sattools_repo[settings.upgrade.os]
    capsule_ak = settings.upgrade.capsule_ak[settings.upgrade.os]
    if capsule_ak is None:
        logger.highlight("The AK name is not provided for Capsule upgrade. Aborting...")
        sys.exit(1)
    org = entities.Organization(nailgun_conf, id=1).read()
    logger.info("Refreshing the attached manifest")
    entities.Subscription(nailgun_conf).refresh_manifest(data={'organization_id': org.id},
                                                         timeout=5000)
    ak = entities.ActivationKey(nailgun_conf, organization=org).search(
        query={'search': f'name={capsule_ak}'})[0]
    add_satellite_subscriptions_in_capsule_ak(ak, org)
    logger.info(f"activation key {capsule_ak} used for capsule subscription and "
                f"it found on the satellite")
    cv = ak.content_view.read()
    lenv = ak.environment.read()
    # Fix dead pulp tasks
    if os_ver == '6':
        run('for i in pulp_resource_manager pulp_workers pulp_celerybeat; '
            'do service $i restart; done')
    logger.info(f"capsule subscription to AK {ak.name} has added successfully")
    add_subscription_for_capsule(ak, org)
    # Publishing and promoting the CV with all newly added capsule, capsuletools,
    # rhscl and server repos combine
    logger.info("content view publish operation started successfully")
    try:
        start_time = job_execution_time("CV_Publish")
        call_entity_method_with_timeout(cv.read().publish, timeout=5000)
        job_execution_time(f"content view {cv.name} publish operation(In past time-out value "
                           f"was 2500 but in current execution we set it 5000)", start_time)
    except Exception as exp:
        logger.critical(f"content view {cv.name} publish failed with exception {exp}")
        # Fix of 1770940, 1773601
        logger.info(f"resuming the cancelled content view {cv.name} publish task")
        resume_failed_task()
    logger.info(f"content view {cv.name} published successfully")
    published_ver = entities.ContentViewVersion(
        nailgun_conf, id=max([cv_ver.id for cv_ver in cv.read().version])).read()
    logger.info(f"content view {cv.name} promotion started successfully")
    published_ver.promote(data={'environment_ids': [lenv.id], 'force': False})
    logger.info(f"content view {cv.name} promotion completed successfully")
    # Add capsule and tools custom prod subscription to capsules
    if capsule_repo:
        add_custom_product_subscription_to_hosts(
            CUSTOM_CONTENTS['capsule']['prod'], capsules)
    if sat_tools_repo:
        add_custom_product_subscription_to_hosts(
            CUSTOM_CONTENTS['capsule_tools']['prod'], capsules)


def sync_capsule_subscription_to_capsule_ak(org):
    """
    Task to sync latest capsule repo which will later be used for capsule upgrade.
    :param org: `nailgun.entities.ActivationKey` used for capsule subscription
    """
    from_version = settings.upgrade.from_version
    to_version = settings.upgrade.to_version
    arch = 'x86_64'
    # If custom capsule repo is not given then
    # enable capsule repo from Redhat Repositories
    if settings.repos.capsule_repo:
        try:
            cap_product = entities.Product(
                nailgun_conf, name=CUSTOM_CONTENTS['capsule']['prod'], organization=org).create()
        except Exception as ex:
            logger.warn(ex)
            cap_product = entities.Product(nailgun_conf, organization=org).search(
                query={"search": f'name={CUSTOM_CONTENTS["capsule"]["prod"]}'}
            )[0]
        try:
            cap_repo = entities.Repository(
                nailgun_conf,
                name=CUSTOM_CONTENTS['capsule']['repo'],
                product=cap_product,
                url=settings.repos.capsule_repo,
                organization=org,
                content_type='yum',
            ).create()
        except Exception as ex:
            logger.warn(ex)
            cap_repo = entities.Repository(
                nailgun_conf, organization=org, product=cap_product
            ).search(query={"search": f'name={CUSTOM_CONTENTS["capsule"]["repo"]}'})[0]
        logger.info("capsule repository {} created successfully for product {}".
                    format(CUSTOM_CONTENTS['capsule']['repo'],
                           CUSTOM_CONTENTS['capsule']['prod']))
    else:
        # y-stream cdn upgrade support
        if from_version != to_version:
            capsule_prod = RHEL_CONTENTS['capsule']['prod']
            capsule_name = RHEL_CONTENTS['capsule']['repofull']
            with fabric_settings(warn_only=True):
                result = run(f'hammer repository-set enable --product '
                             f'"{capsule_prod}" --basearch {arch} --releasever {to_version}'
                             f' --name "{capsule_name}" '
                             f'--organization-id {org.id}')
                if result.return_code == 0:
                    logger.info("capsule repo enabled successfully")
                elif result.return_code == 70:
                    logger.info("capsule repo already enabled so the error code 70 is expected")
                else:
                    logger.warn(result)

        cap_product = entities.Product(
            nailgun_conf,
            name=RHEL_CONTENTS['capsule']['prod'],
            organization=org
        ).search(query={'per_page': 100})[0]
        logger.info(f"rhel capsule product {RHEL_CONTENTS['capsule']['prod']} is "
                    f"found enabled.")
        cap_reposet = entities.RepositorySet(
            nailgun_conf, name=RHEL_CONTENTS['capsule']['repofull'], product=cap_product
        ).search()[0]
        logger.info("entities of repository {} search completed successfully".
                    format(RHEL_CONTENTS['capsule']['repofull']))
        try:
            cap_reposet.enable(
                data={
                    'basearch': 'x86_64', 'releasever': '7Server', 'organization_id': org.id
                })
        except requests.exceptions.HTTPError as exp:
            logger.warn(exp)
        cap_repo = entities.Repository(
            nailgun_conf, name=RHEL_CONTENTS['capsule']['repo']).search(
            query={'organization_id': org.id, 'per_page': 100}
        )[0]
        logger.info(f"capsule repository's repofull {RHEL_CONTENTS['capsule']['repofull']} "
                    f"search completed successfully")

    logger.info(f"entities repository sync operation started successfully "
                f"for name {cap_repo.name}")
    start_time = job_execution_time("entity repository sync")
    # Expected value 2500
    try:
        call_entity_method_with_timeout(
            entities.Repository(nailgun_conf, id=cap_repo.id).sync, timeout=4000)
        job_execution_time(
            f"entity repository {cap_repo.name} sync (In past time-out value was "
            f"2500 but in current execution we set it 4000)", start_time)
    except Exception as exp:
        logger.warn(f"Capsule repository sync failed with exception: {exp}")
        repos_sync_failure_remiediation(org, cap_repo, timeout=4000)
    job_execution_time(f"entity repository {cap_repo.name} sync (In past time-out value was "
                       f"2500 but in current execution we set it 4000)", start_time)
    logger.info(f"entities repository sync operation completed successfully "
                f"for name {cap_repo.name}")
    if settings.repos.capsule_repo:
        cap_repo.repo_id = CUSTOM_CONTENTS['capsule']['repo']
    else:
        cap_repo.repo_id = RHEL_CONTENTS['capsule']['label']
    return cap_repo


def sync_rh_repos_to_satellite(org):
    """
    Task to sync redhat repositories which will later be used for capsule upgrade.
    :param org: ``nailgun.entities.Organization` entity of capsule
    :returns tuple: scl and server nailgun object
    """
    arch = 'x86_64'
    # Enable rhscl repository
    scl_product = entities.Product(
        nailgun_conf, name=RHEL_CONTENTS['rhscl_sat64']['prod'], organization=org
    ).search(query={'per_page': 100})[0]
    logger.info(f"red hat software collection for product "
                f"{RHEL_CONTENTS['rhscl_sat64']['prod']} is enabled")
    scl_reposet = entities.RepositorySet(
        nailgun_conf, name=RHEL_CONTENTS['rhscl']['repo'], product=scl_product
    ).search()[0]
    logger.info(f"red hat software collection repo "
                f"{RHEL_CONTENTS['rhscl']['repo']} is enabled")
    try:
        scl_reposet.enable(
            data={'basearch': arch, 'releasever': '7Server', 'organization_id': org.id})
        logger.info("red hat software collection repository enabled successfully")
    except requests.exceptions.HTTPError as exp:
        logger.warn(exp)
    time.sleep(20)
    # Sync enabled Repo from cdn
    scl_repo = entities.Repository(
        nailgun_conf, name=RHEL_CONTENTS['rhscl']['repofull']).search(
        query={'organization_id': org.id, 'per_page': 100}
    )[0]
    start_time = job_execution_time("Repository sync")
    try:
        call_entity_method_with_timeout(
            entities.Repository(nailgun_conf, id=scl_repo.id).sync, timeout=3500
        )
    except Exception as exp:
        logger.warn(f"RHCL repository sync failed with exception: {exp}")
        repos_sync_failure_remiediation(org, scl_repo, timeout=3500)
    job_execution_time(f"repository {scl_repo.name} sync (In past time-out value was 2000 "
                       f"but in current execution we set it 3500) takes", start_time)

    # Enable RHEL 7 Server repository
    server_product = entities.Product(
        nailgun_conf, name=RHEL_CONTENTS['server']['prod'], organization=org).\
        search(query={'per_page': 100})[0]
    logger.info(f"product {RHEL_CONTENTS['server']['prod']} is enable")
    server_reposet = entities.RepositorySet(
        nailgun_conf, name=RHEL_CONTENTS['server']['repo'], product=server_product).search()[0]
    logger.info(f"repository {RHEL_CONTENTS['server']['repo']} is enabled")
    try:
        server_reposet.enable(
            data={'basearch': arch, 'releasever': '7Server', 'organization_id': org.id})
        logger.info(f"repository enabled successfully for base arch {server_reposet.name}")
    except requests.exceptions.HTTPError as exp:
        logger.warn(exp)
    time.sleep(20)
    # Sync enabled Repo from cdn
    server_repo = entities.Repository(
        nailgun_conf, name=RHEL_CONTENTS['server']['repofull']
    ).search(query={'organization_id': org.id, 'per_page': 100})[0]
    logger.info(f"entities repository sync operation started successfully"
                f" for name {server_repo.name}")
    start_time = job_execution_time("Repository sync")
    try:
        call_entity_method_with_timeout(
            entities.Repository(nailgun_conf, id=server_repo.id).sync, timeout=6000)
    except Exception as exp:
        logger.warn(f"RH Server repository sync failed with exception: {exp}")
        repos_sync_failure_remiediation(org, server_repo, timeout=6000)
    job_execution_time(f"repository {server_repo.name} sync (In past time-out value was 3600 "
                       f"but in current execution we set it 6000) takes", start_time)
    logger.info(f"entities repository sync operation completed successfully"
                f" for name {server_repo.name}")
    scl_repo.repo_id = RHEL_CONTENTS['rhscl']['label']
    server_repo.repo_id = RHEL_CONTENTS['server']['label']
    return scl_repo, server_repo


def sync_ansible_repo_to_satellite(org):
    """
    Task to sync `RH Ansible Engine` used for capsule upgrade.
    :param org: `nailgun.entities.Organization` entity where the repo will be synced
    :return: `nailgun.entities.repository` entity for ansible
    """
    # Enable the repository
    ansible_product = entities.Product(
        nailgun_conf, name=RHEL_CONTENTS['ansible']['prod'], organization=org
    ).search(query={'per_page': 100})[0]
    ansible_reposet = entities.RepositorySet(
        nailgun_conf, name=RHEL_CONTENTS['ansible']['repo'], product=ansible_product
    ).search()[0]
    try:
        ansible_reposet.enable(
            data={'basearch': 'x86_64', 'releasever': '7Server', 'organization_id': org.id})
        logger.info("RH Ansible Engine repository enabled successfully")
    except requests.exceptions.HTTPError as exp:
        logger.warn(exp)
    time.sleep(20)
    # Sync the repo from CDN
    ansible_repo = entities.Repository(
        nailgun_conf, name=RHEL_CONTENTS['ansible']['repofull']).search(
        query={'organization_id': org.id, 'per_page': 100}
    )[0]
    try:
        call_entity_method_with_timeout(
            entities.Repository(nailgun_conf, id=ansible_repo.id).sync, timeout=600)
        logger.info("RH Ansible Engine repository synced successfully")
    except requests.exceptions.HTTPError as exp:
        logger.warn(f"RH Ansible engine repository sync failed with exception: {exp}")
        repos_sync_failure_remiediation(org, ansible_repo, timeout=600)
    ansible_repo.repo_id = RHEL_CONTENTS['ansible']['label']
    return ansible_repo


def sync_sattools_repos_to_satellite_for_capsule(org):
    """
    Creates custom / Enables RH Tools repo on satellite and syncs for capsule upgrade
    :param org: `nailgun.entities.Organization` entity of capsule
    :return: `nailgun.entities.repository` entity for capsule
    """
    arch = 'x86_64'
    from_version = settings.upgrade.from_version
    to_version = settings.upgrade.to_version
    sat_tools_repo = settings.repos.sattools_repo[settings.upgrade.os]
    if sat_tools_repo:
        try:
            sattools_product = entities.Product(
                nailgun_conf,
                name=CUSTOM_CONTENTS['capsule_tools']['prod'],
                organization=org
            ).create()
        except Exception as ex:
            logger.warn(ex)
            sattools_product = entities.Product(nailgun_conf, organization=org).search(
                query={"search": f'name={CUSTOM_CONTENTS["capsule_tools"]["prod"]}'}
            )[0]
        try:
            sattools_repo = entities.Repository(
                nailgun_conf,
                name=CUSTOM_CONTENTS['capsule_tools']['repo'],
                product=sattools_product,
                url=sat_tools_repo,
                organization=org,
                content_type='yum',
            ).create()
        except Exception as ex:
            logger.warn(ex)
            sattools_repo = entities.Repository(
                nailgun_conf, organization=org, product=sattools_product
            ).search(query={"search": f'name={CUSTOM_CONTENTS["capsule_tools"]["repo"]}'})[0]
        logger.info(f"custom tools product {CUSTOM_CONTENTS['capsule_tools']['prod']} "
                    f"and repository {CUSTOM_CONTENTS['capsule_tools']['repo']} created"
                    f" from satellite tools url")
    else:
        if from_version != to_version:
            tools_name = RHEL_CONTENTS['tools']['repofull']
            tools_prod = RHEL_CONTENTS['tools']['prod']
            with fabric_settings(warn_only=True):
                result = run(f'hammer repository-set enable --product "{tools_prod}" '
                             f'--basearch {arch} --releasever {to_version} --name '
                             f'"{tools_name}" --organization-id {org.id}')
                if result.return_code == 0:
                    logger.info("sattools repo enabled successfully")
                elif result.return_code == 70:
                    logger.info("sattools repo already enabled so the error code 70 is "
                                "expected")
                else:
                    logger.warn(result)

        sattools_product = entities.Product(
            nailgun_conf, name=RHEL_CONTENTS['tools']['prod'], organization=org
        ).search(query={'per_page': 100})[0]
        sat_reposet = entities.RepositorySet(
            nailgun_conf, name=RHEL_CONTENTS['tools']['repofull'], product=sattools_product
        ).search()[0]
        logger.info(f"check the capsule tool's product"
                    f" {RHEL_CONTENTS['tools']['prod']} and"
                    f" repository {RHEL_CONTENTS['tools']['repo']} "
                    f"availability on the setup")
        try:
            sat_reposet.enable(data={'basearch': arch, 'organization_id': org.id})
            logger.info(f"satellite tools repository enabled successfully for "
                        f"{sat_reposet.name}")
        except requests.exceptions.HTTPError as exp:
            logger.warn(exp)
        time.sleep(5)
        sattools_repo = entities.Repository(
            nailgun_conf, name=RHEL_CONTENTS['tools']['repo']
        ).search(query={'organization_id': org.id, 'per_page': 100})[0]
        logger.info(f"entities repository search completed successfully for sattools "
                    f"repo {RHEL_CONTENTS['tools']['repofull']}")
    logger.info("entities repository sync started successfully for capsule repo name {}".
                format(sattools_repo.name))
    start_time = job_execution_time("Entities repository sync")
    try:
        call_entity_method_with_timeout(
            entities.Repository(nailgun_conf, id=sattools_repo.id).sync, timeout=5000)
    except Exception as exp:
        logger.warn(f"RH Satellite tool repository sync failed with exception: {exp}")
        repos_sync_failure_remiediation(org, sattools_repo, timeout=5000)

    job_execution_time(f"entities repository {sattools_repo.name} "
                       f"sync(In past time-out value was 2500 "
                       f"but in current execution we set it 5000)", start_time)
    logger.info(f"entities repository sync completed successfully for capsule repo "
                f"name {sattools_repo.name}")
    if sat_tools_repo:
        sattools_repo.repo_id = CUSTOM_CONTENTS['capsule_tools']['repo']
    else:
        sattools_repo.repo_id = RHEL_CONTENTS['tools']['label']
    return sattools_repo


def sync_maintenance_repos_to_satellite_for_capsule(org):
    """
    Uses to enable the maintenance repo for capsule upgrade
    :param org: `nailgun.entities.Organization` entity of capsule
    :return: `nailgun.entities.repository` entity for capsule
    """
    to_version = settings.upgrade.to_version
    arch = 'x86_64'
    if settings.repos.satmaintenance_repo:
        try:
            maintenance_product = entities.Product(
                nailgun_conf,
                name=CUSTOM_CONTENTS['maintenance']['prod'],
                organization=org).create()
        except Exception as ex:
            logger.warn(ex)
            maintenance_product = entities.Product(
                nailgun_conf, organization=org).search(
                query={"search": f'name={CUSTOM_CONTENTS["maintenance"]["prod"]}'})[0]
        try:
            maintenance_repo = entities.Repository(
                nailgun_conf,
                name=CUSTOM_CONTENTS['maintenance']['repo'],
                product=maintenance_product, url=settings.repos.satmaintenance_repo,
                organization=org,
                content_type='yum'
            ).create()
        except Exception as ex:
            logger.warn(ex)
            maintenance_repo = entities.Repository(
                nailgun_conf, organization=org, product=maintenance_product
            ).search(query={"search": f'name={CUSTOM_CONTENTS["maintenance"]["repo"]}'})[0]
        logger.info(f"the custom maintenance product "
                    f"{CUSTOM_CONTENTS['maintenance']['prod']} "
                    f"and repository {CUSTOM_CONTENTS['maintenance']['repo']} is created from "
                    "satmaintenance downstream repo")
    else:
        maintenance_name = RHEL_CONTENTS['maintenance']['repofull']
        maintenance_prod = RHEL_CONTENTS['maintenance']['prod']
        with fabric_settings(warn_only=True):
            result = run(f'hammer repository-set enable --product "{maintenance_prod}"'
                         f' --basearch {arch} --releasever {to_version} --name '
                         f'"{maintenance_name}" --organization-id {org.id}')
            if result.return_code == 0:
                logger.info("maintenance repo enabled successfully")
            elif result.return_code == 70:
                logger.info("maintenance repo already enabled so the error code "
                            "70 is expected")
            else:
                logger.warn(result)
        maintenance_product = entities.Product(
            nailgun_conf, name=RHEL_CONTENTS['maintenance']['prod'], organization=org
        ).search(query={'per_page': 100})[0]
        maintenance_reposet = entities.RepositorySet(
            nailgun_conf,
            name=RHEL_CONTENTS['maintenance']['repofull'],
            product=maintenance_product
        ).search()[0]
        logger.info(f"maintenance product {RHEL_CONTENTS['maintenance']['prod']} and "
                    f"repository {RHEL_CONTENTS['maintenance']['repo']} searched complete "
                    f"successfully"
                    )
        try:
            maintenance_reposet.enable(data={'basearch': arch, 'organization_id': org.id})
            logger.info(f"maintenance repository enabled successfully for "
                        f"{maintenance_reposet.name}")
        except requests.exceptions.HTTPError as exp:
            logger.warn(exp)
        time.sleep(5)
        maintenance_repo = entities.Repository(
            nailgun_conf, name=RHEL_CONTENTS['maintenance']['repo']).search(
            query={'organization_id': org.id, 'per_page': 100}
        )[0]
        logger.info(f"entities repository search completed successfully for maintenance "
                    f"repo {RHEL_CONTENTS['maintenance']['repofull']}")
    logger.info(f"entities repository sync started successfully for "
                f"maintenance repo {maintenance_repo.name}")
    start_time = job_execution_time("Entities repository sync")
    try:
        call_entity_method_with_timeout(
            entities.Repository(nailgun_conf, id=maintenance_repo.id).sync, timeout=5000)
    except Exception as exp:
        logger.warn(f"RH Maintenance repository sync failed with exception: {exp}")
        repos_sync_failure_remiediation(org, maintenance_repo, timeout=5000)

    job_execution_time(f"entities repository {maintenance_repo.name} sync(In past time-out "
                       f"value was 2500 but in current execution we set it 5000)", start_time)
    logger.info(f"entities repository sync completed successfully for "
                f"maintenance repo {maintenance_repo.name}")
    if settings.repos.satmaintenance_repo:
        maintenance_repo.repo_id = CUSTOM_CONTENTS['maintenance']['repo']
    else:
        maintenance_repo.repo_id = RHEL_CONTENTS['maintenance']['label']
    return maintenance_repo


def add_subscription_for_capsule(ak, org):
    """
    Adds capsule, rhscl, rhel server, tools, maintenance subscription in capsule ak
    :param ak: `nailgun.entities.ActivationKey` of capsule
    :param org: `nailgun.entities.org` of capsule
    """
    cap_repo = sync_capsule_subscription_to_capsule_ak(org)
    scl_repo, server_repo = sync_rh_repos_to_satellite(org)
    maintenance_repo = sync_maintenance_repos_to_satellite_for_capsule(org)
    sattools_repo = sync_sattools_repos_to_satellite_for_capsule(org)
    # to update each repos fresh content view read is required,
    # otherwise it does not consider the pending repos from the point of failure.
    for repo_name in [cap_repo, maintenance_repo, scl_repo, server_repo, sattools_repo]:
        cv = ak.content_view.read()
        cv.repository += [repo_name]
        try:
            cv.update(['repository'])
            logger.info(f"repository {repo_name.name} enabled in content view {cv.name}")
        except requests.exceptions.HTTPError as exp:
            logger.warn(exp)
    ak = ak.read()
    ak.content_override(
        data={'content_override': {'content_label': scl_repo.repo_id, 'value': '1'}}
    )
    logger.info(f"activation key successfully override for content_label {scl_repo.name}")
    ak.content_override(
        data={'content_override': {'content_label': server_repo.repo_id, 'value': '1'}}
    )

    if settings.repos.capsule_repo is None:
        ak.content_override(
            data={
                'content_override': {'content_label': cap_repo.repo_id, 'value': '1'}
            }
        )
        logger.info(f"activation key content override successfully for "
                    f"content label:{cap_repo.name}")
    else:
        cap_sub = entities.Subscription(nailgun_conf).search(
            query={'search': 'name={0}'.format(CUSTOM_CONTENTS['capsule']['prod'])})[0]
        ak.add_subscriptions(data={
            'quantity': 1,
            'subscription_id': cap_sub.id,
        })
        logger.info(f"capsule subscription {cap_sub.name} added successfully to capsule ak")

    if settings.repos.satmaintenance_repo is None:
        ak.content_override(
            data={
                'content_override': {'content_label': maintenance_repo.repo_id, 'value': '1'}
            }
        )
        logger.info(f"cdn activation key successfully override for maintenance content_label"
                    f" {maintenance_repo.name}")
    else:
        maintenance_sub = entities.Subscription(nailgun_conf).search(
            query={'search': 'name={0}'.format(
                CUSTOM_CONTENTS['maintenance']['prod'])
            }
        )[0]
        ak.add_subscriptions(data={
            'quantity': 1,
            'subscription_id': maintenance_sub.id,
        })
        logger.info(f" maintenance subscription {maintenance_sub.id} added successfully to "
                    f"capsule ak")

    if settings.repos.sattools_repo[settings.upgrade.os] is None:
        ak.content_override(
            data={
                'content_override': {'content_label': sattools_repo.repo_id, 'value': '1'}
            })
        logger.info(f"cdn activation key successfully override) for "
                    f"capsule content_label {sattools_repo.name}")
    else:
        captools_sub = entities.Subscription(nailgun_conf).search(
            query={'search': f'name={CUSTOM_CONTENTS["capsule_tools"]["prod"]}'})[0]
        ak.add_subscriptions(data={
            'quantity': 1,
            'subscription_id': captools_sub.id,
        })
        logger.info(f"custom capsule Tools subscription {captools_sub.id} added successfully"
                    f" to capsule ak")


def sync_tools_repos_to_upgrade(client_os, hosts, ak_name):
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
    tools_repo_url = settings.repos.sattools_repo[client_os]
    if tools_repo_url is None:
        logger.warning('The Tools Repo URL for {} is not provided '
                       'to perform Client Upgrade !'.format(client_os))
        logger.highlight(f"The Tools Repo URL for {client_os} is not provided "
                         "to perform Client Upgrade. Aborting...")
        sys.exit(1)
    if ak_name is None:
        logger.highlight(f"The AK details are not provided for {0} Client upgrade."
                         " Aborting...")
        sys.exit(1)

    org = entities.Organization(nailgun_conf).search(
        query={'search': f'name="{DEFAULT_ORGANIZATION}"'})[0]
    ak = entities.ActivationKey(nailgun_conf, organization=org).search(
        query={'search': 'name={}'.format(ak_name)})[0]
    cv = ak.content_view.read()
    lenv = ak.environment.read()
    toolsproduct_name = CUSTOM_CONTENTS['tools']['prod'].format(client_os=client_os)
    toolsrepo_name = CUSTOM_CONTENTS['tools']['repo'].format(client_os=client_os)
    # adding sleeps in between to avoid race conditions
    try:
        tools_product = entities.Product(
            nailgun_conf, name=toolsproduct_name, organization=org).create()
    except Exception as exp:
        logger.warning(exp)
        tools_product = entities.Product(nailgun_conf, organization=org).search(
            query={'search': f'name={toolsproduct_name}'})[0]

    try:
        tools_repo = entities.Repository(
            nailgun_conf, name=toolsrepo_name, product=tools_product, url=tools_repo_url,
            organization=org, content_type='yum').create()
    except Exception as exp:
        logger.warning(exp)
        tools_repo = entities.Repository(
            nailgun_conf, organization=org).search(
            query={'search': f'name={toolsrepo_name}'})[0]

    logger.info(f"entities product {tools_product} and repository {toolsrepo_name} "
                f"created successfully")
    start_time = job_execution_time("tools repo sync operation")
    entities.Repository(nailgun_conf, id=tools_repo.id).sync()
    job_execution_time(f"tools repo {toolsrepo_name} sync operation", start_time)
    logger.info(f"entities repository sync operation completed successfully "
                f"for tool repos name {tools_repo.name}")
    cv.repository += [tools_repo]
    try:
        cv.update(['repository'])
    except requests.exceptions.HTTPError as exp:
        logger.warn(exp)
    logger.info("content view publish operation is started successfully")
    try:
        start_time = job_execution_time("CV_Publish")
        call_entity_method_with_timeout(cv.read().publish, timeout=5000)
        # expected time out value is 3500
        job_execution_time(f"content view {cv.name} publish operation(In past time-out value was "
                           f"3500 but in current execution we set it 5000) ", start_time)
    except Exception as exp:
        logger.critical(f"content view {cv.name} publish failed with exception {exp}")
        # Fix of 1770940, 1773601
        logger.info(f"resuming the cancelled content views {cv.name} published task")
        resume_failed_task()
    logger.info("content view published successfully")
    published_ver = entities.ContentViewVersion(
        nailgun_conf, id=max([cv_ver.id for cv_ver in cv.read().version])).read()
    logger.info(f"details of the published_ver is {published_ver}")
    start_time = job_execution_time("CV_Promotion")
    logger.info(f"published content view {cv.name} version promotion is started successfully")
    published_ver.promote(data={'environment_ids': [lenv.id], 'force': False})
    job_execution_time(f"content view {cv.name} promotion ", start_time)
    logger.info(f"published cv {cv.name} version has promoted successfully")
    tools_sub = entities.Subscription(nailgun_conf).search(
        query={'search': 'name={0}'.format(toolsproduct_name)})[0]
    ak.add_subscriptions(data={
        'quantity': 1,
        'subscription_id': tools_sub.id,
    })
    logger.info(f"subscription added successfully in capsule "
                f"activation key for name {tools_sub.name}")
    # Add this latest tools repo to hosts to upgrade
    sub = entities.Subscription(nailgun_conf).search(
        query={'search': 'name={0}'.format(toolsproduct_name)})[0]
    for host in hosts:
        host = entities.Host(nailgun_conf).search(query={'search': 'name={}'.format(host)})[0]
        logger.info(f"Adding the Subscription {sub.name} on host {host.name}")
        entities.HostSubscription(nailgun_conf, host=host).add_subscriptions(
            data={'subscriptions': [{'id': sub.id, 'quantity': 1}]})


def post_upgrade_test_tasks(sat_host, cap_host=None):
    """Run set of tasks for post upgrade tests
    :param string sat_host: Hostname to run the tasks on
    :param list cap_host: Capsule hosts to run sync on
    """
    # Execute tasks as post upgrade tests are dependent
    certificate_url = settings.fake_manifest.cert_url
    if certificate_url is not None:
        execute(
            setup_fake_manifest_certificate,
            certificate_url,
            host=sat_host
        )
    sat_version = settings.upgrade.to_version
    execute(setup_alternate_capsule_ports, host=sat_host)
    logger.info("update the default organization name")
    org = entities.Organization(nailgun_conf).search(
        query={'search': f'label="{DEFAULT_ORGANIZATION_LABEL}"'}
    )[0]
    org.name = f"{DEFAULT_ORGANIZATION}"
    org.update(['name'])
    # Update the Default Location name
    logger.info("update the Default Location name")
    loc = entities.Location(nailgun_conf).search(
        query={'search': f'name="{DEFAULT_LOCATION}"'})[0]
    loc.name = f"{DEFAULT_LOCATION}"
    loc.update(['name'])
    # Increase log level to DEBUG, to get better logs in foreman_debug
    execute(lambda: run('sed -i -e \'/:level: / s/: .*/: '
                        'debug/\' /etc/foreman/settings.yaml'), host=sat_host)
    execute(foreman_service_restart, host=sat_host)
    # Execute task for template changes required for discovery feature
    execute(
        setup_foreman_discovery,
        sat_version=sat_version,
        host=sat_host
    )
    # Execute task for creating latest discovery iso required for unattended test
    env.disable_known_hosts = True
    if host_pings(settings.libvirt.libvirt_hostname):
        execute(
            get_discovery_image,
            host=settings.libvirt.libvirt_hostname
        )
    else:
        logger.warn(f"libvirt host {settings.libvirt.libvirt_hostname} "
                    f"is not working, please check and fix it in the code")
    # Commenting out until GH issue:#135
    # Removing the original manifest from Default Organization (Org-id 1),
    # to allow test-cases to utilize the same manifest.
    # logger.info("Removing the Original Manifest from Default Organization")
    # execute(hammer, 'subscription delete-manifest --organization-id 1',
    #         host=sat_host)
    os.environ['HTTP_SERVER_HOSTNAME'] = settings.repos.rhel_os_repo_host
    # Run Avahi Task on upgrade boxes for REX tests to run
    execute(foreman_packages_installation_check, state="unlock", non_upgrade_task=True,
            host=sat_host)
    execute(lambda: run('yum remove -y epel*'), host=sat_host)
    execute(setup_avahi_discovery, host=sat_host)
    execute(foreman_packages_installation_check, state="lock", non_upgrade_task=True,
            host=sat_host)
    # setup RHEV certificate so it can be added as a CR
    execute(setup_rhv_ca, host=sat_host)


def capsule_sync(cap_host):
    """Run Capsule Sync as a part of job
    :param list cap_host: List of capsules to perform sync
    """
    capsule = entities.SmartProxy(nailgun_conf).search(
        query={'search': 'name={}'.format(cap_host)})[0]
    capsule.refresh()
    logger.info('Running Capsule sync for capsule host {0}'.
                format(cap_host))
    capsule = entities.Capsule(nailgun_conf).search(
        query={'search': 'name={}'.format(cap_host)})[0]
    start_time = job_execution_time("Capsule content sync operation")
    try:
        capsule.content_sync()
    except Exception as ex:
        logger.critical(ex)
    job_execution_time("Capsule content sync operation", start_time)


def foreman_service_restart():
    """Restarts the foreman-maintain services"""
    services = run('foreman-maintain service restart')
    if services.return_code > 0:
        logger.error('Unable to re-start the Satellite Services')
        logger.highlight("Failed to restart the satellite services. Aborting...")
        sys.exit(1)


def check_ntpd():
    """Check if ntpd is running else start the service"""
    ntpd_check = run("service ntpd status", warn_only=True)
    if ntpd_check.return_code > 0:
        run("service ntpd start")
        run("chkconfig ntpd on")


def setup_satellite_repo():
    """Task which install foreman-maintain tool.
    Environment Variables necessary to proceed Setup:
    -----------------------------------------------------
    DISTRIBUTION
        The satellite upgrade using internal or cdn distribution.
        e.g 'cdn','downstream'
    MAINTAIN_REPO
        URL of repo if distribution is downstream
    BASE_URL
        URL for the compose repository if distribution is downstream
    TOOLS_RHEL7
        URL for the satellite tools repo if distribution is downstream
    """
    env.disable_known_hosts = True
    # setting up foreman-maintain repo
    setup_foreman_maintain_repo()
    if settings.upgrade.distribution != 'cdn':
        for repo in CUSTOM_SAT_REPO:
            if repo != "foreman-maintain":
                repository_setup(
                    CUSTOM_SAT_REPO[repo]["repository"],
                    CUSTOM_SAT_REPO[repo]["repository_name"],
                    CUSTOM_SAT_REPO[repo]["base_url"],
                    CUSTOM_SAT_REPO[repo]["enable"],
                    CUSTOM_SAT_REPO[repo]["gpg"]
                )


def maintenance_repo_update():
    """
    Use to update the maintenance repo url for downstream y-stream version
    """
    os_version = settings.upgrade.os.upper()
    if settings.upgrade.to_version == '7.0' or settings.upgrade.downstream_fm_upgrade:
        maintenance_repo = settings.repos.satmaintenance_repo
        settings.repos.satmaintenance_repo = re.sub(
            f'Satellite_Maintenance_Next_{os_version}|Satellite_Maintenance_{os_version}',
            f'Satellite_{settings.repos.satellite_version_undr}_with_{os_version}_Server',
            settings.repos.satmaintenance_repo, 1)
        logger.info(f"updated maintenance repo for downstream y stream upgrade "
                    f"{settings.repos.satmaintenance_repo}")
        if requests.get(f"{settings.repos.satmaintenance_repo }").status_code != 200:
            settings.repos.satmaintenance_repo = maintenance_repo
            logger.warn(f"updated downstream y-stream repo did not work "
                        f"so we rollbacked to the stable maintenance repo "
                        f"{settings.repos.satmaintenance_repo}")
        CUSTOM_SAT_REPO["foreman-maintain"]["base_url"] = settings.repos.satmaintenance_repo


def setup_foreman_maintain_repo():
    """Task which setup repo for foreman-maintain.
    Environment Variables necessary to proceed Setup:
    -----------------------------------------------------
    DISTRIBUTION
        The satellite upgrade using internal or cdn distribution.
        e.g 'cdn','downstream'
    MAINTAIN_REPO
        URL of repo if distribution is downstream
    """
    # setting up foreman-maintain repo
    if settings.upgrade.distribution == 'cdn':
        enable_repos('rhel-7-server-satellite-maintenance-6-rpms')
    else:
        repository_setup(
            CUSTOM_SAT_REPO["foreman-maintain"]["repository"],
            CUSTOM_SAT_REPO["foreman-maintain"]["repository_name"],
            CUSTOM_SAT_REPO["foreman-maintain"]["base_url"],
            CUSTOM_SAT_REPO["foreman-maintain"]["enable"],
            CUSTOM_SAT_REPO["foreman-maintain"]["gpg"]
        )


def hammer_config():
    """
    Use to update the hammer config file on the satellite
    """
    run('mkdir -p /root/.hammer/cli.modules.d')
    hammer_file = StringIO()
    hammer_file.write('--- \n')
    hammer_file.write(' :foreman: \n')
    hammer_file.write('  :username: admin\n')
    hammer_file.write('  :password: changeme \n')
    put(local_path=hammer_file,
        remote_path='/root/.hammer/cli.modules.d/foreman.yml')
    hammer_file.close()


def upgrade_using_foreman_maintain(sat_host=True):
    """Task which upgrades the product using foreman-maintain tool.
    Environment Variables necessary to proceed Upgrade:
    -----------------------------------------------------
    FROM_VERSION
        Current satellite version which will be upgraded to latest version
    TO_VERSION
        To which Satellite version to upgrade.
        e.g '6.2','6.3'
    :param bool sat_host: if sat_host is True then upgrade will be
     satellite otherwise capsule.
    """
    env.disable_known_hosts = True

    def pre_satellite_upgrade_check():
        with warn_only():
            if settings.upgrade.from_version == settings.upgrade.to_version:
                # z stream upgrade
                run(f'foreman-maintain upgrade check --target-version '
                    f'{settings.upgrade.to_version}.z -y')
            else:
                run(f'foreman-maintain upgrade check --target-version'
                    f' {settings.upgrade.to_version} -y')

    def pre_capsule_upgrade_check():
        with warn_only():
            if settings.upgrade.from_version == settings.upgrade.to_version:
                run(f'foreman-maintain upgrade check --whitelist="repositories-validate, '
                    f'repositories-setup" --target-version {settings.upgrade.to_version}.z -y')
            else:
                run(f'foreman-maintain upgrade check --whitelist="repositories-validate, '
                    f'repositories-setup" --target-version {settings.upgrade.to_version}.z -y')

    def satellite_upgrade():
        """ This inner function is used to perform Y & Z satellite stream upgrade"""
        # whitelist disk-performance check
        if settings.upgrade.from_version == settings.upgrade.to_version:
            # z stream satellite upgrade
            run(f'foreman-maintain upgrade run '
                f'--whitelist="disk-performance" '
                f'--target-version {settings.upgrade.to_version}.z -y')
        else:
            if settings.upgrade.from_version != settings.upgrade.to_version:
                run(f'foreman-maintain upgrade run --whitelist="disk-performance'
                    f'{settings.upgrade.whitelist_param}" --target-version '
                    f'{settings.upgrade.to_version} -y')
            else:
                run(f'foreman-maintain upgrade run --whitelist="disk-performance" '
                    f'--target-version {settings.upgrade.to_version}.z -y')

    def capsule_upgrade():
        """ This inner function is used to perform Y & Z stream Capsule upgrade"""
        if settings.upgrade.from_version == settings.upgrade.to_version:
            # z capsule stream upgrade, If we do not whitelist the repos setup then cdn
            # repos of target version gets enabled.
            if settings.upgrade.distribution == 'cdn':
                run(f'foreman-maintain upgrade run --target-version '
                    f'{settings.upgrade.to_version}.z -y')
            else:
                run(f'foreman-maintain upgrade run -whitelist="repositories-validate,'
                    f'repositories-setup" --target-version '
                    f'{settings.upgrade.to_version}.z -y')
        else:
            if settings.upgrade.distribution == 'cdn':
                run(f'foreman-maintain upgrade run --target-version'
                    f' {settings.upgrade.to_version} -y')
            else:
                run(f'foreman-maintain upgrade run --whitelist="repositories-validate, '
                    f'repositories-setup" --target-version'
                    f' {settings.upgrade.to_version} -y')

    if sat_host:
        pre_satellite_upgrade_check()
        preup_time = datetime.now().replace(microsecond=0)
        satellite_upgrade()
    else:
        pre_capsule_upgrade_check()
        preup_time = datetime.now().replace(microsecond=0)
        capsule_upgrade()
    postup_time = datetime.now().replace(microsecond=0)

    if sat_host:
        logger.highlight(f'Time taken for satellite upgrade - {str(postup_time - preup_time)}')
    else:
        logger.highlight(f'Time taken for capsule upgrade - {str(postup_time - preup_time)}')


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
    repository_setup("rhel", "rhel",
                     base_url, 1, 0)


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


def wait_untill_capsule_sync(capsule):
    """The polling function that waits for capsule sync task to finish
    :param capsule: A capsule hostname
    """
    cap = entities.Capsule(nailgun_conf).search(
        query={'search': f'name={capsule}'})[0]
    logger.info(f"Waiting for capsule {capsule} sync to finish ...")
    active_tasks = cap.content_get_sync()['active_sync_tasks']
    logger.info(f"Active tasks {active_tasks}")
    if len(active_tasks) >= 1:
        logger.info(
            'Wait for background capsule sync to finish on '
            'capsule: {}'.format(cap.name))
        start_time = job_execution_time("capsule_sync")
        for task in active_tasks:
            try:
                entities.ForemanTask(nailgun_conf, id=task['id']).poll(timeout=9000)
            except Exception as ex:
                logger.warn(f"Task id {task['id']} failed with {ex}")
        job_execution_time("Background capsule sync operation(In past time-out value was "
                           "2700 but in current execution we have set it 9000)",
                           start_time)


def pre_upgrade_system_checks(capsules):
    """The preupgrade system checks necessary for smooth upgrade experience

    :param capsules: The list of capsules
    """
    # Check and wait if the capsule sync task is running before upgrade
    if capsules:
        for capsule in capsules:
            wait_untill_capsule_sync(capsule)


def generate_custom_certs():
    """ Task to generate custom certs for satellite
    Environment Variable:
    SERVER_HOSTNAME
        The satellite server hostname
    """
    certs_script = StringIO()
    certs_script.write(
        "#! /bin/bash\n"
        "name={hostname}\n"
        "mkdir ownca\n"
        "pushd ownca\n"
        "wget https://raw.githubusercontent.com/ntkathole/ownca/master/openssl.cnf\n"
        "wget https://raw.githubusercontent.com/ntkathole/ownca/master/generate-ca.sh\n"
        "wget https://raw.githubusercontent.com/ntkathole/ownca/master/generate-crt.sh\n"
        "echo 100001 >> serial\n"
        "chmod 744 *.sh\n"
        'yes "" | ./generate-ca.sh\n'
        'yes | ./generate-crt.sh $name\n'
        'cp cacert.crt $name/\n'
        .format(hostname=settings.upgrade.satellite_hostname)
    )
    put(local_path=certs_script,
        remote_path='/root/certs_script.sh')
    certs_script.close()
    run("sh /root/certs_script.sh")


def add_custom_product_subscription_to_hosts(product, hosts):
    """Adds custom product subscription to given list of hosts

    :param str product: The custom product name
    :param list hosts: List of content host names
    """
    for host in hosts:
        sub = entities.Subscription(nailgun_conf).search(
            query={'search': f'name={product}'})[0]
        if float(settings.upgrade.from_version) <= 6.1:
            execute(
                attach_subscription_to_host_from_content_host, sub.cp_id, host=host)
        else:
            host = entities.Host(nailgun_conf).search(query={'search': f'name={host}'})[0]
            entities.HostSubscription(nailgun_conf, host=host).add_subscriptions(
                data={'subscriptions': [{'id': sub.id, 'quantity': 1}]})


def repository_setup(repository, repository_name, base_url, enable, gpgcheck):
    """
    This is generic fucntion which is used to setup the repository
    :param str repository: uniq repository ID
    :param str repository_name: repository name in string
    :param str base_url: repository url
    :param int enable: repoitory enable(1) or disable(0)
    :param int gpgcheck: verify GPG authenticity pass 1 otherwise pass 0
    :return:
    """
    satellite_repo = StringIO()
    satellite_repo.write(f'[{repository}]\n')
    satellite_repo.write(f'name=s{repository_name}\n')
    satellite_repo.write(f'baseurl={base_url}\n')
    satellite_repo.write(f'enabled={enable}\n')
    satellite_repo.write(f'gpgcheck={gpgcheck}\n')
    put(local_path=satellite_repo,
        remote_path=f'/etc/yum.repos.d/{repository}.repo')
    satellite_repo.close()


def enable_disable_repo(disable_repos_name=None, enable_repos_name=None):
    """
    The purpose of this function is to enable and disable the
    repository as per requirements.
    :param list disable_repos_name: This will take the
    list of repository which you are going to disable
    :param list enable_repos_name: This will take the list of
    repository which you are going to enable
    """
    if disable_repos_name:
        [disable_repos(f'{repo}', silent=True) for repo in disable_repos_name]
    if enable_repos_name:
        [enable_repos(f'{repo}') for repo in enable_repos_name]


def nonfm_upgrade(satellite_upgrade=True,
                  cap_host=None, sat_host=None):
    """
    The purpose of this module to perform the upgrade task without foreman-maintain.
    In this function we setup the repository, stop the foreman-maintain services,
    cleanup, and execute satellite upgrade task"
    :param bool satellite_upgrade: If satellite_upgrade is True then upgrade
    type satellite otherwise capsule
    :param bool zstream: Capsule zStream upgrade
    :param str cap_host: hostname of capsule it used to generate certificate for
    capsules major version upgrade.
    :param str sat_host: hostname of satellite used to generate certificate for
    capsules major version upgrade.
    :
    """
    # Check what repos are set
    upgrade_type = "satellite" if satellite_upgrade else "capsule"
    run('yum repolist')
    # Stop foreman-maintain services
    run('foreman-maintain service stop')
    run('yum clean all', warn_only=True)
    # Updating the packages again after setting sat repo
    logger.info(f'Updating system and {upgrade_type} packages... ')
    preyum_time = datetime.now().replace(microsecond=0)
    update_packages(quiet=False)
    postyum_time = datetime.now().replace(microsecond=0)
    logger.highlight(f'Time taken for system and {upgrade_type} packages update'
                     f' - {str(postyum_time - preyum_time)}')
    # non zStream capsule upgrade
    if sat_host and cap_host:
        execute(
            generate_capsule_certs,
            cap_host,
            True,
            host=sat_host
        )
        execute(lambda: run(f"scp -o 'StrictHostKeyChecking no' {cap_host}-certs.tar "
                            f"root@{cap_host}:/home/"), host=sat_host)
        setup_capsule_firewall()
        preup_time = datetime.now().replace(microsecond=0)
        upgrade_task(upgrade_type, cap_host)
    else:
        preup_time = datetime.now().replace(microsecond=0)
        upgrade_task(upgrade_type)
    postup_time = datetime.now().replace(microsecond=0)
    logger.highlight('Time taken for Satellite Upgrade - {}'.format(
        str(postup_time - preup_time)))


def upgrade_task(upgrade_type, cap_host=None):
    """
    :param str upgrade_type: upgrade type would be an string either it is
    satellite or capsule
    :param str cap_host: hostname for capsule's major version upgrade
    """
    if cap_host:
        run(f'satellite-installer --scenario {upgrade_type} '
            f'--certs-tar-file /home/{cap_host}-certs.tar '
            f'--certs-update-all')
    else:
        run(f'satellite-installer --scenario {upgrade_type}')


def upgrade_validation(upgrade_type="satellite", satellite_services_action="status -b"):
    """
    In this function we check the system states after upgrade.
    :param str upgrade_type: satellite or capsule.
    :param str satellite_services_action: start, stop and restart based on the resquest
    """
    with fabric_settings(warn_only=True):
        if upgrade_type == "satellite":
            result = run('hammer ping', warn_only=True)
            if result.return_code != 0:
                logger.warn("hammer ping: some of satellite services in the failed state")
        for action in set(["status -b", satellite_services_action]):
            result = run(f'foreman-maintain service {action}', warn_only=True)
            if result.return_code != 0:
                logger.warn(f"foreman maintain {action} command failed")


def update_scap_content():
    """ The purpose of this function is to perform deletion of old scap-contents
        and then uploading new scap-contents. It also deletes scap-policies and creates
         new scap-policies with new scap-contents. """

    def create_policy(scap_content, policy_name):
        """This function is used for creating scap policy

        :param scap_content: Name of scap-content to be used while creating policy.
        :param str policy_name: Name of policy to be created.
        """
        org = entities.Organization(nailgun_conf).search(
            query={'search': f'name="{DEFAULT_ORGANIZATION}"'})[0]
        loc = entities.Location(nailgun_conf).search(
            query={'search': f'name="{DEFAULT_LOCATION}"'}
        )[0]
        scap_content_profile_id = entities.ScapContents(
            nailgun_conf,
            id=scap_content.id).read().scap_content_profiles[0]['id']
        entities.CompliancePolicies(
            nailgun_conf,
            name=policy_name,
            scap_content_id=scap_content.id,
            scap_content_profile_id=scap_content_profile_id,
            deploy_by='puppet',
            organization=[org],
            location=[loc],
            period='weekly',
            weekday='monday',
        ).create()

    def scap(content_type, content_name):
        """This function is used for deleting old scap contents and policy
        and it use create_policy for creating new policies.

        :param content_type: Search result of scap-content or compliance-policy entity.
        :param str content_name: Name assigned to searched entity.
        """
        for entity in range(len(content_type)):
            if content_name == "updated_scap_content":
                if updated_scap_content[entity].title == scap_content_name[0]:
                    create_policy(updated_scap_content[entity], compliance_policies[0])
                elif updated_scap_content[entity].title == scap_content_name[1]:
                    create_policy(updated_scap_content[entity], compliance_policies[1])
            elif content_name == "policies_search":
                entities.CompliancePolicies(nailgun_conf, id=policies_search[entity].id).delete()
            elif content_name == "scap_content_search":
                entities.ScapContents(nailgun_conf, id=scap_content_search[entity].id).delete()

    compliance_policies = ['RHEL 7 policy', 'RHEL 6 policy']
    scap_content_name = ['Red Hat rhel7 default content', 'Red Hat rhel6 default content']
    scap_content_search = entities.ScapContents(nailgun_conf).search()
    policies_search = entities.CompliancePolicies(nailgun_conf).search()
    scap(policies_search, "policies_search")
    scap(scap_content_search, "scap_content_search")
    run('foreman-rake foreman_openscap:bulk_upload:default')
    updated_scap_content = entities.ScapContents(nailgun_conf).search()
    scap(updated_scap_content, "updated_scap_content")


def mongo_db_engine_upgrade(upgrade_type):
    """
    The purpose of this method to perform the upgrade of mongo DB database engine
    from MMAPv1 to WiredTiger.
    :param str upgrade_type:  If user select the upgrade_type 'Satellite' then mongodb
    upgrade would be performed on Satellite otherwise it would be happened on Capsule
    """
    logger.highlight('\n========== MongoDB DataBase Engine Upgrade =================\n')
    logger.info("Upgrading the MongoDb Database on {}".format(upgrade_type))
    preup_time = datetime.now().replace(microsecond=0)
    run("satellite-installer --upgrade-mongo-storage-engine")
    postup_time = datetime.now().replace(microsecond=0)
    logger.info("MongoDB DataBase Engine Upgraded Successfully")
    logger.highlight('Time taken by MongoDB DataBase Engine Upgrade - {}'.format(
        str(postup_time - preup_time)))


def foreman_packages_installation_check(state="unlock", non_upgrade_task=False):
    """
    This function is used to change the state of the foreman-package installation method,
    And it will be applicable only if the FOREMAN_MAINTAIN_SATELLITE_UPGRADE is False.

    :param str state: To perform the installation using foreman-maintain the state will be
    "lock" otherwise "unlock"
    :param bool non_upgrade_task: to unlock the packages for non_upgrade_task

    """
    if not settings.upgrade.foreman_maintain_satellite_upgrade or non_upgrade_task:
        logger.info("{} the foreman-maintain packages".format(state))
        run("foreman-maintain packages {} -y".format(state))
    else:
        logger.info("Failed to apply the {} state on foreman-maintain packages , "
                    "because FOREMAN_MAINTAIN_SATELLITE_UPGRADE is true")


def job_execution_time(task_name, start_time=None):
    """
    This function is used to collect the information of start and end time and
    also calculate the total execution time
    :param str task_name: Provide the action need to perform
    :param datetime start_time: If start_time is None then we capture the start time
    details.
    :return: start_time
    """
    if start_time:
        end_time = datetime.now().replace(microsecond=0)
        total_job_execution_time = str(end_time - start_time)
        logger.highlight('Time taken by task {} - {}'.format(task_name,
                                                             total_job_execution_time))
    else:
        start_time = datetime.now().replace(microsecond=0)
        return start_time


def resume_failed_task():
    """
    This function is used to resume the canceled paused tasks.
    """
    output = run("hammer task list|awk '/Task canceled/ && /paused/ {print $1}'")
    run(f"hammer task resume --task-ids {','.join(output.split())}")
    for task_id in output.split():
        run(f'hammer task progress --id {task_id}')
    output = run("hammer task list|awk '/Task canceled/ && /paused/ {print $1}'")
    if output:
        logger.warn(f"These task ids {','.join(output.split())} are still in paused state, "
                    f"manual investigation is required")


def repos_sync_failure_remiediation(org, repo_object, timeout=3000):
    """
    Use to rerun the repository sync after manifest refresh
    :param org: nailgun org object
    :param repo_object: nailgun repos object
    :param timeout: sync timeout
    """
    try:
        logger.info(f'Run the {repo_object.name} repository sync again after manifest refresh')
        entities.Subscription(nailgun_conf).refresh_manifest(data={'organization_id': org.id},
                                                             timeout=5000)
    except Exception as exp:
        logger.warn(f'manifst refresh failed due to {exp}')
    # To handle HTTPError: 404 Client Error: Not Found for url:
    # https://xyz.com/katello/api/v2/repositories/2456/sync
    for attempt in range(1, 5):
        try:
            time.sleep(50)
            repo_object = entities.Repository(
                nailgun_conf, name=f'{repo_object.name}').search(
                query={'organization_id': org.id, 'per_page': 100}
            )[0]
            call_entity_method_with_timeout(
                entities.Repository(nailgun_conf, id=repo_object.id).sync, timeout=timeout)
            break
        except Exception as exp:
            # some time pulp_celerybeat services gets down, needs investigation for that,
            # for now as workaround we are starting the services
            upgrade_validation(upgrade_type="satellite",
                               satellite_services_action="start")
            logger.warn(f'Retry:{attempt} Repos sync remediation failed due to {exp}')


def foreman_maintain_package_update():
    """
    Install the latest fm rubygem-foreman_maintain to get the latest y-stream upgrade path.
    """
    # Remove the old repos detail
    run("yum clean all")
    # repolist
    run('yum repolist')
    # install foreman-maintain
    run('yum install rubygem-foreman_maintain -y')


def yum_repos_cleanup():
    """
    Use to remove non-required repos from the /etc/yum.repos.d
    """
    with fabric_settings(warn_only=True):
        result = run("rm -f /etc/yum.repos.d/*")
        if result.return_code != 0:
            logger.warn(result)


def workaround_1829115():
    """
    Replacing the /usr/share/katello/hostname-change.rb with their original file before
    starting the upgrade.
    """
    file_name = "/usr/share/katello/hostname-change.rb"
    file_backup = '/usr/share/katello/hostname-change.rb.backup'
    output = run(f"if [ -f {file_backup} ]; then mv {file_backup} {file_name}; fi")
    if output.return_code > 0:
        logger.warn("Failed to update the file")


def add_satellite_subscriptions_in_capsule_ak(ak, org, custom_repo=None):
    """
    Use to add the satellite subscriptions in capsule activation key, it helps to enable the
    capsule repository.
    :param ak:  capsule activation key object
    :param org: organization object
    :param custom_repo: custom repos object
    """
    with fabric_settings(warn_only=True):
        if not custom_repo:
            rhel_subscription = f'awk \'/{CAPSULE_SUBSCRIPTIONS["rhel_subscription"]}/ ' +\
                                '{print $1}\''
            sat_subscription = f'awk \'/{CAPSULE_SUBSCRIPTIONS["satellite_infra"]}/ ' + \
                               '{print $1}\''
            subscription_map = [rhel_subscription, sat_subscription]
        else:
            subscription_map = [f'awk \'/{custom_repo.product.read_json()["name"]}/ ' +
                                '{print $1}\'']

        for subscription in subscription_map:
            output = run(f'hammer subscription list --organization-id="{org.id}" | {subscription}')
            if output.return_code > 0:
                logger.warn(output)
            else:
                for sub_id in output.splitlines():
                    ak_output = run(f'hammer activation-key add-subscription --subscription-id='
                                    f'"{sub_id}" --id="{ak.id}"')
                    if ak_output.return_code > 0:
                        logger.warn(output)


def satellite_restore_setup():
    """
    Use to setup the satellite restore for upstream satellite clone
    """
    if settings.clone.clone_rpm:
        clone_dir = settings.clone.downstream_clone_dir
    else:
        clone_dir = settings.clone.upstream_clone_dir
    backup_dir = settings.clone.backup_dir.replace("/", "\/")  # noqa
    customer_name = settings.clone.customer_name + \
                     str(settings.upgrade.from_version).replace(".", "") # noqa
    with fabric_settings(warn_only=True):
        run(f"curl -o /etc/yum.repos.d/rhel.repo {settings.repos.rhel7_repo}; "
            f"yum install -y nfs-utils; mkdir -p {settings.clone.backup_dir}; "
            f"mount -o v3 {settings.clone.db_server}:"
            f"/root/customer-dbs {settings.clone.backup_dir}")
        enable_disable_repo(enable_repos_name=[
            f"rhel-{settings.upgrade.os[-1]}-server-ansible-"
            f"{settings.upgrade.ansible_repo_version}-rpms"])
        run("yum install -y ansible")

    if settings.clone.clone_rpm:
        run('yum repolist')
        run('yum install satellite-clone -y')
    else:
        with fabric_settings(warn_only=True):
            run("ssh-keygen -q -t rsa -N '' -f ~/.ssh/id_rsa <<<y >/dev/null 2>&1;"
                "cat ~/.ssh/id_rsa.pub >> ~/.ssh/authorized_keys;")

        with fabric_settings(warn_only=True):
            output = run(f"git clone {settings.clone.satellite_clone_upstream_repos}")
            if output.return_code != 0:
                logger.warn("upstream clone operation failed")
            run(f'cp -a {clone_dir}/satellite-clone-vars.sample.yml '
                f'{clone_dir}/satellite-clone-vars.yml;'
                f'sed -i -e 2s/.*/"{settings.upgrade.satellite_hostname}"/ '
                f'{clone_dir}/inventory;')
    with fabric_settings(warn_only=True):
        output = run(
            f'echo "satellite_version: "{settings.upgrade.from_version}"" >> '
            f'{clone_dir}/satellite-clone-vars.yml;'
            f'echo "activationkey: "test_ak"" >> {clone_dir}/satellite-clone-vars.yml;'
            f'echo "org: "{DEFAULT_ORGANIZATION}"" >> '
            f'{clone_dir}/satellite-clone-vars.yml;'
            f'sed -i -e "s/^#backup_dir.*/backup_dir: '
            f'{backup_dir}\/{customer_name}/" '  # noqa
            f'{clone_dir}/satellite-clone-vars.yml;'
            f'echo "include_pulp_data: "{settings.clone.include_pulp_data}"" >>'
            f' {clone_dir}/satellite-clone-vars.yml;'
            f'echo "restorecon: "{settings.clone.restorecon}"" >>'
            f' {clone_dir}/satellite-clone-vars.yml;'
            f'echo "register_to_portal: true" >> {clone_dir}/satellite-clone-vars.yml;'
            f'sed -i -e "/#org.*/arhn_pool: "{settings.subscription.rhn_poolid}""'
            f' {clone_dir}/satellite-clone-vars.yml;'
            f'sed -i -e "/#org.*/arhn_password: "{settings.subscription.rhn_password}"" '
            f'{clone_dir}/satellite-clone-vars.yml;'
            f'sed -i -e "/#org.*/arhn_user: "{settings.subscription.rhn_username}"" '
            f'{clone_dir}/satellite-clone-vars.yml;'
            f'sed -i -e "/#org.*/arhelversion: "{settings.upgrade.os[-1]}"" '
            f'{clone_dir}/satellite-clone-vars.yml;'
            f'sed -i -e "/subscription-manager register.*/d" '
            f'{clone_dir}/roles/satellite-clone/tasks/main.yml;'
            'sed -i -e "/Register\\/Subscribe the system to Red Hat Portal.*/a\\ \\ '
            'command: subscription-manager register --force --user={{ rhn_user }} '
            '--password={{ rhn_password }} --release={{ rhelversion }}Server" '
            f'{clone_dir}/roles/satellite-clone/tasks/main.yml;'
            'sed -i -e "/subscription-manager register.*/a- name: subscribe machine"'
            f' {clone_dir}/roles/satellite-clone/tasks/main.yml;'
            'sed -i -e "/subscribe machine.*/a\\ \\ command: subscription-manager '
            'subscribe --pool={{ rhn_pool }}" '
            f'{clone_dir}/roles/satellite-clone/'
            f'tasks/main.yml')
        if output.return_code != 0:
            logger.critical(f"satellite clone setup failed: {output}")


def satellite_restore():
    """
    Use to run the satellite restore
    """
    prerestore_time = datetime.now().replace(microsecond=0)
    with fabric_settings(warn_only=True):
        unsubscribe()
        if settings.clone.clone_rpm:
            restore_output = run("satellite-clone -y")
        else:
            with shell_env(ANSIBLE_HOST_KEY_CHECKING="false"):
                ping_output = run(f"cd {settings.clone.upstream_clone_dir}; "
                                  f"ansible all -i inventory -m ping -u root")
                if ping_output.return_code != 0:
                    logger.highlight(
                        "The provided setup is in-accessible. Aborting...")
                    sys.exit(1)
                restore_output = run(f"cd {settings.clone.upstream_clone_dir}; "
                                     f"ansible-playbook -i inventory "
                                     f"satellite-clone-playbook.yml")
        postrestore_time = datetime.now().replace(microsecond=0)
        logger.highlight(f'Time taken by satellite restore - '
                         f'{str(postrestore_time - prerestore_time)}')
        run(f"umount {settings.clone.backup_dir}")
        if restore_output.return_code != 0:
            logger.highlight("Satellite restore completed with some error. "
                             "Aborting...")
            sys.exit(1)


def satellite_backup():
    """
    Use to perform the satellite backup after upgrade
    """
    satellite_backup_type = settings.upgrade.satellite_backup_type[randrange(2)]
    logger.info(f"running satellite backup in {satellite_backup_type} mode")
    preyum_time = datetime.now().replace(microsecond=0)
    with fabric_settings(warn_only=True):
        output = run(f"satellite-maintain backup {satellite_backup_type} "
                     f"--skip-pulp-content -y {settings.clone.backup_dir}"
                     f"_{satellite_backup_type}")
        postyum_time = datetime.now().replace(microsecond=0)
        logger.highlight(f'Time taken by {satellite_backup_type} satellite backup - '
                         f'{str(postyum_time - preyum_time)}')
        if output.return_code != 0:
            logger.warn(f"satellite backup failed in {satellite_backup_type} mode")


def unsubscribe():
    """
    Use to unsubscribe the setup from cdn.
    """
    with fabric_settings(warn_only=True):
        run("subscription-manager unregister")
        run('subscription-manager clean')


def subscribe():
    """
    Use to subscribe the setup from cdn
    :return:
    """
    with fabric_settings(warn_only=True):
        with hide('running'):
            run(f'subscription-manager register --force '
                f'--user={settings.subscription.rhn_username} '
                f'--password={settings.subscription.rhn_password} --release '
                f'{settings.upgrade.os[-1]}Server')
        attach_cmd = f'subscription-manager attach --pool {settings.subscription.rhn_poolid}'
        has_pool_msg = 'This unit has already had the subscription matching pool ID'
        for _ in range(10):
            result = run(attach_cmd)
            if result.succeeded or has_pool_msg in result:
                return
            time.sleep(5)
        logger.highlight("Unable to attach the system to pool. Aborting...")
        sys.exit(1)


def create_capsule_ak():
    """
    Use to creates a activation key for capsule upgrade on a blank Satellite
    """
    def activation_key_availability_check(org):
        """
        Use to identifying the activation keys availabilty in the setup
        """
        ak = entities.ActivationKey(nailgun_conf, organization=org).search(
            query={"search": f"name={settings.upgrade.capsule_ak[settings.upgrade.os]}"}
        )
        return ak

    def manifest_upload(org):
        """
        Use to download and upload the manifest file.
        """
        manifest_name = settings.fake_manifest.url.default.split('/')[-1]
        try:
            with open(f'{manifest_name}', 'rb') as manifest:
                entities.Subscription(nailgun_conf).upload(data={'organization_id': org.id},
                                                           files={'content': manifest})
        except Exception as ex:
            logger.warn(ex)
        entities.Subscription(nailgun_conf).refresh_manifest(data={'organization_id': org.id},
                                                             timeout=5000)

    def repos_sync(org):
        """
        Use to setup the repository sync
        """
        logger.info("Syncing Ansible Engine repo..")
        ans_repo = sync_ansible_repo_to_satellite(org)
        logger.info("Syncing server and scl repo..")
        rhscl_repo, server_repo = sync_rh_repos_to_satellite(org)
        cap_repo = sync_capsule_subscription_to_capsule_ak(org)
        maint_repo = sync_maintenance_repos_to_satellite_for_capsule(org)
        captools_repo = sync_sattools_repos_to_satellite_for_capsule(org)
        repos_map = {
            'ansible': ans_repo,
            'rhscl': rhscl_repo,
            "server": server_repo,
            'capsule': cap_repo,
            'maintenance': maint_repo,
            'capsule_tools': captools_repo,
        }
        return repos_map

    def lifecycle_setup(org):
        """
        Use to create the lifecycle environment for the non specific group
        """
        logger.info("Creating lifecycle environment..")
        lib_lce = entities.LifecycleEnvironment(nailgun_conf, organization=org).search(
            query={"search": "name=Library"}
        )[0]
        try:
            dev_lce = entities.LifecycleEnvironment(
                nailgun_conf, organization=org, name="Dev", prior=lib_lce
            ).create()
        except Exception as ex:
            logger.warn(ex)
            dev_lce = entities.LifecycleEnvironment(nailgun_conf, organization=org).search(
                query={"search": "name=Dev"}
            )[0]
        try:
            entities.LifecycleEnvironment(
                nailgun_conf, organization=org, name="QA", prior=dev_lce
            ).create()
        except Exception as ex:
            logger.warn(ex)
        return dev_lce

    def content_view_setup(org, lce, repos_map):
        """
            Use to create the content view and promote it to the sacrificed group
        """
        logger.info("Creating content view..")
        cv_name = f'{settings.upgrade.os}_capsule_cv'
        try:
            cv = entities.ContentView(nailgun_conf, name=cv_name, organization=org).create()
        except Exception as ex:
            logger.warn(ex)
            cv = entities.ContentView(nailgun_conf, name=cv_name, organization=org).search(
                query={"search": f"name={cv_name}"}
            )[0]
        cv.repository = repos_map.values()
        cv.update(['repository'])
        logger.info("content view publish operation started successfully")
        try:
            start_time = job_execution_time("CV_Publish")
            call_entity_method_with_timeout(cv.read().publish, timeout=5000)
            job_execution_time(
                f"content view {cv.name} publish operation(In past time-out value "
                f"was 2500 but in current execution we set it 5000)",
                start_time,
            )
        except Exception as exp:
            logger.critical(f"content view {cv.name} publish failed with exception {exp}")
            # Fix of 1770940, 1773601
            logger.info(f"resuming the cancelled content view {cv.name} publish task")
            resume_failed_task()
        logger.info(f"content view {cv.name} published successfully")

        logger.info("Promoting content view..")
        cv = cv.read()
        cv.version[-1].promote(data={'environment_ids': [lce.id]})
        return cv

    def activation_key_setup(org, cv, lce, repos_map):
        """
        Use to create the activation key for capsule upgrade
        """
        logger.info("Creating activation key..")
        ak_name = settings.upgrade.capsule_ak[settings.upgrade.os]
        try:
            ak = entities.ActivationKey(
                nailgun_conf, organization=org, environment=lce, content_view=cv,
                name=ak_name
            ).create()
        except Exception as ex:
            logger.warn(ex)
            ak = entities.ActivationKey(nailgun_conf, organization=org).search(
                query={"search": f"name={ak_name}"}
            )[0]
        # Add subscriptions to AK
        add_satellite_subscriptions_in_capsule_ak(ak, org)
        for repo_name, repo_object in repos_map.items():
            if repo_name not in ['ansible', 'rhscl', 'server'] and \
                    settings.upgrade.distribution != "cdn":
                add_satellite_subscriptions_in_capsule_ak(ak, org, custom_repo=repo_object)
            ak_content_override(org, ak_name, repo_object)
    org_object = entities.Organization(nailgun_conf).search(
        query={'search': f'name="{DEFAULT_ORGANIZATION}"'}
    )[0]

    activation_key_status = activation_key_availability_check(org_object)
    if not activation_key_status:
        manifest_upload(org_object)
        repos_map_object = repos_sync(org_object)
        lce_object = lifecycle_setup(org_object)
        cv_object = content_view_setup(org_object, lce_object, repos_map_object)
        activation_key_setup(org_object, cv_object, lce_object, repos_map_object)
        return True
    else:
        logger.info(f"{settings.upgrade.capsule_ak[settings.upgrade.os]} Activation key is "
                    f"configured")
        return False


def ak_content_override(org, ak_name, repo):
    """
    A helper to override content of an Activation Key
    :param org: Organization where the content is managed.
    :param ak_name: Name of the AK
    :param repo: Repo to be overriden
    """
    with fabric_settings(warn_only=True):
        result = run(f"hammer activation-key content-override --organization-id {org.id} "
                     f"--name {ak_name} --content-label {repo.repo_id} --value 1")
        if result.return_code == 0:
            logger.info(f"content-override for {repo.repo_id} was set successfully")
        else:
            logger.warn(result)


def ak_add_subscription(org, ak, sub_name):
    """
    A helper to add a subscription to an Activation Key
    :param org: Organization where the content is managed
    :param ak: Activation Key to be changed
    :param sub_name: Name of the subscription to be added
    """
    sub = entities.Subscription(nailgun_conf).search(
        query={'organization_id': f'{org.id}',
               'search': f'name={sub_name}'})[0]
    ak.add_subscriptions(data={
        'quantity': 1,
        'subscription_id': sub.id,
    })
    logger.info(f"custom subscription {sub.name} added successfully to the AK {ak.name}")
