"""All the helper functions, needed for scenarios test case automation to be
added here"""
import os
import json
import time

from automation_tools import manage_daemon
from upgrade.helpers.docker import generate_satellite_docker_clients_on_rhevm
from upgrade.helpers.rhevm import (
    create_rhevm_instance,
    get_rhevm_client,
    wait_till_rhevm_instance_status
)
from upgrade.helpers.logger import logger
from fabric.api import execute

rpm1 = 'https://inecas.fedorapeople.org/fakerepos/zoo3/bear-4.1-1.noarch.rpm'
rpm2 = 'https://inecas.fedorapeople.org/fakerepos/zoo3/camel-0.1-1.noarch.rpm'
data = {}

logger = logger()


def create_dict(entities_dict):
    """Stores a global dictionary of entities created in satellite by the
    scenarios tested, so that these entities can be retrieved post upgrade
    to assert the test cases.

    :param string entities_dict: A dictionary of entities created in
        satellite
    """
    data.update(entities_dict)
    with open('scenario_entities', 'wb') as pref:
        json.dump(data, pref)


def get_entity_data(scenario_name):
    """Fetches the dictionary of entities from the disk depending on the
    Scenario name (class name in which test is defined)

    :param string scenario_name : The name of the class for which the data is
        to fetched
    :returns dict entity_data : Returns a dictionary of entities
    """
    with open('scenario_entities') as pref:
        entity_data = json.load(pref)
        entity_data = entity_data[scenario_name]
    return entity_data


def dockerize(ak_name=None, distro=None, org_label=None):
    """Creates Docker Container's of specified distro and subscribes them to
    given AK

    :param string ak_name : Activation Key name, to be used to subscribe
    the docker container's
    :param string distro : The OS of the VM to be created.
        Supported are 'rhel7' and 'rhel6'
    :returns dict clients : A dictonary which contain's container name
    and id.

    Environment Variable:

    DOCKER_VM
        The Docker VM IP/Hostname on rhevm to create clients
    RHEV_CLIENT_AK
        The AK using which client will be registered to satellite
    """
    ak_name = ak_name or os.environ.get(
        'RHEV_CLIENT_AK_{}'.format(distro.upper()))
    docker_vm = os.environ.get('DOCKER_VM')
    # Check if the VM containing docker images is up, else turn on
    rhevm_client = get_rhevm_client()
    instance_name = 'sat6-docker-upgrade'
    template_name = 'sat6-docker-upgrade-template'
    vm = rhevm_client.vms.get(name=instance_name)
    if not vm:
        logger.info('Docker VM for generating Content Host is not created.'
                    'Creating it, please wait..')
        create_rhevm_instance(instance_name, template_name)
        execute(manage_daemon, 'restart', 'docker', host=docker_vm)
    elif vm.get_status().get_state() == 'down':
        logger.info('Docker VM for generating Content Host is not up. '
                    'Turning on, please wait ....')
        rhevm_client.vms.get(name=instance_name).start()
        wait_till_rhevm_instance_status(instance_name, 'up', 5)
        execute(manage_daemon, 'restart', 'docker', host=docker_vm)
    rhevm_client.disconnect()
    time.sleep(5)
    logger.info('Generating client on RHEL7 on Docker. '
                'Please wait .....')
    # Generate Clients on RHEL 7
    time.sleep(30)
    clients = execute(
        generate_satellite_docker_clients_on_rhevm,
        distro,
        1,
        ak_name,
        org_label,
        host=docker_vm,
    )[docker_vm]
    return clients


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
