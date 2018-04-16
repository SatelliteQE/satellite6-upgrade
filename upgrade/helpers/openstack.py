
import os
import shade
import sys
import yaml

from fabric.api import env, execute, run
from upgrade.helpers.logger import logger
from upgrade.helpers.tasks import get_osp_hostname
from upgrade.helpers.tools import host_pings, host_ssh_availability_check

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
    PROJECT_NAME
        Project NAME of an openstack project.

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
    project_name = os.environ.get('PROJECT_NAME')
    if project_name is None:
        logger.warning('The PROJECT_NAME environment variable should '
                       'be defined')
    data = {
        'clouds':
            {
                'satellite-jenkins':
                    {
                        'auth':
                            {
                                'username': username,
                                'password': password,
                                'project_name': project_name,
                                'auth_url': auth_url
                            }
                    }
            }
    }
    with open('clouds.yml', 'w') as outfile:
        yaml.dump(data, outfile, default_flow_style=False)
    openstack_client = shade.openstack_cloud(cloud='satellite-jenkins')
    return openstack_client


def create_openstack_instance(instance_name, image_name, volume_size,
                              flavor_name=None, ssh_key=None,
                              network_name=None):
    """Creates openstack Instance from Image and Assigns a floating IP
    to instance. Also It ensures that instance is ready for testing.

    :param instance_name: A string. Openstack Instance name to create.
    :param image_name: A string. Openstack image name from which instance
        to be created.
    :param volume_size: A string. Volume size to be created for osp instance
    :param flavor_name: A string. Openstack flavor_name for instance.
        e.g m1.small.
    :param ssh_key: A string. ssh_key 'name' that required to add
        into this instance.
    :param network_name: A string. Network 'name' that required to create
        this instance.

    ssh_key should be added to openstack project before running automation.
    Else the automation will fail.

    The following environment variables affect this command:

    FLAVOR_NAME
        Openstack flavor name to create compute settings for instance
    NETWORK_NAME
        Name of the network where the instance is created
    SSH_KEY
        ssh key to be added into the instance from openstack
    """
    env.user = 'root'
    env.disable_known_hosts = True
    if flavor_name is None:
        flavor_name = flavor_name or os.environ.get('FLAVOR_NAME')
    if network_name is None:
        network_name = network_name or os.environ.get('NETWORK_NAME')
    if ssh_key is None:
        ssh_key = ssh_key or os.environ.get('OSP_SSHKEY')
    openstack_client = shade.openstack_cloud(cloud='satellite-jenkins')
    # Validate image is added into openstack project
    image = openstack_client.get_image(image_name)
    # Create instance from the given parameters
    logger.info('Creating new Openstack instance {0}'.format(instance_name))
    instance = openstack_client.create_server(
        name=instance_name,
        image=image.id,
        flavor=flavor_name,
        boot_from_volume=True,
        key_name=ssh_key,
        network=network_name,
        volume_size=volume_size,
        terminate_volume=True,
        wait=True
    )
    if instance.interface_ip:
        ip_addr = instance.interface_ip
    else:
        logger.error("No floating Ip assigned")

    # Wait till DNS resolves the IP
    logger.info('Pinging the Host by IP:{0} ..........'.format(ip_addr))
    host_ssh_availability_check(ip_addr)
    host_pings(str(ip_addr))
    logger.info('SUCCESS !! The given IP has been pinged!!\n')
    logger.info('Now, Getting the hostname from IP......\n')
    hostname = get_osp_hostname(ip_addr)
    if not hostname:
        sys.exit(1)
    logger.info('Pinging the Hostname:{0} ..........'.format(hostname))
    host_pings(hostname)
    logger.info('SUCCESS !! The obtained hostname from IP is pinged !!')
    # Update the /etc/hosts file
    execute(lambda: run("hostnamectl set-hostname {0}".format(
        hostname)), host=hostname)
    execute(lambda: run("echo {0} {1} >> /etc/hosts".format(
        ip_addr, hostname)), host=hostname)
    with open('/tmp/instance.info', 'w') as outfile:
        outfile.write('OSP_HOSTNAME={0}'.format(hostname))


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
    PROJECT_NAME
        Project NAME of an openstack project.

    """
    openstack_client = get_openstack_client()
    if openstack_client.delete_server(instance_name):
        logger.info('Success! The instance {0} has been deleted from '
                    'Openstack.'.format(instance_name))
    else:
        logger.error('Instance {0} not found in Openstack project.'.format(
            instance_name))
