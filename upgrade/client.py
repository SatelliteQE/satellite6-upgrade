import re
import sys
import time

from automation_tools.repository import disable_repos
from fabric.api import env
from fabric.api import execute
from fabric.api import run

from upgrade.helpers import settings
from upgrade.helpers.docker import docker_execute_command
from upgrade.helpers.docker import generate_satellite_docker_clients_on_rhevm
from upgrade.helpers.docker import refresh_subscriptions_on_docker_clients
from upgrade.helpers.logger import logger
from upgrade.helpers.tasks import puppet_autosign_hosts
from upgrade.helpers.tasks import sync_tools_repos_to_upgrade
from upgrade.helpers.tools import version_filter

logger = logger()


def satellite6_client_setup():
    """Sets up required things on upgrade running machine and on Client to
    perform client upgrade later

    If not personal clients, then it creates docker containers as clients on
    rhevm vm.

    Environment Variable:

    DOCKER_VM
        The Docker VM IP/Hostname on rhevm to create clients
    """
    # If User Defined Clients Hostname provided
    clients6 = settings.upgrade.user_defined_client_hosts.rhel6
    clients7 = settings.upgrade.user_defined_client_hosts.rhel7
    puppet_clients6 = puppet_clients7 = None
    docker_vm = settings.upgrade.docker_vm
    clients_count = settings.upgrade.clients_count
    from_version = settings.upgrade.from_version
    sat_host = env.get('satellite_host')
    if clients6:
        clients6 = [client.strip() for client in str(clients6).split(',')]
        # Sync latest sat tools repo to clients if downstream
        if settings.repos.sattools_repo.rhel6:
            logger.info('Syncing Tools repos of rhel6 in Satellite:')
            execute(
                sync_tools_repos_to_upgrade, 'rhel6', clients6,
                settings.upgrade.client_ak.rhel6,
                host=sat_host)
    if clients7:
        clients7 = [client.strip() for client in str(clients7).split(',')]
        # Sync latest sat tools repo to clients if downstream
        if settings.repos.sattools_repo.rhel7:
            logger.info('Syncing Tools repos of rhel7 in Satellite:')
            execute(
                sync_tools_repos_to_upgrade, 'rhel7', clients7,
                settings.upgrade.client_ak.rhel7,
                host=sat_host)

    # Run upgrade on Docker Containers
    if not all([clients6, clients7]):
        if not clients_count:
            logger.warning('Clients Count is not set, please set and rerun !')
            sys.exit(1)
        elif int(clients_count) < 2:
            logger.warning('Clients Count should be atleast 2, please rerun !')
            sys.exit(1)
        time.sleep(5)
        logger.info('Generating {} clients on RHEL6 and RHEL7 on Docker. '
                    'Please wait .....'.format(clients_count))
        # Generate Clients on RHEL 7 and RHEL 6
        clients6 = execute(
            generate_satellite_docker_clients_on_rhevm,
            'rhel6',
            int(clients_count) / 2,
            host=docker_vm
        )[docker_vm]
        clients7 = execute(
            generate_satellite_docker_clients_on_rhevm,
            'rhel7',
            int(clients_count) / 2,
            host=docker_vm
        )[docker_vm]
        # Allow all puppet clients to be signed automatically
        execute(
            puppet_autosign_hosts, from_version, ['*'], host=sat_host)
        puppet_clients7 = execute(
            generate_satellite_docker_clients_on_rhevm, 'rhel7', 2,
            puppet=True,
            host=docker_vm
        )[docker_vm]
        puppet_clients6 = execute(
            generate_satellite_docker_clients_on_rhevm, 'rhel6', 2,
            puppet=True,
            host=docker_vm
        )[docker_vm]
        # Sync latest sat tools repo to clients if downstream
        if all([
            settings.repos.sattools_repo.rhel6,
            settings.repos.sattools_repo.rhel7
        ]):
            time.sleep(10)
            vers = ['6.0', '6.1']
            logger.info('Syncing Tools repos of rhel7 in Satellite..')
            if from_version in vers:
                all_clients7 = list(clients7.values()) + list(puppet_clients7.values())
                all_clients6 = list(clients6.values()) + list(puppet_clients6.values())
            else:
                all_clients7 = list(clients7.keys()) + list(puppet_clients7.keys())
                all_clients6 = list(clients6.keys()) + list(puppet_clients6.keys())
            execute(
                sync_tools_repos_to_upgrade,
                'rhel7',
                # Containers_ids are not required from sat version > 6.1 to
                # attach the subscription to client
                all_clients7,
                settings.upgrade.client_ak.rhel7,
                host=sat_host
            )
            time.sleep(10)
            logger.info('Syncing Tools repos of rhel6 in Satellite..')
            execute(
                sync_tools_repos_to_upgrade,
                'rhel6',
                # Containers_ids are not requied from sat version > 6.1 to
                # attach the subscriprion to client
                all_clients6,
                settings.upgrade.client_ak.rhel6,
                host=sat_host
            )
        # Refresh subscriptions on clients
        time.sleep(30)
        execute(
            refresh_subscriptions_on_docker_clients,
            list(clients6.values()) + list(puppet_clients6.values()),
            host=docker_vm)
        time.sleep(30)
        execute(
            refresh_subscriptions_on_docker_clients,
            list(clients7.values()) + list(puppet_clients7.values()),
            host=docker_vm)
        # Resetting autosign conf
        execute(
            puppet_autosign_hosts, from_version, [''], False, host=sat_host)
        time.sleep(400)
        logger.info("wait for all the running yum command's completions")
        for agent in puppet_clients7, puppet_clients6:
            execute(
                docker_client_missing_package_installation,
                agent,
                "puppet-agent",
                host=docker_vm
            )
        for agent in clients6, clients7:
            execute(
                docker_client_missing_package_installation,
                agent, "katello-agent",
                host=docker_vm
            )
    logger.info('Clients are ready for Upgrade.')
    return clients6, clients7, puppet_clients7, puppet_clients6


