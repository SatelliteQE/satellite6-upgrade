import os
import sys
import time

from automation_tools import manage_daemon
from automation_tools.repository import disable_repos
from upgrade.helpers.docker import (
    docker_execute_command,
    generate_satellite_docker_clients_on_rhevm,
    refresh_subscriptions_on_docker_clients,
)
from upgrade.helpers.logger import logger
from upgrade.helpers.rhevm4 import (
    create_rhevm4_instance,
    get_rhevm4_client,
    wait_till_rhevm4_instance_status
)
from upgrade.helpers.tasks import (
    sync_tools_repos_to_upgrade
)
from upgrade.helpers.tools import version_filter
from fabric.api import env, execute, run

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
    clients6 = os.environ.get('CLIENT6_HOSTS')
    clients7 = os.environ.get('CLIENT7_HOSTS')
    docker_vm = os.environ.get('DOCKER_VM')
    clients_count = os.environ.get('CLIENTS_COUNT')
    from_version = os.environ.get('FROM_VERSION')
    sat_host = env.get('satellite_host')
    if clients6:
        clients6 = [client.strip() for client in str(clients6).split(',')]
        # Sync latest sat tools repo to clients if downstream
        if os.environ.get('TOOLS_URL_RHEL6'):
            logger.info('Syncing Tools repos of rhel6 in Satellite:')
            execute(
                sync_tools_repos_to_upgrade, 'rhel6', clients6, host=sat_host)
    if clients7:
        clients7 = [client.strip() for client in str(clients7).split(',')]
        # Sync latest sat tools repo to clients if downstream
        if os.environ.get('TOOLS_URL_RHEL7'):
            logger.info('Syncing Tools repos of rhel7 in Satellite:')
            execute(
                sync_tools_repos_to_upgrade, 'rhel7', clients7, host=sat_host)
    # Run upgrade on Docker Containers
    if not all([clients6, clients7]):
        if not clients_count:
            logger.warning('Clients Count is not set, please set and rerun !')
            sys.exit(1)
        elif int(clients_count) < 2:
            logger.warning('Clients Count should be atleast 2, please rerun !')
            sys.exit(1)
        # Check if the VM containing docker images is up, else turn on
        with get_rhevm4_client().build() as rhevm_client:
            instance_name = 'sat6-docker-upgrade'
            template_name = 'sat6-docker-upgrade-template'
            vm = rhevm_client.system_service().vms_service(
                ).list(search='name={}'.format(instance_name))
            if not vm:
                logger.info(
                    'Docker VM for generating Content Host is not created. '
                    'Creating it, please wait..')
                create_rhevm4_instance(instance_name, template_name)
                execute(manage_daemon, 'restart', 'docker', host=docker_vm)
            elif vm[0].status.name.lower() == 'down':
                logger.info('Docker VM for generating Content Host is not up. '
                            'Turning on, please wait ....')
                rhevm_client.vms.get(name=instance_name).start()
                wait_till_rhevm4_instance_status(instance_name, 'up', 5)
                execute(manage_daemon, 'restart', 'docker', host=docker_vm)
        time.sleep(5)
        logger.info('Generating {} clients on RHEL6 and RHEL7 on Docker. '
                    'Please wait .....'.format(clients_count))
        # Generate Clients on RHEL 7 and RHEL 6
        clients6 = execute(
            generate_satellite_docker_clients_on_rhevm,
            'rhel6',
            int(clients_count)/2,
            host=docker_vm
        )[docker_vm]['katello']
        clients7 = execute(
            generate_satellite_docker_clients_on_rhevm,
            'rhel7',
            int(clients_count)/2,
            host=docker_vm
        )[docker_vm]['katello']
        # Allow all puppet clients to be signed automatically
        execute(
            lambda: run('echo "*" > /etc/puppetlabs/puppet/autosign.conf'),
            host=sat_host)
        puppet_clients7 = execute(
            generate_satellite_docker_clients_on_rhevm, 'rhel7', 2,
            puppet=True,
            host=docker_vm
        )[docker_vm]['puppet']
        # Sync latest sat tools repo to clients if downstream
        if all([
            os.environ.get('TOOLS_URL_RHEL6'),
            os.environ.get('TOOLS_URL_RHEL7')
        ]):
            time.sleep(10)
            vers = ['6.0', '6.1']
            logger.info('Syncing Tools repos of rhel7 in Satellite..')
            if from_version in vers:
                all_clients7 = clients7.values() + puppet_clients7.values()
            else:
                all_clients7 = clients7.keys() + puppet_clients7.keys()
            execute(
                sync_tools_repos_to_upgrade,
                'rhel7',
                # Containers_ids are not required from sat version > 6.1 to
                # attach the subscription to client
                all_clients7,
                host=sat_host
            )
            time.sleep(10)
            logger.info('Syncing Tools repos of rhel6 in Satellite..')
            execute(
                sync_tools_repos_to_upgrade,
                'rhel6',
                # Containers_ids are not requied from sat version > 6.1 to
                # attach the subscriprion to client
                clients6.values() if from_version in vers else clients6.keys(),
                host=sat_host
            )
        # Refresh subscriptions on clients
        time.sleep(30)
        execute(
            refresh_subscriptions_on_docker_clients,
            clients6.values(),
            host=docker_vm)
        time.sleep(30)
        execute(
            refresh_subscriptions_on_docker_clients,
            clients7.values() + puppet_clients7.values(),
            host=docker_vm)
        # Resetting autosign conf
        execute(
            lambda: run('echo "" > /etc/puppetlabs/puppet/autosign.conf'),
            host=sat_host)
    logger.info('Clients are ready for Upgrade.')
    return clients6, clients7, puppet_clients7


