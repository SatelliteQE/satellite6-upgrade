"""All the helper functions, needed for scenarios test case automation to be
added here"""
import json
import os
import time

from automation_tools.satellite6 import hammer
from fabric.api import execute
from fabric.api import run

from upgrade.helpers import settings
from upgrade.helpers.docker import generate_satellite_docker_clients
from upgrade.helpers.logger import logger

rpm1 = 'https://inecas.fedorapeople.org/fakerepos/zoo3/bear-4.1-1.noarch.rpm'
rpm2 = 'https://inecas.fedorapeople.org/fakerepos/zoo3/camel-0.1-1.noarch.rpm'

logger = logger()


def create_dict(entities_dict):
    """Stores a global dictionary of entities created in satellite by the
    scenarios tested, so that these entities can be retrieved post upgrade
    to assert the test cases.

    :param dict entities_dict: A dictionary of entities created in
        satellite
    """
    if os.path.exists('scenario_entities'):
        with open('scenario_entities') as entities_data:
            data = json.load(entities_data)
        data.update(entities_dict)
        with open('scenario_entities', 'w') as entities_data:
            json.dump(data, entities_data)
    else:
        with open('scenario_entities', 'w') as entities_data:
            json.dump(entities_dict, entities_data)


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
    ak_name = settings.upgrade.client_ak[settings.upgrade.os]
    docker_vm = settings.upgrade.docker_vm
    logger.info('Generating katello client on RHEL7 on Docker. Please wait .....')
    # Generate Clients on RHEL 7
    time.sleep(40)
    clients = execute(
        generate_satellite_docker_clients,
        distro,
        1,
        ak_name,
        org_label,
        host=docker_vm,
    )[docker_vm]
    return clients


def upload_manifest(manifest_url, org_name):
    """ Upload manifest to satellite

    :param manifest_url: URL of manifest hosted over http
    :param org_name: Organization name in satellite

    Usage:
        upload_manifest(self.manifest_url, self.org_name)
    """
    # Sets hammer default configuration
    hammer.set_hammer_config()
    run('wget {0} -O {1}'.format(manifest_url, '/manifest.zip'))
    print(hammer.hammer(
        f'subscription upload --file "/manifest.zip" --organization {org_name}'
    ))


def delete_manifest(org_name):
    """ Delete manifest from satellite

    :param org_name: Organization name in satellite

    Usage:
        delete_manifest(self.org_name)
    """
    # Sets hammer default configuration
    hammer.set_hammer_config()
    print(hammer.hammer(
        f'subscription delete-manifest --organization {org_name}'
    ))