def satellite6_client_upgrade(os_version, clients, puppet=False):
    """Upgrades clients from existing version to latest version

    :param string os_version: The rhel os onto which the client is installed or
        to be installed
    :param list clients: The list of clients onto which the upgrade will be
        performed
    :param bool puppet: clients are puppet clients or not, default no
    """
    docker_vm = settings.upgrade.docker_vm
    logger.highlight(
        '\n========== {0} {1} CLIENTS UPGRADE =================\n'.format(
            os_version.upper(), 'PUPPET' if puppet else 'KATELLO'))
    old_repo = f'rhel-{settings.upgrade.os[-1]}-server-satellite-tools-' \
        f'{settings.upgrade.from_version}-rpms'
    agent = 'puppet-agent' if puppet else 'katello-agent'
    if settings.upgrade.user_defined_client_hosts.rhel6 or \
            settings.upgrade.user_defined_client_hosts.rhel7:
        user_clients_upgrade(old_repo, clients, agent)
    elif settings.upgrade.docker_vm:
        execute(
            docker_clients_upgrade,
            old_repo,
            clients,
            agent,
            host=docker_vm
        )
        # Fetching katello-agent version post upgrade from all clients
        # Giving 5 minutes for docker clients to upgrade katello-agent
        time.sleep(300)
        client_vers = execute(
            docker_clients_agent_version,
            clients,
            agent,
            host=docker_vm
        )[docker_vm]
        for hostname, version in tuple(client_vers.items()):
            logger.highlight(f'The {agent} on client {hostname} upgraded to version {version}')


def user_clients_upgrade(old_repo, clients, agent):
    """Helper function to run upgrade on user provided clients

    :param string old_repo: The old tools repo to disable before updating
        katello-agent package
    :param list clients: The list of clients onto which katello-agent package
        will be updated
    :param string agent: puppet-agent / katello-agent
    """
    for client in clients:
        execute(disable_repos, old_repo, host=client)
        execute(lambda: run(f'yum update -y {agent}'), host=client)
        post = version_filter(execute(lambda: run(f'rpm -q {agent}'), host=client)[client])
        logger.highlight(f'{agent} on {client} upgraded to {post}')


def docker_clients_upgrade(old_repo, clients, agent):
    """Helper function to run upgrade on docker containers as clients

    :param string old_repo: The old tools repo to disable before updating
        katello-agent package
    :param dict clients: The dictionary containing client_name as key and
        container_id as value
    :param string agent: puppet-agent / katello-agent
    """
    for hostname, container in tuple(clients.items()):
        logger.info(f'Upgrading client {hostname} on docker container: {container}')
        docker_execute_command(container, f'subscription-manager repos --disable {old_repo}')
        docker_execute_command(container, f'yum update -y {agent}', True)


def docker_clients_agent_version(clients, agent):
    """Determines and returns the katello or puppet agent version on docker
    clients

    :param dict clients: The dictionary containing client_name as key and
        container_id as value
    :param string agent: puppet/ puppet-agent / katello-agent
    :returns dict: The dict of docker clients hostname as key and
        its katello or puppet agent version as value
    """
    clients_dict = {}
    for hostname, container in tuple(clients.items()):
        try:
            command_output = docker_execute_command(container, f'rpm -q {agent}')
            pst = version_filter(command_output)
            clients_dict[hostname] = pst
        except Exception as ex:
            logger.warn(ex)
            clients_dict[hostname] = f"{agent} package not updated"
    return clients_dict


def docker_client_missing_package_installation(clients, agent):
    """
    Use to install the missing packages of puppet agent and katello-agent
    :param dict clients: The dictionary containing client_name as key and
        container_id as value
    :param string agent: puppet-agent / katello-agent
    """
    for hostname, container in tuple(clients.items()):
        logger.info(f'Installing client {hostname} on docker container: {container}')
        try:
            for _ in range(1, 15):
                yum_status = docker_execute_command(container, f'pgrep yum', True)
                if yum_status == '':
                    break
                logger.info("yum command is running wait fot 60 seconds...")
                time.sleep(60)
            command_output = docker_execute_command(container, f'rpm -q {agent}', True)
            if re.search(f'package {agent} is not installed', command_output):
                logger.warn(f"base version of {agent} package missed(because of timeout) on "
                            f"{container} so installing it separately")
                docker_execute_command(container, f'yum install -y {agent}', True)
                command_output = docker_execute_command(container, f'rpm -q {agent}', True)
                if re.search(f'package {agent} is not installed', command_output):
                    logger.warn(f"failed to install package {agent} on {container}")
                else:
                    logger.info(f"base version of {agent} package {command_output} installed "
                                f"successfully on {container}")
            else:
                logger.info(f"{agent} package {command_output} is available before "
                            f"upgrade on {container}")
        except Exception as ex:
            logger.warn(ex)
