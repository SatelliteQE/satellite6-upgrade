"""A set of tasks to help upgrade Satellite and Capsule.

Many commands are affected by environment variables. Unless stated otherwise,
all environment variables are required.
"""
import os
import sys
import time
import requests
import socket
from datetime import datetime

from automation_tools import (
    setup_rhv_ca,
    setup_alternate_capsule_ports,
    setup_fake_manifest_certificate,
)
from automation_tools import setup_capsule_firewall
from automation_tools import setup_foreman_discovery, setup_avahi_discovery
from automation_tools.repository import enable_repos, disable_repos
from automation_tools.utils import get_discovery_image, update_packages
from automation_tools.satellite6.capsule import generate_capsule_certs
from nailgun import entities
from robozilla.decorators import bz_bug_is_open
from upgrade.helpers.constants import customcontents, rhelcontents
from upgrade.helpers.docker import (
    attach_subscription_to_host_from_content_host
)
from upgrade.helpers.logger import logger
from upgrade.helpers.tools import call_entity_method_with_timeout
from fabric.api import env, execute, put, run, warn_only
from fabric.context_managers import shell_env
if sys.version_info[0] == 2:
    from StringIO import StringIO  # (import-error) pylint:disable=F0401
else:  # pylint:disable=F0401,E0611
    from io import StringIO

logger = logger()


class ProductNotFound(Exception):
    """Raise if the product you are searching is not found"""


def check_necessary_env_variables_for_upgrade(product):
    """Checks if necessary Environment Variables are provided

    :param string product: The product name to upgrade
    """
    failure = []
    # The upgrade product
    products = ['satellite', 'capsule', 'client', 'longrun', 'n-1']
    if product not in products:
        failure.append('Product name should be one of {0}.'.format(
            ', '.join(products)))
    # Check If OS is set for creating an instance name in rhevm
    if not os.environ.get('OS'):
        failure.append('Please provide OS version as rhel7 or rhel6, '
                       'And retry !')
    if failure:
        logger.warning('Cannot Proceed Upgrade as:')
        for msg in failure:
            logger.warning(msg)
        sys.exit(1)
    return True


