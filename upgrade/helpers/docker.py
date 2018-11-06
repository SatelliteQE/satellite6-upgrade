import os
import sys
import time
from automation_tools.bz import bz_bug_is_open
from fauxfactory import gen_string
from upgrade.helpers.logger import logger
from fabric.api import run

logger = logger()


def generate_satellite_docker_clients_on_rhevm(
        client_os,
        clients_count,
        custom_ak=None,
        org_label=None,
        puppet=False):
    """Generates satellite katello or puppet clients on docker as containers

    :param string client_os: Client OS of which client to be generated
        e.g: rhel6, rhel7
    :param string clients_count: No of clients to generate
    :param string custom_ak: Activation key name, to register clients
    :param string org_label: The organization in which the docker clients to
        created and where the custom ak is available
    :param bool puppet: Genearates puppet clients only if true
    :return dict: Returns the dictionary of katello or puppet clients
        By default katello clients will be created

    Environment Variables:

    RHEV_SAT_HOST
        The satellite hostname for which clients to be generated and
        registered
    RHEV_CLIENT_AK
        The AK using which client will be registered to satellite
    """
    if int(clients_count) == 0:
        logger.warning(
            'Clients count to generate on Docker should be atleast 1 !')
        sys.exit(1)
    satellite_hostname = os.environ.get('RHEV_SAT_HOST')
    ak = custom_ak or os.environ.get(
        'RHEV_CLIENT_AK_{}'.format(client_os.upper()))
    result = {}
    puppet = bool(puppet)
    if not puppet:
        host_title = 'scenariokatelloclient{0}'.format(
            gen_string('alpha')) if custom_ak else 'dockerkatelloclient'
        image = 'upgrade:{}'
    else:
        host_title = 'scenariopuppetclient{0}'.format(
            gen_string('alpha')) if custom_ak else 'dockerpuppetclient'
        image = 'upgrade:puppet-{}'
    for count in range(int(clients_count)):
        if bz_bug_is_open('1405085'):
            time.sleep(5)
        # If custom activation key is passed, it will be used to create custom
        # docker clients for scenario tests and we will require to set distinct
        # hostname for those content hosts
        hostname = '{0}{1}{2}'.format(count, host_title, client_os)
        if org_label:
            create_command = 'docker run -d -h {0} -v /dev/log:/dev/log ' \
                '-e "SATHOST={1}" -e "AK={2}" -e "ORG={3}" {4}'.format(
                    hostname, satellite_hostname, ak, org_label,
                    image.format(client_os))
        else:
            create_command = 'docker run -d -h {0} -v /dev/log:/dev/log ' \
                '-e "SATHOST={1}" -e "AK={2}" {3}'.format(
                    hostname, satellite_hostname, ak, image.format(client_os))
        container_id = run(create_command)
        result[hostname] = container_id
    return result


def attach_subscription_to_host_from_content_host(
        subscription_id, dockered_host=False, container_id=None):
    """Attaches product subscription to content host from host itself

    :param string subscription_id: The product uuid/pool_id of which the
    subscription to be attached to content host
    """
    attach_command = 'subscription-manager attach --pool={0}'.format(
        subscription_id)
    if not dockered_host:
        run(attach_command)
    else:
        docker_execute_command(container_id, attach_command)


def refresh_subscriptions_on_docker_clients(container_ids):
    """Refreshes subscription on docker containers which are satellite clients

    :param list container_ids: The list of container ids onto which
    subscriptions will be refreshed
    """
    if isinstance(container_ids, list):
        for container_id in container_ids:
            docker_execute_command(
                container_id, 'subscription-manager refresh')
            docker_execute_command(container_id, 'yum clean all', quiet=True)
    else:
        docker_execute_command(container_ids, 'subscription-manager refresh')
        docker_execute_command(container_ids, 'yum clean all', quiet=True)


def docker_execute_command(container_id, command, quiet=True, **kwargs):
    """Executes command on running docker container

    :param string container_id: Running containers id to execute command
    :param string command: Command to run on running container
    :param bool quiet: To run command in quiet mode on container
    :param bool async: To run command in background mode on container

    :returns command output if async is False
    """
    if not isinstance(quiet, bool):
        raise TypeError(
            'quiet parameter value should be boolean type. '
            '{} type provided.'.format(type(quiet))
        )
    if 'async' in kwargs and not isinstance(kwargs['async'], bool):
        raise TypeError(
            'async parameter value should be boolean type. '
            '{} type provided.'.format(type(kwargs['async']))
        )
    return run(
        'docker exec {0} {1} {2}'.format(
            '-d' if kwargs.get('async') else '', container_id, command),
        quiet=quiet
        )


def docker_cleanup_containers():
    logger.info('Cleaning UP of Docker containers BEGINS')
    logger.info('Stopping all the running docker containers')
    run('docker ps -a | grep \'days ago\' | awk \'{print $1}\' | xargs '
        '--no-run-if-empty docker stop')
    logger.info('Removing all the docker containers')
    run('docker ps -a | grep \'days ago\' | awk \'{print $1}\' | xargs '
        '--no-run-if-empty docker rm ')
    logger.info('Cleaning UP of Docker containers ENDS')


def docker_wait_until_repo_list(container_id, timeout=5):
    """Waits until the ak is attached and repo's are listed

    :param string container_id: ID of the docker container
    :param int timeout: The polling timeout in minutes.
    """
    timeup = time.time() + int(timeout) * 60
    while True:
        result = docker_execute_command(
            container_id,
            'yum repolist | grep repolist',
            quiet=True
        )
        if result.startswith('repolist'):
            result = int(result.splitlines()[0].split(':')[1].strip())
        if time.time() > timeup:
            logger.warning('There are no repos on {0} or timeup of {1} mins '
                           'has occured'.format(container_id, timeout))
            return False
        if result > 0:
            return True
        else:
            time.sleep(5)
