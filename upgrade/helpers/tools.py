"""A set of common tasks for automating interactions with Satellite & Capsule.

Many commands are affected by environment variables. Unless stated otherwise,
all environment variables are required.
"""
import json
import re
import subprocess
import time

from nailgun import entity_mixins
from fabric.api import execute, run
from upgrade.helpers.logger import logger

logger = logger()


def reboot(halt_time=300):
    """Reboots the host.

    Also halts the execution until reboots according to given time.

    :param int halt_time: Halt execution in seconds.
    """
    halt_time = halt_time
    logger.info('Rebooting the host, please wait .... ')
    try:
        run('reboot', warn_only=True)
    except Exception as e:
        logger.info(e)
    time.sleep(halt_time)


def copy_ssh_key(from_host, to_hosts):
    """This will generate(if not already) ssh-key on from_host
    and copy that ssh-key to to_hosts.

    Beware that to and from hosts should have authorized key added
    for test-running host.

    :param string from_host: Hostname on which the key to be generated and
        to be copied from.
    :param list to_hosts: Hostnames on to which the ssh-key will be copied.

    """
    execute(lambda: run('mkdir -p ~/.ssh'), host=from_host)
    # do we have privkey? generate only pubkey
    execute(lambda: run(
        '[ ! -f ~/.ssh/id_rsa ] || '
        'ssh-keygen -y -f ~/.ssh/id_rsa > ~/.ssh/id_rsa.pub'), host=from_host)
    # dont we have still pubkey? generate keypair
    execute(lambda: run(
        '[ -f ~/.ssh/id_rsa.pub ] || '
        'ssh-keygen -f ~/.ssh/id_rsa -t rsa -N \'\''), host=from_host)
    # read pubkey content in sanitized way
    pub_key = execute(lambda: run(
        '[ ! -f ~/.ssh/id_rsa.pub ] || cat ~/.ssh/id_rsa.pub'),
        host=from_host)[from_host]
    if pub_key:
        for to_host in to_hosts:
            execute(lambda: run('mkdir -p ~/.ssh'), host=to_host)
            # deploy pubkey to another host
            execute(lambda: run(
                'echo "{0}" >> ~/.ssh/authorized_keys'.format(pub_key)
            ), host=to_host)


def host_pings(host, timeout=15, ip_addr=False):
    """This ensures the given IP/hostname pings succesfully.

    :param host: A string. The IP or hostname of host.
    :param int timeout: The polling timeout in minutes.
    :param Boolean ip_addr: To return the ip address of the host

    """
    timeup = time.time() + int(timeout) * 60
    while True:
        command = subprocess.Popen(
            'ping -c1 {0}; echo $?'.format(host),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=True
        )
        output = command.communicate()[0].decode()
        # Checking the return code of ping is 0
        if time.time() > timeup:
            logger.warning('The timeout for pinging the host {0} has '
                           'reached!'.format(host))
            return False
        if int(output.split()[-1]) == 0:
            if ip_addr:
                ip = output[output.find("(") + 1:output.find(")")]
                return True, ip
            return True
        else:
            time.sleep(5)


def host_ssh_availability_check(host, timeout=7):
    """This ensures the given host has ssh up and running.

    :param host: A string. The IP or hostname of host.
    :param int timeout: The polling timeout in minutes.

    """
    _, ip = host_pings(host, timeout=timeout, ip_addr=True)
    timeup = time.time() + int(timeout) * 60
    while True:
        command = subprocess.Popen(
            'nc -vn {0} 22 <<< \'\''.format(ip),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=True
        )
        output = command.communicate()[1].decode()
        print(output)
        # Checking the return code of ping is 0
        if time.time() > timeup:
            logger.warning('SSH timed out for host {0} '.format(host))
            return False
        if output.__contains__('seconds'):
            return True
        else:
            time.sleep(5)