def satellite6_client_upgrade(os_version, clients, puppet=False):
    """Upgrades clients from existing version to latest version

    :param string os_version: The rhel os onto which the client is installed or
        to be installed
    :param list clients: The list of clients onto which the upgrade will be
        performed
    :param bool puppet: clients are puppet clients or not, default no
    """
    logger.highlight(
        '\n========== {0} {1} CLIENTS UPGRADE =================\n'.format(
            os_version.upper(), 'puppet' if puppet else 'katello'))
    old_version = os.environ.get('FROM_VERSION')
    docker_vm = os.environ.get('DOCKER_VM')
    rhel_ver = os_version[-1]
    old_repo = 'rhel-{0}-server-satellite-tools-{1}-rpms'.format(
        rhel_ver, old_version)
    if os.environ.get('CLIENT6_HOSTS') or os.environ.get('CLIENT7_HOSTS'):
        user_clients_upgrade(old_repo, clients, puppet)
    elif os.environ.get('DOCKER_VM'):
        execute(
            docker_clients_upgrade,
            old_repo,
            clients,
            puppet,
            host=docker_vm
        )
        # Fetching katello-agent version post upgrade from all clients
        # Giving 5 minutes for docker clients to upgrade katello-agent
        time.sleep(300)
        client_vers = execute(
            docker_clients_agent_version,
            clients,
            puppet,
            host=docker_vm
        )[docker_vm]
        for hostname, version in client_vers.items():
            logger.highlight(
                'The {0}-agent on client {1} upgraded '
                'to version {2}'.format(
                    'puppet' if puppet else 'katello', hostname, version))


def user_clients_upgrade(old_repo, clients, puppet=False):
    """Helper function to run upgrade on user provided clients

    :param string old_repo: The old tools repo to disable before updating
        katello-agent package
    :param list clients: The list of clients onto which katello-agent package
        will be updated
    :param bool puppet: clients are puppet clients or not, default no
    """
    for client in clients:
        execute(disable_repos, old_repo, host=client)
        agent = 'puppet' if puppet else 'katello'
        execute(
            lambda: run('yum update -y {}-agent'.format(agent)), host=client)
        post = version_filter(execute(
            lambda: run('rpm -q {}-agent'.format(agent)), host=client)[client])
        logger.highlight(
            '{0}-agent on {1} upgraded to {2}'.format(agent, client, post))


def docker_clients_upgrade(old_repo, clients, puppet=False):
    """Helper function to run upgrade on docker containers as clients

    :param string old_repo: The old tools repo to disable before updating
        katello-agent package
    :param dict clients: The dictionary containing client_name as key and
        container_id as value
    :param bool puppet: clients are puppet clients or not, default no
    """
    agent = 'puppet' if puppet else 'katello'
    for hostname, container in clients.items():
        logger.info('Upgrading client {0} on docker container: {1}'.format(
            hostname, container))
        docker_execute_command(
            container, 'subscription-manager repos --disable {}'.format(
                old_repo))
        docker_execute_command(
            container, 'yum update -y {}-agent'.format(agent), True)


def docker_clients_agent_version(clients, puppet=False):
    """Determines and returns the katello or puppet agent version on docker
    clients

    :param dict clients: The dictionary containing client_name as key and
        container_id as value
    :returns dict: The dict of docker clients hostname as key and
        its katello or puppet agent version as value
    :param bool puppet: get puppet agent version if true
    """
    clients_dict = {}
    agent = 'puppet' if puppet else 'katello'
    for hostname, container in clients.items():
        pst = version_filter(
            docker_execute_command(container, 'rpm -q {}-agent'.format(agent)))
        clients_dict[hostname] = pst
    return clients_dict
