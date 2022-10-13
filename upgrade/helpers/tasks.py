"""A set of tasks to help upgrade Satellite and Capsule.

Many commands are affected by environment variables. Unless stated otherwise,
all environment variables are required.
"""
import re
import socket
import sys
import time
from datetime import datetime
from io import StringIO
from random import randrange

import requests
from automation_tools import setup_alternate_capsule_ports
from automation_tools import setup_fake_manifest_certificate
from automation_tools import setup_foreman_discovery
from automation_tools.repository import disable_repos
from automation_tools.repository import enable_repos
from automation_tools.satellite6.capsule import generate_capsule_certs
from automation_tools.utils import get_discovery_image
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
from packaging.version import Version

from upgrade.helpers import nailgun_conf
from upgrade.helpers import settings
from upgrade.helpers.constants.constants import CAPSULE_SUBSCRIPTIONS
from upgrade.helpers.constants.constants import CUSTOM_CONTENT
from upgrade.helpers.constants.constants import CUSTOM_SAT_REPO
from upgrade.helpers.constants.constants import DEFAULT_LOCATION
from upgrade.helpers.constants.constants import DEFAULT_ORGANIZATION
from upgrade.helpers.constants.constants import DEFAULT_ORGANIZATION_LABEL
from upgrade.helpers.constants.constants import OS_REPOS
from upgrade.helpers.constants.constants import os_ver
from upgrade.helpers.constants.constants import RH_CONTENT
from upgrade.helpers.logger import logger
from upgrade.helpers.tools import call_entity_method_with_timeout
from upgrade.helpers.tools import host_pings

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
                logger.warning(f'No capsule availble in the capsule list retry {attempt} '
                               f'after exception: {exp}')
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
            logger.warning(err)
        with fabric_settings(warn_only=True):
            result = run(f"hammer capsule content add-lifecycle-environment --organization-id "
                         f"{org.id} --lifecycle-environment 'Dev'  --name {capsule}")
            if result.return_code == 0:
                logger.info("for Capsule 'Dev' lifecycle environment added successfully")
            else:
                logger.warning(result)


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
        nailgun_conf, name=f"{name}", url=f"{proxy_url}",
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
                logger.warning(result)