def disable_old_repos(repo_name, timeout=1):
    """This ensures that the repo is disable and the command doesn't timeout

    :param repo_name: Repo ID of the repo to be disable
    :param int timeout: The polling timeout in minutes.
    """
    timeup = time.time() + int(timeout) * 60
    while True:
        run('subscription-manager refresh')
        repos = run('subscription-manager repos --list | grep \'Repo ID\'')
        if time.time() > timeup:
            logger.warning('There is no {0} repo to disable'.format(repo_name))
            return False
        if repos.__contains__(repo_name):
            run('subscription-manager repos --disable {0}'.format(repo_name))
            return True
        else:
            time.sleep(5)


def get_hostname_from_ip(ip, timeout=3):
    """Retrives the hostname by logging into remote machine by IP.
    Specially for the systems who doesnt support reverse DNS.
    e.g usersys machines.

    :param ip: A string. The IP address of the remote host.
    :param int timeout: The polling timeout in minutes.

    """
    timeup = time.time() + int(timeout) * 60
    while True:
        if time.time() > timeup:
            logger.warning(
                'The timeout for getting the Hostname from IP has reached!')
            return False
        try:
            output = execute(lambda: run('hostname'), host=ip)
            logger.info('Hostname determined as: {0}'.format(output[ip]))
            break
        except Exception as e:
            logger.info('Fetching hostname from ip {0} is '
                        'failed due to: {1}'.format(ip, e))
            time.sleep(5)
    return output[ip]


def version_filter(rpm_name):
    """Helper function to filter the katello-agent version from katello-agent
    rpm name

    :param string rpm_name: The katello-agent rpm name
    """
    return re.search(r'\d(\-\d|\.\d)*', rpm_name).group()


def _extract_sat_cap_version(command):
    """Extracts Satellite and Capsule version

    :param string command: The command to run on Satellite and Capsule that
    returns installed version
    :return string: Satellite/Capsule version
    """
    if command:
        cmd_result = run(command, quiet=True)
        version_re = (
            r'[^\d]*(?P<version>\d(\.\d\.*\d*){1})'
        )
        result = re.search(version_re, cmd_result)
        if result:
            version = result.group('version')
            return version, cmd_result
    return None, cmd_result


def get_sat_cap_version(product):
    """Determines and returns the installed Satellite/Capsule version on system

    :param string product: The product name as satellite/capsule
    :return string: Satellite/Capsule version
    """
    if 'sat' in product.lower():
        _6_2_VERSION_COMMAND = 'rpm -q satellite'
        _LT_6_2_VERSION_COMMAND = (
            'grep "VERSION" /usr/share/foreman/lib/satellite/version.rb'
        )
    if 'cap' in product.lower():
        _6_2_VERSION_COMMAND = 'rpm -q satellite-capsule'
        _LT_6_2_VERSION_COMMAND = 'None'
    results = (
        _extract_sat_cap_version(cmd) for cmd in
        (_6_2_VERSION_COMMAND, _LT_6_2_VERSION_COMMAND)
    )
    for version, cmd_result in results:
        if version:
            return version
    logger.warning('Unable to detect installed version due to:\n{}'.format(
        cmd_result
    ))


def create_setup_dict(setups_dict):
    """Creates a file to save the return values from setup_products_for_upgrade
     task

    :param dict setups_dict: Dictionary of all return value of
    setup_products_for_upgrade
    """
    with open('product_setup', 'w') as pref:
        json.dump(setups_dict, pref)


def get_setup_data():
    """Open's the file to return the values from
    setup_products_for_upgrade to product_upgrade task
    task

    :returns dict: The dict of all the returns values of
    setup_products_for_upgrade that were saved in the product_setup file
    """
    with open('product_setup', 'r') as pref:
        data = json.load(pref)
    return data


def call_entity_method_with_timeout(entity_callable, timeout=300, **kwargs):
    """Call Entity callable with a custom timeout

    :param entity_callable, the entity method object to call
    :param timeout: the time to wait for the method call to finish
    :param kwargs: the kwargs to pass to the entity callable

    Usage:
        call_entity_method_with_timeout(
            entities.Repository(id=repo_id).sync, timeout=1500)
    """
    original_task_timeout = entity_mixins.TASK_TIMEOUT
    entity_mixins.TASK_TIMEOUT = timeout
    try:
        entity_callable(**kwargs)
    finally:
        entity_mixins.TASK_TIMEOUT = original_task_timeout
