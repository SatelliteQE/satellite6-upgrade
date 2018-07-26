"""All the helper functions, needed for scenarios test case automation to be
added here"""
import os
import json
import time

from automation_tools import manage_daemon
from automation_tools.satellite6 import hammer
from fabric.api import run
from nailgun import entity_mixins
from upgrade.helpers.docker import generate_satellite_docker_clients_on_rhevm
from upgrade.helpers.rhevm4 import (
    create_rhevm4_instance,
    get_rhevm4_client,
    wait_till_rhevm4_instance_status
)
from upgrade.helpers.logger import logger
from fabric.api import execute

rpm1 = 'https://inecas.fedorapeople.org/fakerepos/zoo3/bear-4.1-1.noarch.rpm'
rpm2 = 'https://inecas.fedorapeople.org/fakerepos/zoo3/camel-0.1-1.noarch.rpm'

logger = logger()


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
    ak_name = ak_name or os.environ.get(
        'RHEV_CLIENT_AK_{}'.format(distro.upper()))
    docker_vm = os.environ.get('DOCKER_VM')
    # Check if the VM containing docker images is up, else turn on
    with get_rhevm4_client().build() as rhevm_client:
        instance_name = 'sat6-docker-upgrade'
        template_name = 'sat6-docker-upgrade-template'
        vm = rhevm_client.system_service().vms_service(
            ).list(search='name={}'.format(instance_name))
        if not vm:
            logger.info('Docker VM for generating Content Host is not created.'
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
    logger.info('Generating katello client on RHEL7 on Docker. '
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
    print hammer.hammer('subscription upload --file {0} '
                        '--organization {1}'.format('/manifest.zip',
                                                    org_name))


def delete_manifest(org_name):
    """ Delete manifest from satellite

    :param org_name: Organization name in satellite

    Usage:
        delete_manifest(self.org_name)
    """
    # Sets hammer default configuration
    hammer.set_hammer_config()
    print hammer.hammer(
        'subscription delete-manifest '
        '--organization "{0}"'.format(org_name)
    )