def check_settings_for_upgrade(product):
    """Checks if required settings are provided

    :param string product: The product name to upgrade
    """
    failure = []
    # The upgrade product
    if product not in settings.upgrade.products:
        failure.append(f'Product name should be one of {", ".join(settings.upgrade.products)}')
    # Check If OS is set for creating an instance name in rhevm
    if not settings.upgrade.os:
        failure.append('Please provide OS version as rhel7 or rhel8 and retry !')
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
    """
    logger.info('Syncing latest capsule repos in Satellite ...')
    capsule_ak = settings.upgrade.capsule_ak[settings.upgrade.os]
    if capsule_ak is None:
        logger.highlight("The AK name is not provided for Capsule upgrade. Aborting...")
        sys.exit(1)
    org = entities.Organization(nailgun_conf, id=1).read()
    logger.info("Refreshing the attached manifest")
    entities.Subscription(nailgun_conf, organization=org).refresh_manifest(
        data={'organization_id': org.id}, timeout=5000
    )
    ak = entities.ActivationKey(nailgun_conf, organization=org).search(
        query={'search': f'name={capsule_ak}'})[0]
    add_satellite_subscriptions_in_capsule_ak(ak, org)
    logger.info(f"activation key {capsule_ak} used for capsule subscription and "
                f"it found on the satellite")
    cv = ak.content_view.read()
    lenv = ak.environment.read()
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

    # Add capsule and satclient custom prod subscription to capsules
    client = 'client' if Version(settings.upgrade.to_version) > Version('6.10') else 'tools'
    client_repo = settings.repos[f'sat{client}_repo'][settings.upgrade.os]
    if client_repo:
        add_custom_product_subscription_to_hosts(
            org, CUSTOM_CONTENT[f'capsule_{client}']['prod'], capsules
        )
    if settings.repos.capsule_repo:
        add_custom_product_subscription_to_hosts(
            org, CUSTOM_CONTENT['capsule']['prod'], capsules
        )


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
    if settings.upgrade.distribution != 'cdn':
        try:
            cap_product = entities.Product(
                nailgun_conf, name=CUSTOM_CONTENT['capsule']['prod'], organization=org).create()
        except Exception as ex:
            logger.warning(ex)
            cap_product = entities.Product(nailgun_conf, organization=org).search(
                query={"search": f'name={CUSTOM_CONTENT["capsule"]["prod"]}'}
            )[0]
        try:
            cap_repo = entities.Repository(
                nailgun_conf,
                name=CUSTOM_CONTENT['capsule']['reposet'],
                product=cap_product,
                url=settings.repos.capsule_repo,
                organization=org,
                content_type='yum',
            ).create()
        except Exception as ex:
            logger.warning(ex)
            cap_repo = entities.Repository(
                nailgun_conf, organization=org, product=cap_product
            ).search(query={"search": f'name={CUSTOM_CONTENT["capsule"]["repo"]}'})[0]
        logger.info("capsule repository {} created successfully for product {}".
                    format(CUSTOM_CONTENT['capsule']['reposet'],
                           CUSTOM_CONTENT['capsule']['prod']))
    else:
        # y-stream cdn upgrade support
        capsule_prod = RH_CONTENT['capsule']['prod']
        capsule_reposet = RH_CONTENT['capsule']['reposet']
        if from_version != to_version:
            with fabric_settings(warn_only=True):
                result = run(f'hammer repository-set enable --product '
                             f'"{capsule_prod}" --basearch {arch} --releasever {to_version}'
                             f' --name "{capsule_reposet}" '
                             f'--organization-id {org.id}')
                if result.return_code == 0:
                    logger.info("capsule repo enabled successfully")
                elif result.return_code == 70:
                    logger.info("capsule repo already enabled so the error code 70 is expected")
                else:
                    logger.warning(result)

        cap_product = entities.Product(
            nailgun_conf,
            name=capsule_prod,
            organization=org
        ).search(query={'per_page': 100})[0]
        logger.info(f"CDN capsule product {capsule_prod} is enabled.")
        cap_reposet = entities.RepositorySet(
            nailgun_conf, name=capsule_reposet, product=cap_product
        ).search()[0]
        logger.info(f'entities of repository {capsule_reposet} search completed successfully')
        try:
            cap_reposet.enable(
                data={
                    'basearch': 'x86_64', 'releasever': '7Server', 'organization_id': org.id
                })
        except requests.exceptions.HTTPError as exp:
            logger.warning(exp)
        cap_repo = entities.Repository(
            nailgun_conf, name=RH_CONTENT['capsule']['repo']).search(
            query={'organization_id': org.id, 'per_page': 100}
        )[0]
        logger.info(f"capsule repositoryset {RH_CONTENT['capsule']['repo']} "
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
        logger.warning(f"Capsule repository sync failed with exception: {exp}")
        repos_sync_failure_remiediation(org, cap_repo, timeout=4000)
    job_execution_time(f"entity repository {cap_repo.name} sync (In past time-out value was "
                       f"2500 but in current execution we set it 4000)", start_time)
    logger.info(f"entities repository sync operation completed successfully "
                f"for name {cap_repo.name}")
    if settings.upgrade.distribution != 'cdn':
        cap_repo.repo_id = CUSTOM_CONTENT['capsule']['reposet']
    else:
        cap_repo.repo_id = RH_CONTENT['capsule']['label']
    return cap_repo


def sync_os_repos_to_satellite(org):
    """
    Task to sync redhat repositories which will later be used for capsule upgrade.
    :param org: ``nailgun.entities.Organization` entity of capsule
    :returns list: os repos nailgun objects
    """
    ent_repos = []
    for repo in OS_REPOS.values():
        arch = 'x86_64'
        relver = str(os_ver) if os_ver > 7 else f'{os_ver}Server'
        ent_product = entities.Product(
            nailgun_conf, name=repo['prod'], organization=org).search(query={'per_page': 100})[0]
        logger.info(f'product: {ent_product.name} is present')
        ent_reposet = entities.RepositorySet(
            nailgun_conf, name=repo['reposet'], product=ent_product).search()[0]
        logger.info(f'repository set: {ent_reposet.name} is present')
        try:
            ent_reposet.enable(
                data={'basearch': arch, 'releasever': relver, 'organization_id': org.id})
            logger.info(f'repository: {ent_reposet.name} for {arch} {relver} enabled successfully')
        except requests.exceptions.HTTPError as exp:
            logger.warning(exp)
        time.sleep(20)
        # Sync enabled Repo from cdn
        ent_repo = entities.Repository(nailgun_conf, name=repo['repo']).search(
            query={'organization_id': org.id, 'per_page': 100})[0]
        logger.info(f'repository: {ent_repo.name} sync is about to start')
        start_time = job_execution_time('Repository sync')
        try:
            call_entity_method_with_timeout(
                entities.Repository(nailgun_conf, id=ent_repo.id).sync, timeout=6000)
        except Exception as exp:
            logger.warning(f'RH repository sync failed with exception: {exp}')
            repos_sync_failure_remiediation(org, ent_repo, timeout=6000)
        job_execution_time(f'repository: {ent_repo.name} sync has taken', start_time)
        logger.info(f'repository: {ent_repo.name} sync operation completed successfully')
        ent_repo.repo_id = repo['label']
        ent_repos.append(ent_repo)
    return ent_repos


def sync_satclient_repo_to_satellite_for_capsule(org):
    """
    Creates custom / Enables RH satclient / tools repo on satellite and syncs for capsule upgrade

    :param org: `nailgun.entities.Organization` entity of capsule
    :return: `nailgun.entities.repository` entity for capsule
    """
    arch = 'x86_64'
    client = 'client' if Version(settings.upgrade.to_version) > Version('6.10') else 'tools'
    client_repo_url = settings.repos[f'sat{client}_repo'][settings.upgrade.os]
    if client_repo_url:
        repo = CUSTOM_CONTENT[f'capsule_{client}']
        try:
            ent_product = entities.Product(
                nailgun_conf, name=repo['prod'], organization=org).create()
        except Exception as ex:
            logger.warning(ex)
            ent_product = entities.Product(nailgun_conf, organization=org).search(
                query={"search": f'name={repo["prod"]}'})[0]
        try:
            ent_repo = entities.Repository(
                nailgun_conf, name=repo['reposet'], organization=org, product=ent_product,
                url=client_repo_url, content_type='yum'
            ).create()
        except Exception as ex:
            logger.warning(ex)
            ent_repo = entities.Repository(
                nailgun_conf, organization=org, product=ent_product
            ).search(query={"search": f'name={repo["repo"]}'})[0]
        logger.info(f"custom product: {repo['prod']} and repository: {repo['reposet']} created"
                    f"from satellite-{client} repo url")
        ent_repo.repo_id = repo['reposet']
    else:
        if settings.upgrade.from_version != settings.upgrade.to_version:
            repo = RH_CONTENT[client]
            with fabric_settings(warn_only=True):
                result = run(f"hammer repository-set enable --product \"{repo['prod']}\" "
                             f"--name \"{repo['reposet']}\" --organization-id {org.id} "
                             f'--basearch {arch} ')
                if result.return_code == 0:
                    logger.info("client repo enabled successfully")
                elif result.return_code == 70:
                    logger.info("client repo already enabled so the error code 70 is expected")
                else:
                    logger.warning(result)
        ent_product = entities.Product(
            nailgun_conf, name=repo['prod'], organization=org).search(query={'per_page': 100})[0]
        logger.info(f'product: {ent_product.name} is present')
        ent_reposet = entities.RepositorySet(
            nailgun_conf, name=repo['reposet'], product=ent_product).search()[0]
        logger.info(f'repository set: {ent_reposet.name} is present')
        try:
            ent_reposet.enable(data={'basearch': arch, 'organization_id': org.id})
            logger.info(f'repository: {ent_reposet.name} for {arch} enabled successfully')
        except requests.exceptions.HTTPError as exp:
            logger.warning(exp)
        time.sleep(5)
        ent_repo = entities.Repository(nailgun_conf, name=repo['repo']).search(
            query={'organization_id': org.id, 'per_page': 100})[0]
        logger.info(f"repository: {repo['repo']} search completed successfully")
        ent_repo.repo_id = repo['label']

    logger.info(f"repository: {ent_repo.name} sync is about to start")
    start_time = job_execution_time("Entities repository sync")
    try:
        call_entity_method_with_timeout(
            entities.Repository(nailgun_conf, id=ent_repo.id).sync, timeout=5000)
    except Exception as exp:
        logger.warning(f"repository: {ent_repo.name} sync failed with exception: {exp}")
        repos_sync_failure_remiediation(org, ent_repo, timeout=5000)
    job_execution_time(f'repository: {ent_repo.name} sync has taken', start_time)
    logger.info(f'repository: {ent_repo.name} sync completed successfully')
    return ent_repo


def sync_maintenance_repo_to_satellite_for_capsule(org):
    """
    Uses to enable the maintenance repo for capsule upgrade
    :param org: `nailgun.entities.Organization` entity of capsule
    :return: `nailgun.entities.repository` entity for capsule
    """
    arch = 'x86_64'
    relver = str(os_ver) if os_ver > 7 else f'{os_ver}Server'
    if settings.upgrade.distribution != 'cdn':
        repo = CUSTOM_CONTENT['maintenance']
        try:
            ent_product = entities.Product(
                nailgun_conf,
                name=repo['prod'],
                organization=org).create()
        except Exception as ex:
            logger.warning(ex)
            ent_product = entities.Product(nailgun_conf, organization=org).search(
                query={"search": f'name={repo["prod"]}'})[0]
        try:
            ent_repo = entities.Repository(
                nailgun_conf,
                name=repo['reposet'],
                product=ent_product, url=settings.repos.satmaintenance_repo,
                organization=org,
                content_type='yum'
            ).create()
        except Exception as ex:
            logger.warning(ex)
            ent_repo = entities.Repository(
                nailgun_conf, organization=org, product=ent_product
            ).search(query={"search": f'name={repo["repo"]}'})[0]
        logger.info(f"the custom maintenance product "
                    f"{repo['prod']} "
                    f"and repository {repo['reposet']} is created from "
                    "satmaintenance downstream repo")
        ent_repo.repo_id = repo['reposet']
    else:
        repo = RH_CONTENT['maintenance']
        with fabric_settings(warn_only=True):
            result = run(f"hammer repository-set enable --product \"{repo['prod']}\" "
                         f"--name \"{repo['reposet']}\" --organization-id {org.id} "
                         f"--basearch {arch} --releasever {relver}")
            if result.return_code == 0:
                logger.info("maintenance repo enabled successfully")
            elif result.return_code == 70:
                logger.info("maintenance repo already enabled so the error code 70 is expected")
            else:
                logger.warning(result)
        ent_product = entities.Product(nailgun_conf, name=repo['prod'], organization=org).search(
            query={'per_page': 100})[0]
        logger.info(f'product: {ent_product.name} is present')
        ent_reposet = entities.RepositorySet(
            nailgun_conf, name=repo['reposet'], product=ent_product).search()[0]
        logger.info(f'repository set: {ent_reposet.name} is present')
        try:
            ent_reposet.enable(data={'basearch': arch, 'organization_id': org.id})
            logger.info(f'repository: {ent_reposet.name} for {arch} enabled successfully')
        except requests.exceptions.HTTPError as exp:
            logger.warning(exp)
        time.sleep(5)
        ent_repo = entities.Repository(
            nailgun_conf, name=repo['repo']).search(
            query={'organization_id': org.id, 'per_page': 100}
        )[0]
        logger.info(f"entities repository search completed successfully for maintenance "
                    f"repo {repo['repo']}")
        ent_repo.repo_id = repo['label']

    logger.info(f"entities repository sync started successfully for "
                f"maintenance repo {ent_repo.name}")
    start_time = job_execution_time("Entities repository sync")
    try:
        call_entity_method_with_timeout(
            entities.Repository(nailgun_conf, id=ent_repo.id).sync, timeout=5000)
    except Exception as exp:
        logger.warning(f"RH Maintenance repository sync failed with exception: {exp}")
        repos_sync_failure_remiediation(org, ent_repo, timeout=5000)

    job_execution_time(f"entities repository {ent_repo.name} sync(In past time-out "
                       f"value was 2500 but in current execution we set it 5000)", start_time)
    logger.info(f"entities repository sync completed successfully for "
                f"maintenance repo {ent_repo.name}")
    return ent_repo


def add_subscription_for_capsule(ak, org):
    """
    Adds capsule, maintenance, (rhscl, rhel server, ansible | baseos, appstream) subscriptions
    in capsule ak
    :param ak: `nailgun.entities.ActivationKey` of capsule
    :param org: `nailgun.entities.org` of capsule
    """
    os_repos = sync_os_repos_to_satellite(org)
    cap_repo = sync_capsule_subscription_to_capsule_ak(org)
    maintenance_repo = sync_maintenance_repo_to_satellite_for_capsule(org)
    satclient_repo = sync_satclient_repo_to_satellite_for_capsule(org)
    sat_repos = [cap_repo, maintenance_repo, satclient_repo]

    # to update each repos fresh content view read is required,
    # otherwise it does not consider the pending repos from the point of failure.
    for repo_name in os_repos + sat_repos:
        cv = ak.content_view.read()
        if repo_name:
            cv.repository += [repo_name]
            try:
                cv.update(['repository'])
                logger.info(f"repository {repo_name.name} enabled in content view {cv.name}")
            except requests.exceptions.HTTPError as exp:
                logger.warning(exp)
    ak = ak.read()
    for os_repo in os_repos:
        ak.content_override(
            data={'content_override': {'content_label': os_repo.repo_id, 'value': '1'}}
        )
        logger.info(f'ak: {ak.name} content override succeeded for label: {os_repo.name}')

    if settings.repos.capsule_repo is None:
        ak.content_override(
            data={'content_override': {'content_label': cap_repo.repo_id, 'value': '1'}}
        )
        logger.info(f"activation key content override successfully for "
                    f"content label:{cap_repo.name}")
    else:
        cap_sub = entities.Subscription(nailgun_conf, organization=org).search(
            query={'search': f'name={CUSTOM_CONTENT["capsule"]["prod"]}'})[0]
        try:
            ak.add_subscriptions(
                data={'quantity': 1, 'subscription_id': cap_sub.id}
            )
        except Exception as err:
            logger.warning(err)
        logger.info(f"capsule subscription {cap_sub.name} added successfully to capsule ak")

    if settings.repos.satmaintenance_repo is None:
        ak.content_override(
            data={'content_override': {'content_label': maintenance_repo.repo_id, 'value': '1'}}
        )
        logger.info(f"cdn activation key successfully override for maintenance content_label"
                    f" {maintenance_repo.name}")
    else:
        maintenance_sub = entities.Subscription(nailgun_conf, organization=org).search(
            query={'search': f'name={CUSTOM_CONTENT["maintenance"]["prod"]}'})[0]
        try:
            ak.add_subscriptions(
                data={'quantity': 1, 'subscription_id': maintenance_sub.id}
            )
            logger.info(f" maintenance subscription {maintenance_sub.id} added successfully to "
                        f"capsule ak")
        except Exception as err:
            logger.warning(err)

    client = 'client' if Version(settings.upgrade.to_version) > Version('6.10') else 'tools'
    client_repo_url = settings.repos[f'sat{client}_repo'][settings.upgrade.os]
    if client_repo_url is None:
        ak.content_override(
            data={'content_override': {'content_label': satclient_repo.repo_id, 'value': '1'}}
        )
        logger.info(f"cdn activation key successfully override for "
                    f"capsule content_label {satclient_repo.name}")
    else:
        client_sub = entities.Subscription(nailgun_conf, organization=org).search(
            query={'search': f'name={CUSTOM_CONTENT["capsule_client"]["prod"]}'})[0]
        try:
            ak.add_subscriptions(data={
                'quantity': 1,
                'subscription_id': client_sub.id,
            })
            logger.info(f"custom capsule Client subscription {client_sub.id} added "
                        f"successfully to capsule ak")
        except Exception as err:
            logger.warn(err)


def sync_client_repo_to_upgrade(client_os, hosts, ak_name):
    """This syncs the client repos in Satellite server and also attaches
    the new client repo subscription onto each client

    :param string client_os: The client OS of which tools repo to be synced
        e.g: rhel6, rhel7
    :param list hosts: The list of capsule hostnames to which new capsule
        repo subscription will be attached
    """
    client = 'client' if Version(settings.upgrade.to_version) > Version('6.10') else 'tools'
    client_repo_url = settings.repos[f'sat{client}_repo'][client_os]
    if client_repo_url is None:
        logger.warning(f'The Client Repo URL for {client_os} is not provided.')
        logger.highlight(f"The Client Repo URL for {client_os} is not provided "
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
    client_product_name = CUSTOM_CONTENT[client]['prod'].format(client_os=client_os)
    client_repo_name = CUSTOM_CONTENT[client]['reposet'].format(client_os=client_os)
    try:
        ent_product = entities.Product(
            nailgun_conf, name=client_product_name, organization=org).create()
    except Exception as exp:
        logger.warning(exp)
        ent_product = entities.Product(nailgun_conf, organization=org).search(
            query={'search': f'name={client_product_name}'})[0]
    logger.info(f'product: {ent_product.name} is present')
    try:
        ent_repo = entities.Repository(
            nailgun_conf, name=client_repo_name, product=ent_product, url=client_repo_url,
            organization=org, content_type='yum').create()
    except Exception as exp:
        logger.warning(exp)
        ent_repo = entities.Repository(nailgun_conf, organization=org).search(
            query={'search': f'name={client_repo_name}'})[0]
    logger.info(f'repository: {ent_repo.name} is present')
    start_time = job_execution_time(f'repository: {ent_repo.name} sync is about to start')
    entities.Repository(nailgun_conf, id=ent_repo.id).sync()
    job_execution_time(f'repository: {ent_repo.name} sync operation', start_time)
    logger.info(f'repository: {ent_repo.name} sync completed successfully')
    cv.repository += [ent_repo]
    try:
        cv.update(['repository'])
    except requests.exceptions.HTTPError as exp:
        logger.warning(exp)
    logger.info(f'content view: {cv.name} publish is about to start')
    try:
        start_time = job_execution_time("CV_Publish")
        call_entity_method_with_timeout(cv.read().publish, timeout=5000)
        # expected time out value is 3500
        job_execution_time(f"content view: {cv.name} publish has taken", start_time)
    except Exception as exp:
        logger.critical(f"content view: {cv.name} publish failed with exception {exp}")
    logger.info(f'content view: {cv.name} published successfully')
    published_ver = entities.ContentViewVersion(
        nailgun_conf, id=max([cv_ver.id for cv_ver in cv.read().version])).read()
    logger.info(f"details of the published_ver is {published_ver}")
    start_time = job_execution_time("CV_Promotion")
    logger.info(f"content view: {cv.name} version promotion is about to start")
    published_ver.promote(data={'environment_ids': [lenv.id], 'force': False})
    job_execution_time(f"content view: {cv.name} promotion has taken", start_time)
    logger.info(f"content view: {cv.name} version has been promoted successfully")
    client_sub = entities.Subscription(nailgun_conf, organization=org).search(
        query={'search': 'name={0}'.format(client_product_name)})[0]
    try:
        ak.add_subscriptions(data={'quantity': 1, 'subscription_id': client_sub.id})
    except Exception as exp:
        logger.warning(exp)
    logger.info(f'subscription: {client_sub.name} added successfully to ak: {ak.name}')
    # Add this latest tools repo to hosts to upgrade
    sub = entities.Subscription(nailgun_conf, organization=org).search(
        query={'search': 'name={0}'.format(client_product_name)})[0]
    logger.info(f'hosts: {hosts}')
    for host in hosts:
        host = entities.Host(nailgun_conf, organization=org).search(
            query={'search': f'name={host}'}
        )[0]
        entities.HostSubscription(nailgun_conf, host=host).add_subscriptions(
            data={'subscriptions': [{'id': sub.id, 'quantity': 1}]})
        logger.info(f"subscription: {sub.name} assigned to host: {host.name}")


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
        logger.warning(f'libvirt host {settings.libvirt.libvirt_hostname} '
                       f'is not working, please check and fix it in the code')
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


def capsule_certs_update(cap_host):
    """
    Use to generate the capsule certificate on the satellite and upload it on
    the capsule
    """
    tar_path = generate_capsule_certs(cap_host, True)
    scp_opts = '-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null'
    run(f"scp {scp_opts} {tar_path} root@{cap_host}:/root")


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
    """
    Task which install foreman-maintain tool.
    """
    env.disable_known_hosts = True
    # setting up foreman-maintain repo
    setup_foreman_maintain_repo()
    if settings.upgrade.distribution != 'cdn':
        for repo, repodata in CUSTOM_SAT_REPO.items():
            if repo != 'maintenance':
                repository_setup(**repodata)


def setup_foreman_maintain_repo():
    """
    Task which setup repo for foreman-maintain.
    """
    # setting up foreman-maintain repo
    if settings.upgrade.distribution == 'cdn':
        enable_repos(RH_CONTENT['maintenance']['label'])
    else:
        repository_setup(**CUSTOM_SAT_REPO['maintenance'])


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


def upgrade_using_foreman_maintain(satellite=True):
    """Task which upgrades the product using foreman-maintain tool.

    :param bool satellite: True (=satellite upgrade) or False (=capsule upgrade)
    """
    env.disable_known_hosts = True

    def satellite_upgrade_check(zstream=False):
        with warn_only():
            version_suffix = '.z' if zstream else ''
            run(f'foreman-maintain upgrade check --plaintext '
                f'--whitelist="repositories-validate" '
                f'--target-version {settings.upgrade.to_version}{version_suffix} -y')

    def capsule_upgrade_check(zstream=False):
        with warn_only():
            version_suffix = '.z' if zstream else ''
            run(f'foreman-maintain upgrade check --plaintext '
                f'--whitelist="repositories-validate" '
                f'--target-version {settings.upgrade.to_version}{version_suffix} -y')

    def satellite_upgrade(zstream=False):
        """ This inner function is used to perform Y & Z satellite stream upgrade"""
        version_suffix = '.z' if zstream else ''
        command = (
            f'foreman-maintain upgrade run --plaintext '
            f'--whitelist="{settings.upgrade.whitelist_param}" '
            f'--target-version {settings.upgrade.to_version}{version_suffix} -y'
        )
        # use Beta until becomes GA
        if settings.upgrade.to_version == '6.12':
            with shell_env(FOREMAN_MAINTAIN_USE_BETA='1'):
                run(command)
        else:
            run(command)

    def capsule_upgrade(zstream=False):
        """ This inner function is used to perform Y & Z stream Capsule upgrade"""
        version_suffix = '.z' if zstream else ''
        # z capsule stream upgrade, If we do not whitelist the repos setup then cdn
        # repos of target version gets enabled.
        whitelist_param = '--whitelist="repositories-validate,repositories-setup"'
        if settings.upgrade.distribution == 'cdn':
            whitelist_param = ''
        run(f'foreman-maintain upgrade run --plaintext {whitelist_param} '
            f'--target-version {settings.upgrade.to_version}{version_suffix} -y')

    with warn_only():
        run('foreman-maintain upgrade list-versions')  # we usually trigger self-upgrade here
    zstream = settings.upgrade.from_version == settings.upgrade.to_version
    if satellite:
        satellite_upgrade_check(zstream)
        preup_time = datetime.now().replace(microsecond=0)
        satellite_upgrade(zstream)
    else:
        capsule_upgrade_check(zstream)
        preup_time = datetime.now().replace(microsecond=0)
        capsule_upgrade(zstream)
    postup_time = datetime.now().replace(microsecond=0)

    if satellite:
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


def add_baseOS_repos(**repos):
    """This adds the latest repo to the host to fetch latest available packages

    :param repos: dict of repos to be added in form of {reponame: baseurl}.
    """
    for name, url in repos.items():
        repository_setup(name, name, url)


def puppet_autosign_hosts(hosts, append=True):
    """Appends host entries to puppet autosign conf file

    :param list hosts: The list of hosts to be added for autoconf
    :param bool append: Whether to add or append
    """
    append = '>>' if append else '>'
    for host in hosts:
        run('echo "{0}" {1} /etc/puppetlabs/puppet/autosign.conf'.format(host, append))


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
                logger.warning(f"Task id {task['id']} failed with {ex}")
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
    """
    Task to generate custom certs for satellite
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


def add_custom_product_subscription_to_hosts(org, product, hosts):
    """Adds custom product subscription to given list of hosts

    :param object org: Organization object
    :param str product: The custom product name
    :param list hosts: List of content host names
    """
    for host in hosts:
        sub = entities.Subscription(nailgun_conf, organization=org).search(
            query={'search': f'name={product}'})[0]
        host = entities.Host(nailgun_conf).search(query={'search': f'name={host}'})[0]
        entities.HostSubscription(nailgun_conf, host=host).add_subscriptions(
            data={'subscriptions': [{'id': sub.id, 'quantity': 1}]})


def repository_setup(repository, repository_name, base_url, enable=1, gpgcheck=0):
    """
    This is generic fucntion which is used to setup the repository
    :param str repository: uniq repository ID
    :param str repository_name: repository name in string
    :param str base_url: repository url
    :param int enable: repoitory enable(1) or disable(0)
    :param int gpgcheck: verify GPG authenticity pass 1 otherwise pass 0
    :return:
    """
    repofile = StringIO()
    repofile.write(f'[{repository}]\n')
    repofile.write(f'name={repository_name}\n')
    repofile.write(f'baseurl={base_url}\n')
    repofile.write(f'enabled={enable}\n')
    repofile.write(f'gpgcheck={gpgcheck}\n')
    put(local_path=repofile, remote_path=f'/etc/yum.repos.d/{repository}.repo')
    repofile.close()


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


def upgrade_task(upgrade_type, cap_host=None):
    """
    :param string upgrade_type: upgrade type would be an string either it is
    satellite or capsule
    :param string cap_host: hostname for capsule's major version upgrade
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
            for i in range(1, 6):
                result = run('hammer ping', warn_only=True)
                if result.succeeded:
                    break
                else:
                    logger.warning("hammer ping: try {i}: some components are in failed state")
                time.sleep(30 * i)
        for action in set(["status -b", satellite_services_action]):
            result = run(f'foreman-maintain service {action}', warn_only=True)
            if result.return_code != 0:
                logger.warning(f"foreman maintain {action} command failed")


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
            query={'search': f'name="{DEFAULT_LOCATION}"'})[0]
        scap_content_profile_id = entities.ScapContents(
            nailgun_conf, id=scap_content.id).read().scap_content_profiles[0]['id']
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
        logger.highlight(f'Time taken by task {task_name} - {total_job_execution_time}')
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
        logger.warning(f"These task ids {','.join(output.split())} are still in paused state, "
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
        entities.Subscription(nailgun_conf, organization=org).refresh_manifest(
            data={'organization_id': org.id},
            timeout=5000
        )
    except Exception as exp:
        logger.warning(f'manifst refresh failed due to {exp}')
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
            logger.warning(f'Retry:{attempt} Repos sync remediation failed due to {exp}')


def foreman_maintain_package_update(zstream=False, fetch_content_from_sat=False):
    """
    Install the latest fm rubygem-foreman_maintain to get the latest y-stream upgrade path.
    """
    if zstream:
        with warn_only():
            run('foreman-maintain upgrade list-versions')
    else:
        if settings.upgrade.distribution == 'cdn':
            run('foreman-maintain self-upgrade')
        else:
            product_label = CUSTOM_CONTENT['maintenance']['prod']
            repo_label = CUSTOM_CONTENT['maintenance']['reposet']
            maintenance_repo = (
                f'Default_Organization_{product_label}_{repo_label}'
                if fetch_content_from_sat
                else CUSTOM_SAT_REPO['maintenance']['repository']
            )
            run(f'foreman-maintain self-upgrade --maintenance-repo-label {maintenance_repo}')
    run('rpm -qa rubygem-foreman_maintain')


def yum_repos_cleanup():
    """
    Use to remove non-required repos from the /etc/yum.repos.d
    """
    with fabric_settings(warn_only=True):
        result = run("rm -f /etc/yum.repos.d/*")
        if result.return_code != 0:
            logger.warning(result)


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
            subscription_map = [f"awk '/{CAPSULE_SUBSCRIPTIONS['sat_infra']}/{{print $1}}'"]
        else:
            subscription_map = [f"awk '/{custom_repo.product.read_json()['name']}/{{print $1}}'"]

        for subscription in subscription_map:
            output = run(f'hammer subscription list --organization-id="{org.id}" | {subscription}')
            if output.return_code > 0:
                logger.warning(output)
            else:
                for sub_id in output.splitlines():
                    ak_output = run(f'hammer activation-key add-subscription --subscription-id='
                                    f'"{sub_id}" --id="{ak.id}"')
                    if ak_output.return_code > 0:
                        logger.warning(output)


def satellite_restore_setup():
    """
    Use to setup the satellite restore for upstream satellite clone
    """
    answer_file = '/usr/share/satellite-clone/satellite-clone-vars.yml'
    backup_dir = (f'{settings.clone.mount_dir}/{settings.clone.customer_name}'
                  f'{settings.upgrade.from_version.replace(".", "")}')

    with fabric_settings(warn_only=True):
        os_repos = settings.repos[f'rhel{os_ver}_os']
        if isinstance(os_repos, str):
            os_repos = {f'rhel{os_ver}': os_repos}
        add_baseOS_repos(**os_repos)
        run(f"yum -d1 install -y nfs-utils; mkdir -p {settings.clone.mount_dir}")
    run(f'mount {settings.clone.db_server}:/root/customer-dbs {settings.clone.mount_dir}')

    if os_ver == 7:
        enable_disable_repo(enable_repos_name=[f'rhel-{os_ver}-server-ansible-2.9-rpms'])
    if settings.clone.upstream:
        run(f"yum -d1 install -y ansible{'-core' if os_ver > 7 else ''}")
        run(f"cd /usr/share; git clone -q {settings.clone.satellite_clone_upstream_repos}")
    else:
        run('yum -d1 repolist')
        run('yum -d1 install -y satellite-clone')
    run(
        f'echo "satellite_version: {settings.upgrade.from_version}">>{answer_file};'
        f'echo "backup_dir: {backup_dir}">>{answer_file};'
        f'echo "restorecon: {settings.clone.restorecon}">>{answer_file};'
        f'echo "register_to_portal: {settings.clone.register_to_portal}">>{answer_file};'
        f'echo "activationkey: {settings.clone.ak}">>{answer_file};'
        f'echo "org: {settings.clone.org}">>{answer_file}')


def satellite_restore():
    """
    Use to run the satellite restore
    """
    clone_dir = '/usr/share/satellite-clone'
    ping_output = run(f'cd {clone_dir}; ansible all -i inventory -m ping -u root')
    if ping_output.return_code != 0:
        logger.highlight('The provided inventory is not accessible. Aborting...')
        sys.exit(1)
    if settings.clone.upstream:
        clone_cmd = f'cd {clone_dir}; ansible-playbook -i inventory satellite-clone-playbook.yml'
    else:
        clone_cmd = 'satellite-clone -y'
    prerestore_time = datetime.now().replace(microsecond=0)
    with fabric_settings(warn_only=True):
        restore_output = run(clone_cmd)
        # Workaround for BZ#2109608 (remove once fixed in 6.11.z)
        if restore_output.return_code != 0:
            if settings.upgrade.from_version == '6.11' and os_ver == 8:
                run('echo "skip_satellite_rpm_check: true">>'
                    '/usr/share/satellite-clone/satellite-clone-vars.yml')
                run('yum -d1 --disableplugin foreman-protector distro-sync -y')
                restore_output = run(clone_cmd)
        # EOW
        postrestore_time = datetime.now().replace(microsecond=0)
        logger.highlight(f'Time taken by satellite restore - '
                         f'{str(postrestore_time - prerestore_time)}')
        run(f"umount {settings.clone.mount_dir}")
        # Remove the workaround once BZ 2051912 gets fixed.
        for line in restore_output.split('\n'):
            if re.search(r'some executors are not responding, '
                         r'check /foreman_tasks/dynflow/status', line):
                upgrade_validation(upgrade_type="satellite", satellite_services_action="restart")
                break
        else:
            if restore_output.return_code != 0:
                logger.highlight("Satellite restore completed with some error. Aborting...")
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
                     f"--plaintext --skip-pulp-content -y /tmp")
        postyum_time = datetime.now().replace(microsecond=0)
        logger.highlight(f'Time taken by {satellite_backup_type} satellite backup - '
                         f'{str(postyum_time - preyum_time)}')
        if output.return_code != 0:
            logger.warning(f"satellite backup failed in {satellite_backup_type} mode")


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
            run(f'subscription-manager register --user={settings.subscription.rhn_username} '
                f'--password={settings.subscription.rhn_password} --force')
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
                entities.Subscription(nailgun_conf, organization=org).upload(
                    data={'organization_id': org.id},
                    files={'content': manifest}
                )
        except Exception as ex:
            logger.warning(ex)
        entities.Subscription(nailgun_conf, organization=org).refresh_manifest(
            data={'organization_id': org.id},
            timeout=5000
        )

    def repos_sync(org):
        """
        Use to setup the repository sync
        """
        logger.info("Syncing Ansible Engine repo..")
        logger.info("Syncing server and scl repo..")
        os_repos = sync_os_repos_to_satellite(org)
        cap_repo = sync_capsule_subscription_to_capsule_ak(org)
        maint_repo = sync_maintenance_repo_to_satellite_for_capsule(org)
        sat_repos = [cap_repo, maint_repo]
        return os_repos + sat_repos

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
            logger.warning(ex)
            dev_lce = entities.LifecycleEnvironment(nailgun_conf, organization=org).search(
                query={"search": "name=Dev"}
            )[0]
        try:
            entities.LifecycleEnvironment(
                nailgun_conf, organization=org, name="QA", prior=dev_lce
            ).create()
        except Exception as ex:
            logger.warning(ex)
        return dev_lce

    def content_view_setup(org, lce, repos):
        """
            Use to create the content view and promote it to the sacrificed group
        """
        logger.info("Creating content view..")
        cv_name = f'{settings.upgrade.os}_capsule_cv'
        try:
            cv = entities.ContentView(nailgun_conf, name=cv_name, organization=org).create()
        except Exception as ex:
            logger.warning(ex)
            cv = entities.ContentView(nailgun_conf, name=cv_name, organization=org).search(
                query={"search": f"name={cv_name}"}
            )[0]
        cv.repository = repos
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

    def activation_key_setup(org, cv, lce, repos):
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
            logger.warning(ex)
            ak = entities.ActivationKey(nailgun_conf, organization=org).search(
                query={"search": f"name={ak_name}"}
            )[0]
        # Add subscriptions to AK
        add_satellite_subscriptions_in_capsule_ak(ak, org)
        for repo in repos:
            print(repo)
            if settings.upgrade.distribution != "cdn":
                # and repo_name not in ['ansible', 'rhscl', 'server']
                add_satellite_subscriptions_in_capsule_ak(ak, org, custom_repo=repo)
            ak_content_override(org, ak_name, repo)

    org_object = entities.Organization(nailgun_conf).search(
        query={'search': f'name="{DEFAULT_ORGANIZATION}"'})[0]
    activation_key_status = activation_key_availability_check(org_object)
    if not activation_key_status:
        manifest_upload(org_object)
        all_repos = repos_sync(org_object)
        lce_object = lifecycle_setup(org_object)
        cv_object = content_view_setup(org_object, lce_object, all_repos)
        activation_key_setup(org_object, cv_object, lce_object, all_repos)
        return True
    else:
        logger.info(f'ak: {settings.upgrade.capsule_ak[settings.upgrade.os]} is configured')
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
            logger.warning(result)


def ak_add_subscription(org, ak, sub_name):
    """
    A helper to add a subscription to an Activation Key
    :param org: Organization where the content is managed
    :param ak: Activation Key to be changed
    :param sub_name: Name of the subscription to be added
    """
    sub = entities.Subscription(nailgun_conf, organization=org).search(
        query={'organization_id': f'{org.id}',
               'search': f'name={sub_name}'})[0]
    ak.add_subscriptions(data={
        'quantity': 1,
        'subscription_id': sub.id,
    })
    logger.info(f"custom subscription {sub.name} added successfully to the AK {ak.name}")
