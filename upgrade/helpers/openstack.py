import novaclient
import os
import sys
import time

from fabric.api import env, execute, run
from novaclient.client import Client
from upgrade.helpers.logger import logger
from upgrade.helpers.tools import get_hostname_from_ip, host_pings

logger = logger()


def get_openstack_client():
    """Creates client object instance from openstack novaclient API.
    And returns the client object for further use.

    The following environment variables affect this command:

    USERNAME
        The username of an openstack project to login.
    PASSWORD
        The password of an openstack project to login.
    AUTH_URL
        The authentication url of the project.
    PROJECT_ID
        Project ID of an openstack project.

    """
    username = os.environ.get('USERNAME')
    if username is None:
        logger.warning('The USERNAME environment variable should be defined')
    password = os.environ.get('PASSWORD')
    if password is None:
        logger.warning('The PASSWORD environment variable should be defined')
    auth_url = os.environ.get('AUTH_URL')
    if auth_url is None:
        logger.warning('The AUTH_URL environment variable should be defined')
    project_id = os.environ.get('PROJECT_ID')
    if project_id is None:
        logger.warning('The PROJECT_ID environment variable should be defined')
    with Client(
        version=2,
        username=username,
        api_key=password,
        auth_url=auth_url,
        project_id=project_id
    ) as openstack_client:
        openstack_client.authenticate()
        return openstack_client


def create_openstack_instance(
        product, instance_name, image_name, flavor_name, ssh_key, timeout=5):
    """Creates openstack Instance from Image and Assigns a floating IP
    to instance. Also It ensures that instance is ready for testing.

    :param product: A string. A product name of which, instance to create.
    :param instance_name: A string. Openstack Instance name to create.
    :param image_name: A string. Openstack image name from which instance
        to be created.
    :param flavor_name: A string. Openstack flavor_name for instance.
        e.g m1.small.
    :param ssh_key: A string. ssh_key 'name' that required to add
        into this instance.
    :param int timeout: The polling timeout in minutes to assign IP.

    ssh_key should be added to openstack project before running automation.
    Else the automation will fail.

    The following environment variables affect this command:

    USERNAME
        The username of an openstack project to login.
    PASSWORD
        The password of an openstack project to login.
    AUTH_URL
        The authentication url of the project.
    PROJECT_ID
        Project ID of an openstack project.

    """
    network_name = 'satellite-jenkins'
    openstack_client = get_openstack_client()
    # Validate ssh_key is added into openstack project
    openstack_client.keypairs.find(name=ssh_key)
    image = openstack_client.images.find(name=image_name)
    flavor = openstack_client.flavors.find(name=flavor_name)
    network = openstack_client.networks.find(label=network_name)
    floating_ip = openstack_client.floating_ips.create(
        openstack_client.floating_ip_pools.list()[0].name
    )
    # Create instance from the given parameters
    logger.info('Creating new Openstack instance {0}'.format(instance_name))
    instance = openstack_client.servers.create(
        name=instance_name,
        image=image.id,
        flavor=flavor.id,
        key_name=ssh_key,
        network=network.id
    )
    # Assigning floating ip to instance
    timeup = time.time() + int(timeout) * 60
    while True:
        if time.time() > timeup:
            logger.warning(
                'The timeout for assigning the floating IP has reached!')
            sys.exit(1)
        try:
            instance.add_floating_ip(floating_ip)
            logger.info('SUCCESS!! The floating IP {0} has been assigned '
                        'to instance!'.format(floating_ip.ip))
            break
        except novaclient.exceptions.BadRequest:
            time.sleep(5)
    # Wait till DNS resolves the IP
    logger.info('Pinging the Host by IP:{0} ..........'.format(floating_ip.ip))
    host_pings(str(floating_ip.ip))
    logger.info('SUCCESS !! The given IP has been pinged!!\n')
    logger.info('Now, Getting the hostname from IP......\n')
    hostname = get_hostname_from_ip(str(floating_ip.ip))
    if not hostname:
        sys.exit(1)
    env['{0}_host'.format(product)] = hostname
    logger.info('Pinging the Hostname:{0} ..........'.format(hostname))
    host_pings(hostname)
    logger.info('SUCCESS !! The obtained hostname from IP is pinged !!')
    # Update the /etc/hosts file
    execute(lambda: run("echo {0} {1} >> /etc/hosts".format(
        floating_ip.ip, hostname)), host=hostname)


def delete_openstack_instance(instance_name):
    """Deletes openstack Instance.

    :param instance_name: A string. Openstack instance name to delete.

    The following environment variables affect this command:

    USERNAME
        The username of an openstack project to login.
    PASSWORD
        The password of an openstack project to login.
    AUTH_URL
        The authentication url of the project.
    PROJECT_ID
        Project ID of an openstack project.

    """
    openstack_client = get_openstack_client()
    try:
        instance = openstack_client.servers.find(name=instance_name)
    except novaclient.exceptions.NotFound:
        logger.error('Instance {0} not found in Openstack project.'.format(
            instance_name
        ))
        return
    instance.delete()
    logger.info('Success! The instance {0} has been deleted from '
                'Openstack.'.format(instance_name))