def sync_capsule_repos_to_upgrade(capsules):
    """This syncs capsule repo in Satellite server and also attaches
    the capsule repo subscription to each capsule

    :param list capsules: The list of capsule hostnames to which new capsule
    repo subscription will be attached

    Following environment variable affects this function:

    CAPSULE_URL
        The url for capsule repo from latest satellite compose.
        If not provided, capsule repo from Red Hat repositories will be enabled
    TOOLS_URL_RHEL{}.format(os_ver)
        The url for capsuletools repo from latest satellite compose.
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
    to_version = os.environ.get('TO_VERSION')
    logger.info('Syncing latest capsule repos in Satellite ...')
    os_ver = os.environ.get('OS')[-1]
    capsule_repo = os.environ.get('CAPSULE_URL')
    capsuletools_url = os.environ.get('TOOLS_URL_RHEL{}'.format(os_ver))
    ak_name = os.environ.get(
        'CAPSULE_AK', os.environ.get('RHEV_CAPSULE_AK'))
    if ak_name is None:
        logger.warning(
            'The AK name is not provided for Capsule upgrade! Aborting...')
        sys.exit(1)
    org = entities.Organization(id=1).read()
    ak = entities.ActivationKey(organization=org).search(
        query={'search': 'name={}'.format(ak_name)})[0]
    logger.info("Activation key {} used for capsule subscription has found".
                format(ak_name))
    cv = ak.content_view.read()
    lenv = ak.environment.read()
    # Fix dead pulp tasks
    if os_ver == '6':
        run('for i in pulp_resource_manager pulp_workers pulp_celerybeat; '
            'do service $i restart; done')
    _sync_capsule_subscription_to_capsule_ak(ak)
    logger.info("Capsule subscription to AK {} has added successfully".format(ak.name))
    if float(to_version) >= 6.3:
        _add_additional_subscription_for_capsule(ak, capsuletools_url)
    # Publishing and promoting the CV with all newly added capsule, capsuletools,
    # rhscl and server repos combine
    logger.info("Content view publish operation has started successfully")
    try:
        start_time = job_execution_time("CV_Publish")
        call_entity_method_with_timeout(cv.read().publish, timeout=5000)
        job_execution_time("Content view {} publish operation(In past time-out value was "
                           "2500 but in current execution we set it 5000)"
                           .format(cv.name), start_time)
    except Exception as exp:
        logger.critical("Content view {} publish failed with exception {}"
                        .format(cv.name, exp))
        # Fix of 1770940, 1773601
        logger.info("Resuming the cancelled content view {} publish task"
                    .format(cv.name))
        output = run(
            "sleep 100; hammer task resume|grep ') Task identifier:'|"
            "awk -F':' '{print $2}'; sleep 100")
        for task_id in output.split():
            run('hammer task progress --id {}'.format(task_id))
        job_execution_time("Content view {} publish operation(In past time-out value was "
                           "2500 but in current execution we set it 5000) "
                           .format(cv.name), start_time)
    logger.info("Content view publish operation has completed successfully")
    published_ver = entities.ContentViewVersion(
        id=max([cv_ver.id for cv_ver in cv.read().version])).read()
    logger.info("Content view {} promotion has started successfully".
                format(cv.name))
    published_ver.promote(data={'environment_id': lenv.id, 'force': False})
    logger.info("Content view {} promotion has completed successfully".
                format(cv.name))
    # Add capsule and tools custom prod subscription to capsules
    if capsule_repo:
        add_custom_product_subscription_to_hosts(
            customcontents['capsule']['prod'], capsules)
    if float(to_version) >= 6.3:
        if capsuletools_url:
            add_custom_product_subscription_to_hosts(
                customcontents['capsule_tools']['prod'], capsules)


def _sync_capsule_subscription_to_capsule_ak(ak):
    """Syncs to_version capsule contents, adds to the CV and attaches contents to the AK through
    which Capsule is registered

    :param ak: ```nailgun.entities.ActivationKey``` used for capsule subscription
    """
    cv = ak.content_view.read()
    org = ak.organization
    capsule_repo = os.environ.get('CAPSULE_URL')
    to_version = os.environ.get('TO_VERSION')
    os_ver = os.environ.get('OS')[-1]
    # If custom capsule repo is not given then
    # enable capsule repo from Redhat Repositories
    if capsule_repo:
        cap_product = entities.Product(
            name=customcontents['capsule']['prod'], organization=org).create()
        cap_repo = entities.Repository(
            name=customcontents['capsule']['repo'], product=cap_product, url=capsule_repo,
            organization=org, content_type='yum').create()
        logger.info("Capsule repository {} created successfully for product {}".
                    format(customcontents['capsule']['repo'],
                           customcontents['capsule']['prod']))
    else:
        cap_product = entities.Product(
            name=rhelcontents['capsule']['prod'],
            organization=org
        ).search(query={'per_page': 100})[0]
        logger.info("RHEL Capsule Product {} is found enabled.".format(
            rhelcontents['capsule']['prod']))
        cap_reposet = entities.RepositorySet(
            name=rhelcontents['capsule']['repo'].format(cap_ver=to_version, os_ver=os_ver),
            product=cap_product
        ).search()[0]
        logger.info("Entities of Repository {} search completed successfully".
                    format(rhelcontents['capsule']['repo']
                           .format(cap_ver=to_version, os_ver=os_ver)))
        try:
            cap_reposet.enable(
                data={'basearch': 'x86_64', 'releasever': '7Server', 'organization_id': org.id})
        except requests.exceptions.HTTPError as exp:
            logger.warn(exp)
        cap_repo = entities.Repository(
            name=rhelcontents['capsule']['repofull'].format(
                cap_ver=to_version, os_ver=os_ver, arch='x86_64')
        ).search(query={'organization_id': org.id, 'per_page': 100})[0]
        logger.info("Capsule Repository's repofull {} search completed successfully".
                    format(rhelcontents['capsule']['repofull']
                           .format(cap_ver=to_version, os_ver=os_ver, arch='x86_64')))

    logger.info("Entities repository sync operation started successfully for name {}".
                format(cap_repo.name))
    start_time = job_execution_time("Entity repository sync")
    # Expected value 2500
    call_entity_method_with_timeout(entities.Repository(id=cap_repo.id).sync, timeout=4000)
    job_execution_time("Entity repository {} sync (In past time-out value was 2500 "
                       "but in current execution we set it 4000)"
                       .format(cap_repo.name), start_time)
    logger.info("Entities repository sync operation completed successfully for name {}".
                format(cap_repo.name))
    # Add repos to CV
    cv.repository += [cap_repo]
    cv.update(['repository'])
    ak = ak.read()
    if capsule_repo:
        cap_sub = entities.Subscription().search(
            query={'search': 'name={0}'.format(customcontents['capsule']['prod'])})[0]
        ak.add_subscriptions(data={
            'quantity': 1,
            'subscription_id': cap_sub.id,
        })
        logger.info("subscription {} in Activation key used for Capsule subscription "
                    "added successfully for subscription {}".
                    format(cap_sub.id, cap_sub.name))
    else:
        ak.content_override(
            data={
                'content_override': {
                    'content_label': rhelcontents['capsule']['label'].format(
                        cap_ver=to_version, os_ver=os_ver),
                    'value': '1'}
            }
        )
        logger.info("Activation key content override successfully for content label:{}".
                    format(rhelcontents['capsule']['label'].format(cap_ver=to_version,
                                                                   os_ver=os_ver)))


def _sync_rh_repos_to_satellite(org):
    """Task to sync Redhat Repositories to latest required during upgrade

    :param org: ```nailgun.entities.Organization``` entity of capsule
    :returns tuple: RHSCL and Redhat 7 Server repo name, label name and
        product name
    """
    rhelver = '7'
    arch = 'x86_64'
    # Enable rhscl repository
    scl_product = entities.Product(
        name=rhelcontents['rhscl_sat64']['prod'], organization=org
    ).search(query={'per_page': 100})[0]
    logger.info("Red Hat Software Collection for product {} is enabled and found".
                format(rhelcontents['rhscl_sat64']['prod']))
    scl_reposet = entities.RepositorySet(
        name=rhelcontents['rhscl']['repo'].format(os_ver=rhelver), product=scl_product
    ).search()[0]
    logger.info("Red Hat Software Collection for repos {} is already enabled and found".
                format(rhelcontents['rhscl']['repo'].format(os_ver=rhelver)))
    try:
        scl_reposet.enable(
            data={'basearch': arch, 'releasever': '7Server', 'organization_id': org.id})
        logger.info("Red Hat Software collection repository enabled successfully")
    except requests.exceptions.HTTPError as exp:
        logger.warn(exp)
    time.sleep(20)
    # Sync enabled Repo from cdn
    scl_repo = entities.Repository(
        name=rhelcontents['rhscl']['repofull'].format(os_ver=rhelver, arch=arch)
    ).search(query={'organization_id': org.id, 'per_page': 100})[0]
    attempt = 0
    # Fixed upgrade issue: #368
    while attempt <= 3:
        try:
            call_entity_method_with_timeout(
                entities.Repository(id=scl_repo.id).sync, timeout=3500)
            break
        except requests.exceptions.HTTPError as exp:
            logger.warn("Retry{} after exception: {}".format(attempt, exp))
            # Wait 10 seconds to reattempt the same retry option
            time.sleep(10)
            attempt += 1
    # Enable RHEL 7 Server repository
    server_product = entities.Product(
        name=rhelcontents['server']['prod'], organization=org).search(query={'per_page': 100})[0]
    logger.info("Product {} is already enabled and found".
                format(rhelcontents['server']['prod']))
    server_reposet = entities.RepositorySet(
        name=rhelcontents['server']['repo'].format(os_ver=rhelver), product=server_product
    ).search()[0]
    logger.info("Repository {} is already enabled and found".
                format(rhelcontents['server']['repo']))
    try:
        server_reposet.enable(
            data={'basearch': arch, 'releasever': '7Server', 'organization_id': org.id})
        logger.info("Repository enabled successfully for base arch {}, 7Server".format(arch))
    except requests.exceptions.HTTPError as exp:
        logger.warn(exp)
    time.sleep(20)
    # Sync enabled Repo from cdn
    server_repo = entities.Repository(
        name=rhelcontents['server']['repofull'].format(os_ver=rhelver, arch=arch)
    ).search(query={'organization_id': org.id, 'per_page': 100})[0]
    logger.info("Entities repository sync operation has started successfully"
                " for name {}".format(server_repo.name))
    start_time = job_execution_time("Repository sync")
    call_entity_method_with_timeout(entities.Repository(id=server_repo.id).sync,
                                    timeout=6000)
    job_execution_time("Repository {} sync (In past time-out value was 3600 but in "
                       "current execution we set it 6000) ".format(server_repo.name),
                       start_time)
    logger.info("Entities repository sync operation has completed successfully"
                " for name {}".format(server_repo.name))
    scl_repo.repo_id = rhelcontents['rhscl']['label'].format(os_ver=rhelver)
    server_repo.repo_id = rhelcontents['server']['label'].format(os_ver=rhelver)
    return scl_repo, server_repo


def _sync_sattools_repos_to_satellite_for_capsule(capsuletools_url, org):
    """Creates custom / Enables RH Tools repo on satellite and syncs for capsule upgrade

    :param str capsuletools_url: The capsule tools repo url
    :param org: ```nailgun.entities.Organization``` entity of capsule

    :returns: ```nailgun.entities.repository``` entity for capsule
    """
    to_ver = os.environ.get('TO_VERSION')
    rhelver = '7'
    arch = 'x86_64'
    if capsuletools_url:
        captools_product = entities.Product(
            name=customcontents['capsule_tools']['prod'], organization=org).create()
        captools_repo = entities.Repository(
            name=customcontents['capsule_tools']['repo'],
            product=captools_product, url=capsuletools_url, organization=org, content_type='yum'
        ).create()
        logger.info("The custom tools product {} and repository {} is created from "
                    "capsule tools url".format(customcontents['capsule_tools']['prod'],
                                               customcontents['capsule_tools']['repo']))
    else:
        captools_product = entities.Product(
            name=rhelcontents['tools']['prod'], organization=org
        ).search(query={'per_page': 100})[0]
        cap_reposet = entities.RepositorySet(
            name=rhelcontents['tools']['repo'].format(sat_ver=to_ver, os_ver=rhelver),
            product=captools_product).search()[0]
        logger.info("The custom tools product {} and repository {} is created from "
                    "capsule tools url".format(rhelcontents['tools']['prod'],
                                               rhelcontents['tools']['repo']))
        try:
            cap_reposet.enable(data={'basearch': arch, 'organization_id': org.id})
            logger.info("Capsule repository enabled successfully for arch {} and org {}".
                        format(arch, org.id))
        except requests.exceptions.HTTPError as exp:
            logger.warn(exp)
        time.sleep(5)
        captools_repo = entities.Repository(
            name=rhelcontents['tools']['repofull'].format(
                sat_ver=to_ver, os_ver=rhelver, arch=arch)
        ).search(query={'organization_id': org.id, 'per_page': 100})[0]
        logger.info("Entities repository search completed successfully for tools "
                    "repo {}".format(rhelcontents['tools']['repofull'].
                                     format(sat_ver=to_ver, os_ver=rhelver, arch=arch)))
    logger.info("Entities repository sync started successfully for capsule repo name {}".
                format(captools_repo.name))
    start_time = job_execution_time("Entities repository sync")
    call_entity_method_with_timeout(entities.Repository(id=captools_repo.id).sync,
                                    timeout=5000)
    job_execution_time("Entities repository {} sync(In past time-out value was 2500 "
                       "but in current execution we set it 5000)"
                       .format(captools_repo.name), start_time)
    logger.info("Entities repository sync completed successfully for capsule repo name {}"
                .format(captools_repo.name))
    captools_repo.repo_id = rhelcontents['tools']['label'].format(
        os_ver=rhelver, sat_ver=to_ver)
    return captools_repo


def _add_additional_subscription_for_capsule(ak, capsuletools_url):
    """Adds rhscl, rhel server and tools subscription to capsule ak

    Required only for satellite version 6.3 and higher

    :param ak: ```nailgun.entities.ActivationKey``` of capsule
    :param capsuletools_repo: If None then enables redhat tools repo else,
        creates custom repo with this url
    """
    cv = ak.content_view.read()
    org = ak.organization
    scl_repo, server_repo = _sync_rh_repos_to_satellite(org)
    logger.info("Sync operation of SCL and Server repositories  on satellite has "
                "completed successfully")
    captools_repo = _sync_sattools_repos_to_satellite_for_capsule(capsuletools_url, org)
    logger.info("Sync Operation of Tools repository repositories  to Satellite for "
                "Capsule has completed successfully")
    cv.repository += [scl_repo, server_repo, captools_repo]
    cv.update(['repository'])
    ak = ak.read()
    ak.content_override(
        data={'content_override': {'content_label': scl_repo.repo_id, 'value': '1'}}
    )
    logger.info("Activation key successfully override for content_label {}".
                format(scl_repo.name))
    ak.content_override(
        data={'content_override': {'content_label': server_repo.repo_id, 'value': '1'}}
    )
    if not capsuletools_url:
        ak.content_override(
            data={
                'content_override': {'content_label': captools_repo.repo_id, 'value': '1'}
            })
        logger.info("Activation key successfully override for capsule content_label {}".
                    format(captools_repo.name))
    else:
        captools_sub = entities.Subscription().search(
            query={'search': 'name={0}'.format(customcontents['capsule_tools']['prod'])})[0]
        ak.add_subscriptions(data={
            'quantity': 1,
            'subscription_id': captools_sub.id,
        })
        logger.info("Capsule Tools subscription {} added successfully to capsule AK".
                    format(captools_sub.id))


def sync_tools_repos_to_upgrade(client_os, hosts):
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
    client_os = client_os.upper()
    tools_repo_url = os.environ.get('TOOLS_URL_{}'.format(client_os))
    if tools_repo_url is None:
        logger.warning('The Tools Repo URL for {} is not provided '
                       'to perform Client Upgrade !'.format(client_os))
        sys.exit(1)
    ak_name = os.environ.get(
        'CLIENT_AK_{}'.format(client_os),
        os.environ.get('RHEV_CLIENT_AK_{}'.format(client_os))
    )
    if ak_name is None:
        logger.warning('The AK details are not provided for {0} Client '
                       'upgrade!'.format(client_os))
        sys.exit(1)
    org = entities.Organization().search(
        query={'search': 'name="{}"'.format("Default Organization")})[0]
    ak = entities.ActivationKey(organization=org).search(
        query={'search': 'name={}'.format(ak_name)})[0]
    cv = ak.content_view.read()
    lenv = ak.environment.read()
    toolsproduct_name = customcontents['tools']['prod'].format(client_os=client_os)
    toolsrepo_name = customcontents['tools']['repo'].format(client_os=client_os)
    # adding sleeps in between to avoid race conditions
    tools_product = entities.Product(name=toolsproduct_name, organization=org).create()
    tools_repo = entities.Repository(
        name=toolsrepo_name, product=tools_product, url=tools_repo_url,
        organization=org, content_type='yum').create()
    logger.info("Entities product {} and repository {} is created successfully".
                format(tools_product, toolsrepo_name))
    start_time = job_execution_time("tools repo sync operation")
    entities.Repository(id=tools_repo.id).sync()
    job_execution_time("tools repo {} sync operation".format(toolsrepo_name), start_time)
    logger.info("Entities repository sync operation has completed successfully for tool "
                "repos name {}".format(tools_repo.name))
    cv.repository += [tools_repo]
    cv.update(['repository'])
    logger.info("Content view publish operation is started successfully")
    try:
        start_time = job_execution_time("CV_Publish")
        call_entity_method_with_timeout(cv.read().publish, timeout=5000)
        # expected time out value is 3500
        job_execution_time("Content view {} publish operation(In past time-out value was "
                           "3500 but in current execution we set it 5000) "
                           .format(cv.name), start_time)
    except Exception as exp:
        logger.critical("Content view {} publish failed with exception {}"
                        .format(cv.name, exp))
        # Fix of 1770940, 1773601
        logger.info("Resuming the cancelled content view {} publish task"
                    .format(cv.name))
        output = run("sleep 100; hammer task resume|grep ') Task identifier:'|"
                     "awk -F':' '{print $2}'; sleep 100")
        logger.info("The CV publish task {} has resumed successfully, "
                    "waiting for their completion".format(output))
        for task_id in output.split():
            run('hammer task progress --id {}'.format(task_id))
        job_execution_time("Content view {} publish operation(In past time-out value was "
                           "3500 but in current execution we set it 5000) "
                           .format(cv.name), start_time)

    logger.info("Content view has published successfully")
    published_ver = entities.ContentViewVersion(
        id=max([cv_ver.id for cv_ver in cv.read().version])).read()

    start_time = job_execution_time("CV_Promotion")
    logger.info("Published CV {} version promotion is started successfully"
                .format(cv.name))
    published_ver.promote(data={'environment_id': lenv.id, 'force': False})
    job_execution_time("Content view {} promotion ".format(cv.name), start_time)
    logger.info("Published CV {} version has promoted successfully".format(cv.name))
    tools_sub = entities.Subscription().search(
        query={'search': 'name={0}'.format(toolsproduct_name)})[0]
    ak.add_subscriptions(data={
        'quantity': 1,
        'subscription_id': tools_sub.id,
    })
    logger.info("Subscription added successfully in capsule activation key for name {}".
                format(tools_sub.name))
    # Add this latest tools repo to hosts to upgrade
    sub = entities.Subscription().search(
        query={'search': 'name={0}'.format(toolsproduct_name)})[0]
    for host in hosts:
        if float(os.environ.get('FROM_VERSION')) <= 6.1:
            # If not User Hosts then, attach sub to dockered clients
            if not all([
                os.environ.get('CLIENT6_HOSTS'),
                os.environ.get('CLIENT7_HOSTS')
            ]):
                docker_vm = os.environ.get('DOCKER_VM')
                execute(
                    attach_subscription_to_host_from_content_host,
                    sub.cp_id,
                    True,
                    host,
                    host=docker_vm)
            # Else, Attach subs to user hosts
            else:
                execute(
                    attach_subscription_to_host_from_content_host,
                    sub.cp_id,
                    host=host)
        else:
            host = entities.Host().search(query={'search': 'name={}'.format(host)})[0]
            entities.HostSubscription(host=host).add_subscriptions(
                data={'subscriptions': [{'id': sub.id, 'quantity': 1}]})


def post_upgrade_test_tasks(sat_host, cap_host=None):
    """Run set of tasks for post upgrade tests

    :param string sat_host: Hostname to run the tasks on
    :param list cap_host: Capsule hosts to run sync on
    """
    # Execute tasks as post upgrade tests are dependent
    certificate_url = os.environ.get('FAKE_MANIFEST_CERT_URL')
    if certificate_url is not None:
        execute(
            setup_fake_manifest_certificate,
            certificate_url,
            host=sat_host
        )
    sat_version = os.environ.get('TO_VERSION')
    execute(setup_alternate_capsule_ports, host=sat_host)
    if float(sat_version) > 6.1:
        # Update the Default Organization name, which was updated in 6.2
        logger.info("Update the Default Organization name, which was updated "
                    "in 6.2")
        org = entities.Organization().search(query={'search': 'label=Default_Organization'})[0]
        org.name = "Default Organization"
        org.update(['name'])
        # Update the Default Location name, which was updated in 6.2
        logger.info("Update the Default Location name, which was updated in "
                    "6.2")
        loc = entities.Location().search(query={'search': 'name="Default Location"'})[0]
        loc.name = "Default Location"
        loc.update(['name'])
        if bz_bug_is_open(1502505):
            logger.info(
                "Update the default_location_puppet_content value with "
                "updated location name.Refer BZ:1502505")
            puppet_location = entities.Setting().search(
                query={'search': 'name=default_location_puppet_content'}
            )[0]
            puppet_location.value = 'Default Location'
            puppet_location.update(['value'])
    # Increase log level to DEBUG, to get better logs in foreman_debug
    execute(lambda: run('sed -i -e \'/:level: / s/: .*/: '
                        'debug/\' /etc/foreman/settings.yaml'), host=sat_host)
    execute(foreman_service_restart, host=sat_host)
    # Execute task for template changes required for discovery feature
    if bz_bug_is_open(1850934):
        foreman_packages_installation_check(state="unlock", non_upgrade_task=True)
        workaround_section(1850934)
        foreman_packages_installation_check(state="lock", non_upgrade_task=True)
    else:
        execute(
            setup_foreman_discovery,
            sat_version=sat_version,
            host=sat_host
        )
    # Execute task for creating latest discovery iso required for unattended
    #  test
    env.disable_known_hosts = True
    execute(
        get_discovery_image,
        host=os.environ.get('LIBVIRT_HOSTNAME')
    )
    # Commenting out until GH issue:#135
    # Removing the original manifest from Default Organization (Org-id 1),
    # to allow test-cases to utilize the same manifest.
    # logger.info("Removing the Original Manifest from Default Organization")
    # execute(hammer, 'subscription delete-manifest --organization-id 1',
    #         host=sat_host)

    # Run Avahi Task on upgrade boxes for REX tests to run
    execute(lambda: run('yum remove -y epel*'), host=sat_host)
    execute(setup_avahi_discovery, host=sat_host)

    # setup RHEV certificate so it can be added as a CR
    execute(setup_rhv_ca, host=sat_host)


def capsule_sync(cap_host):
    """Run Capsule Sync as a part of job

    :param list cap_host: List of capsules to perform sync
    """
    capsule = entities.SmartProxy().search(
        query={'search': 'name={}'.format(cap_host)})[0]
    if float(os.environ.get('TO_VERSION')) >= 6.2:
        logger.info('Refreshing features for capsule host {0}'.
                    format(cap_host))
        capsule.refresh()
    logger.info('Running Capsule sync for capsule host {0}'.
                format(cap_host))
    capsule = entities.Capsule().search(
        query={'search': 'name={}'.format(cap_host)})[0]
    start_time = job_execution_time("Capsule content sync operation")
    capsule.content_sync()
    job_execution_time("Capsule content sync operation", start_time)


def foreman_service_restart():
    """Restarts the foreman-maintain services"""
    services = run('foreman-maintain service restart')
    if services.return_code > 0:
        logger.error('Unable to re-start the Satellite Services')
        sys.exit(1)


def check_ntpd():
    """Check if ntpd is running else start the service"""
    ntpd_check = run("service ntpd status", warn_only=True)
    if ntpd_check.return_code > 0:
        run("service ntpd start")
        run("chkconfig ntpd on")


def setup_foreman_maintain():
    """Task which install foreman-maintain tool.

    Environment Variables necessary to proceed Setup:
    -----------------------------------------------------

    DISTRIBUTION
        The satellite upgrade using internal or CDN distribution.
        e.g 'CDN','DOWNSTREAM'

    MAINTAIN_REPO
        URL of repo if distribution is DOWNSTREAM

    BASE_URL
        URL for the compose repository if distribution is DOWNSTREAM

    TOOLS_RHEL7
        URL for the satellite tools repo if distribution is DOWNSTREAM
    """
    env.disable_known_hosts = True
    # setting up foreman-maintain repo
    setup_foreman_maintain_repo()
    if os.environ.get('DISTRIBUTION') != 'CDN':
        # Add Sat6 repo from latest compose
        repository_setup("sat6",
                         "satellite 6",
                         "{}".format(os.environ.get('BASE_URL')),
                         1, 0)
        repository_setup("sat6tools7",
                         "satellite6-tools7",
                         "{}".format(os.environ.get('TOOLS_RHEL7')),
                         1, 0)

    # repolist
    run('yum repolist')
    # install foreman-maintain
    run('yum install rubygem-foreman_maintain -y')


def setup_foreman_maintain_repo():
    """Task which setup repo for foreman-maintain.

    Environment Variables necessary to proceed Setup:
    -----------------------------------------------------

    DISTRIBUTION
        The satellite upgrade using internal or CDN distribution.
        e.g 'CDN','DOWNSTREAM'

    MAINTAIN_REPO
        URL of repo if distribution is DOWNSTREAM
    """
    # setting up foreman-maintain repo
    if os.environ.get('DISTRIBUTION') == 'CDN':
        enable_repos('rhel-7-server-satellite-maintenance-6-rpms')
    else:
        repository_setup("foreman-maintain",
                         "foreman-maintain",
                         "{}".format(os.environ.get('MAINTAIN_REPO')),
                         1, 0)


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
    # setup hammer config
    if sat_host:
        run('mkdir -p /root/.hammer/cli.modules.d')
        hammer_file = StringIO()
        hammer_file.write('--- \n')
        hammer_file.write(' :foreman: \n')
        hammer_file.write('  :username: admin\n')
        hammer_file.write('  :password: changeme \n')
        put(local_path=hammer_file,
            remote_path='/root/.hammer/cli.modules.d/foreman.yml')
        hammer_file.close()

    with warn_only():
        if os.environ.get('FROM_VERSION') == os.environ.get('TO_VERSION'):
            # z stream upgrade
            run(f'foreman-maintain upgrade check --target-version '
                f'{os.environ.get("TO_VERSION")}.z -y')
        else:
            run(f'foreman-maintain upgrade check --target-version'
                f' {os.environ.get("TO_VERSION")} -y')

    def satellite_upgrade():
        """ This inner function is used to perform Y & Z satellite stream upgrade"""
        # whitelist disk-performance check
        if os.environ.get('FROM_VERSION') == os.environ.get('TO_VERSION'):
            # z stream satellite upgrade
            run(f'foreman-maintain upgrade run '
                f'--whitelist="disk-performance" '
                f'--target-version {os.environ.get("TO_VERSION")}.z -y')
        else:
            # use beta until 6.8 is GA
            if os.environ.get('TO_VERSION') == '6.8':
                with shell_env(FOREMAN_MAINTAIN_USE_BETA='1'):
                    run(f'foreman-maintain upgrade run --whitelist="disk-performance'
                        f'{os.environ["whitelisted_param"]}" --target-version '
                        f'{os.environ.get("TO_VERSION")} -y')
            else:
                run(f'foreman-maintain upgrade run --whitelist="disk-performance" '
                    f'--target-version {os.environ.get("TO_VERSION")} -y')

    def capsule_upgrade():
        """ This inner function is used to perform Y & Z stream Capsule upgrade"""
        if os.environ.get('FROM_VERSION') == os.environ.get('TO_VERSION'):
            # z capsule stream upgrade
            run(f'foreman-maintain upgrade run --target-version '
                f'{os.environ.get("TO_VERSION")}.z -y')
        else:
            run(f'foreman-maintain upgrade run --whitelist="repositories-validate, '
                f'repositories-setup" --target-version'
                f' {os.environ.get("TO_VERSION")} -y')

    satellite_upgrade() if sat_host else capsule_upgrade()


def upgrade_puppet3_to_puppet4():
    """Task which upgrade satellite 6.3 from puppet3 to puppet4.

    Environment Variables necessary to proceed Setup:
    -----------------------------------------------------

    DISTRIBUTION
        The satellite upgrade using internal or CDN distribution.
        e.g 'CDN','DOWNSTREAM'

    PUPPET4_REPO
        URL of puppet4 repo if distribution is DOWNSTREAM
    """
    env.disable_known_hosts = True
    # setting up puppet4 repo
    if os.environ.get('DISTRIBUTION') == 'CDN':
        enable_repos('rhel-7-server-satellite-6.3-puppet4-rpms')
    else:
        repository_setup("Puppet4",
                         "puppet4",
                         "{}".format(os.environ.get('PUPPET4_REPO')),
                         1, 0)

    # repolist
    run('yum repolist')
    # upgrade puppet
    run('satellite-installer --upgrade-puppet')


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


def setup_satellite_clone():
    """Task which install satellite-clone tool.

    Environment Variables necessary to proceed Setup:
    -----------------------------------------------------

    DISTRIBUTION
        The satellite upgrade using internal or CDN distribution.
        e.g 'CDN','DOWNSTREAM'

    MAINTAIN_REPO
        URL of repo if distribution is DOWNSTREAM

    BASE_URL
        URL for the compose repository if distribution is DOWNSTREAM
    """
    env.disable_known_hosts = True
    # setting up foreman-maintain repo
    if os.environ.get('DISTRIBUTION') == 'CDN':
        enable_repos('rhel-7-server-satellite-maintenance-6-rpms')
    else:
        repository_setup("maintainrepo",
                         "maintain",
                         "{}".format(os.environ.get('MAINTAIN_REPO')),
                         1, 0)

    # repolist
    run('yum repolist')
    # install foreman-maintain
    run('yum install satellite-clone -y')


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


def get_satellite_host():
    """Get the satellite hostname depending on which jenkins variables are set

    :return string : Returns the satellite hostname

    Environment Variable:

    RHEV_SAT_HOST
        This is set, if we are using internal RHEV Templates and VM for
        upgrade.
    SATELLITE_HOSTNAME
        This is set, in case user provides his personal satellite for
        upgrade.
        """
    return os.environ.get(
        'RHEV_SAT_HOST',
        os.environ.get('SATELLITE_HOSTNAME')
    )


def wait_untill_capsule_sync(capsule):
    """The polling function that waits for capsule sync task to finish

    :param capsule: A capsule hostname
    """
    cap = entities.Capsule().search(
        query={'search': 'name={}'.format(capsule)})[0]
    active_tasks = cap.content_get_sync()['active_sync_tasks']
    if len(active_tasks) >= 1:
        logger.info(
            'Wait for background capsule sync to finish on '
            'capsule: {}'.format(cap.name))
        start_time = job_execution_time("capsule_sync")
        for task in active_tasks:
            entities.ForemanTask(id=task['id']).poll(timeout=9000)
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
        .format(hostname=os.environ.get('SERVER_HOSTNAME'))
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
    from_version = os.environ.get('FROM_VERSION')
    for host in hosts:
        sub = entities.Subscription().search(
            query={'search': 'name={0}'.format(product)})[0]
        if float(from_version) <= 6.1:
            execute(
                attach_subscription_to_host_from_content_host, sub.cp_id, host=host)
        else:
            host = entities.Host().search(query={'search': 'name={}'.format(host)})[0]
            entities.HostSubscription(host=host).add_subscriptions(
                data={'subscriptions': [{'id': sub.id, 'quantity': 1}]})


def check_status_of_running_task(command, attempt):
    """
        This function is used to check the running tasks status via foreman-maintain,
        If task is running then wait for their completion otherwise move to
        the next step.
    """
    retry = 0
    while retry <= attempt:
        status = run("{} >/dev/null 2>&1; echo $?".format(command))
        if status:
            logger.info("Attempt{}: Command: {}\n"
                        "Task is still in running state".
                        format(retry, command))
            retry += 1
        else:
            logger.info("Command: {}\n "
                        "Check for running tasks:: [OK]".format(command))
            return 0
    else:
        logger.info("Command: {}\n"
                    "Exceeded the maximum attempt to check the "
                    "tasks running status".format(command))


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
    satellite_repo.write('[{}]\n'.format(repository))
    satellite_repo.write('name=s{}\n'.format(repository_name))
    satellite_repo.write('baseurl={0}\n'.format(base_url))
    satellite_repo.write('enabled={}\n'.format(enable))
    satellite_repo.write('gpgcheck={}\n'.format(gpgcheck))
    put(local_path=satellite_repo,
        remote_path='/etc/yum.repos.d/{}.repo'.format(repository))
    satellite_repo.close()


def foreman_maintain_upgrade(base_url):
    """
    The purpose of this function is to setup the foreman-maintain and perform the
    foreman-mantain upgrade"
    :param str base_url: It is used to check the repository selection whether
    it from CDN or from Downstream
    """
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


def enable_disable_repo(enable_repo_name, disable_repo_name):
    """
    The purpose of this function is to enable and disable the
    repository as per requirements.
    :param list enable_repo_name: This will take the list of
    repository which you are going to enable
    :param list disable_repo_name: This will take the
    list of repository which you are going to disable
    """
    if disable_repo_name:
        [disable_repos('{}'.format(repo), silent=True) for repo in disable_repo_name]
    if enable_repo_name:
        [enable_repos('{}'.format(repo)) for repo in disable_repo_name]


def repository_cleanup(repo_name):
    """
    The purpose of this function to perform the repository cleanup on the basis of
    their name.
    :param str repo_name: repository name
    """
    for fname in os.listdir('/etc/yum.repos.d/'):
        if repo_name in fname.lower():
            os.remove('/etc/yum.repos.d/{}'.format(fname))


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
    # Updating the packages again after setting sat6 repo
    logger.info('Updating system and {} packages... '.format(upgrade_type))
    preyum_time = datetime.now().replace(microsecond=0)
    update_packages(quiet=False)
    postyum_time = datetime.now().replace(microsecond=0)
    logger.highlight('Time taken for system and {} packages update'
                     ' - {}'.format(upgrade_type, str(postyum_time - preyum_time)))
    # non zStream capsule upgrade
    if sat_host and cap_host:
        execute(
            generate_capsule_certs,
            cap_host,
            True,
            host=sat_host
        )
        execute(lambda: run("scp -o 'StrictHostKeyChecking no' {0}-certs.tar "
                            "root@{0}:/home/".format(cap_host)), host=sat_host)
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
        run('satellite-installer --scenario {0} '
            '--certs-tar-file /home/{1}-certs.tar '
            '--certs-update-all'.format(upgrade_type, cap_host))
    else:
        run('satellite-installer --scenario {}'.format(upgrade_type))


def upgrade_validation(upgrade_type=False):
    """
    In this function we check the system states after upgrade.
    :param bool upgrade_type: if upgrade_type is True then we check both the services.
    """
    if upgrade_type:
        run('hammer ping', warn_only=True)
    if bz_bug_is_open(1860444) and not upgrade_type:
        run('foreman-maintain service restart', warn_only=True)
    else:
        run('foreman-maintain service status', warn_only=True)


def update_scap_content():
    """ The purpose of this function is to perform deletion of old scap-contents
        and then uploading new scap-contents. It also deletes scap-policies and creates
         new scap-policies with new scap-contents. """

    def create_policy(scap_content, policy_name):
        """This function is used for creating scap policy

        :param scap_content: Name of scap-content to be used while creating policy.
        :param str policy_name: Name of policy to be created.
        """
        org = entities.Organization().search(
            query={'search': 'name="{}"'.format("Default Organization")})[0]
        loc = entities.Location().search(query={'search': 'name="Default Location"'})[0]
        scap_content_profile_id = entities.ScapContents(
            id=scap_content.id).read().scap_content_profiles[0]['id']
        entities.CompliancePolicies(
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
                entities.CompliancePolicies(id=policies_search[entity].id).delete()
            elif content_name == "scap_content_search":
                entities.ScapContents(id=scap_content_search[entity].id).delete()

    compliance_policies = ['RHEL 7 policy', 'RHEL 6 policy']
    scap_content_name = ['Red Hat rhel7 default content', 'Red Hat rhel6 default content']
    scap_content_search = entities.ScapContents().search()
    policies_search = entities.CompliancePolicies().search()
    scap(policies_search, "policies_search")
    scap(scap_content_search, "scap_content_search")
    run('foreman-rake foreman_openscap:bulk_upload:default')
    updated_scap_content = entities.ScapContents().search()
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
    if os.environ.get('FOREMAN_MAINTAIN_SATELLITE_UPGRADE') != 'true' or non_upgrade_task:
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


def workaround_section(bz):
    """
    This function used to apply the workaround of provided bugzilla.
    :param int bz: Pass the bugzilla number
    """
    if bz == 1850934:
        run("yum install -y foreman-discovery-image")
        run('hammer -u admin -p changeme template update '
            '--name "PXELinux global default" --locked "false"')
        template_file = run('mktemp')
        run(f'hammer -u admin -p changeme template dump --name '
            f'"PXELinux global default" > {template_file}')
        run('hammer -u admin -p changeme settings set --name '
            '"default_pxe_item_global" --value="discovery"')
        run(rf'sed -i -e "s/^TIMEOUT\s\+[0-9]\+/TIMEOUT 5/" {template_file}')
        run(f'hammer -u admin -p changeme template update --name '
            f'"PXELinux global default" --type "PXELinux" --file {template_file}')
        run(f'rm -rf {template_file}')
