"""A set of common tasks for automating interactions with rhevm4

Note: Many functions and commands are affected by environment variables.
"""
import os
import sys
import time
import thread

from fabric.api import execute
from ovirtsdk4 import ConnectionBuilder
from ovirtsdk4 import types
from upgrade.helpers.logger import logger
from upgrade.helpers.tasks import (
    check_necessary_env_variables_for_upgrade,
    capsule_sync,
    check_ntpd,
    katello_restart,
)


logger = logger()


def get_rhevm4_client():
    """Creates and returns a client for rhevm4.

    The following environment variables affect this command:

    RHEV_USER
        The username of a rhevm project to login.
    RHEV_PASSWD
        The password of a rhevm project to login.
    RHEV_URL
        An url to API of rhevm project.
    """
    username = os.environ.get('RHEV_USER')
    if username is None:
        logger.warning('The RHEV_USER environment variable should be defined.')
    password = os.environ.get('RHEV_PASSWD')
    if password is None:
        logger.warning(
            'The RHEV_PASSWD environment variable should be defined.')
    api_url = os.environ.get('RHEV_URL')
    if api_url is None:
        logger.warning('An RHEV_URL environment variable should be defined.')
    builder = ConnectionBuilder(
        url=api_url,
        username=username,
        password=password,
        insecure=True
    )
    conn = builder.build()
    if not conn.test():
        logger.error('Invalid Connection details are provided to RHEVM.')
        sys.exit(1)
    return builder


def create_rhevm4_instance(
        instance_name, template_name, cluster=None, timeout=5):
    """Creates rhevm4 Instance from template.

    The assigning template should have network and storage configuration saved
    already.

    The following environment variables affect this command:

    RHEV_USER
        The username of a rhevm project to login.
    RHEV_PASSWD
        The password of a rhevm project to login.
    RHEV_URL
        An url to API of rhevm project.
    RHEV_CLUSTER
        Cluster name in RHEV where instance is created

    :param instance_name: A string. RHEVM Instance name to create.
    :param template_name: A string. RHEVM image name from which instance
        to be created.
    :param datacenter: A string. Name of the datacenter in rhevm
    :param cluster: A string. Name of the cluster in rhevm
    :param int timeout: The polling timeout in minutes to create rhevm
    instance.
    """
    if not cluster:
        cluster = os.environ.get('RHEV_CLUSTER')
    # Setup VM configuration
    vmconf = types.Vm(
        name=instance_name,
        cluster=types.Cluster(name=cluster),
        template=types.Template(name=template_name)
    )
    with get_rhevm4_client().build() as rhevm_client:
        logger.info('Turning on instance {0} from template {1}. Please wait '
                    'till get up ...'.format(instance_name, template_name))
        vservice = rhevm_client.system_service().vms_service()
        vm = vservice.add(vm=vmconf)
        if wait_till_rhevm4_instance_status(
                instance_name, 'down', timeout=timeout):
            vservice.vm_service(vm.id).start()
            if wait_till_rhevm4_instance_status(
                    instance_name, 'up', timeout=timeout):
                logger.info('Instance {0} is now up !'.format(instance_name))
                # Fetch the Instance FQDN only if RHEV-agent is installed
                # Templates under SAT-QE datacenter includes RHEV-agents.
                if rhevm_client.system_service(
                ).data_centers_service().list(search='name=SAT_QE'):
                    # get the hostname of instance
                    vm_fqdn = vservice.list(
                        search='name={}'.format(instance_name))[0].fqdn
                    logger.info('\t Instance FQDN : %s' % (vm_fqdn))
                    # We need value of vm_fqdn so that we can use it with CI
                    # For now, we are exporting it as a variable value
                    # and source it to use via shell script
                    file_path = "/tmp/rhev_instance.txt"
                    with open(file_path, 'w') as f1:
                        f1.write('export SAT_INSTANCE_FQDN={}'.format(vm_fqdn))


def delete_rhevm4_instance(instance_name, timeout=5):
    """Deletes RHEVM4 Instance.

    The following environment variables affect this command:

    RHEV_USER
        The username of a rhevm project to login.
    RHEV_PASSWD
        The password of a rhevm project to login.
    RHEV_URL
        An url to API of rhevm project.

    :param instance_name: A string. RHEVM instance name to delete.
    :param int timeout: The polling timeout in minutes to delete rhevm
    instance.
    """
    with get_rhevm4_client().build() as rhevm_client:
        vservice = rhevm_client.system_service().vms_service()
        vm = vservice.list(search='name={}'.format(instance_name))[0]
        if not vm:
            logger.info('The instance {0} is not found '
                        'in RHEV to delete!'.format(instance_name))
        else:
            logger.info(
                'Deleting instance {0} from RHEVM.'.format(instance_name))
            if vm.delete_protected:
                logger.warning(
                    'The instance {0} is under delete protection and cannot '
                    'be deleted.'.format(instance_name))
                sys.exit(1)
            if vm.status.name == 'UP':
                vservice.vm_service(vm.id).shutdown()
                if wait_till_rhevm4_instance_status(instance_name, 'down'):
                    vservice.vm_service(vm.id).remove()
            elif vm.status.name == 'DOWN':
                vservice.vm_service(vm.id).remove()
            timeup = time.time() + int(timeout) * 60
            while True:
                if time.time() > timeup:
                    logger.warning(
                        'The timeout for deleting RHEVM instance has reached!')
                    sys.exit(1)
                if not vservice.list(search='name={}'.format(instance_name)):
                    logger.info(
                        'Instance {0} is now deleted from RHEVM!'.format(
                            instance_name))
                    break


def wait_till_rhevm4_instance_status(instance_name, status, timeout=5):
    """Waits untill given RHEVM4 VM status reached.

    The following environment variables affect this command:

    RHEV_USER
        The username of a rhevm project to login.
    RHEV_PASSWD
        The password of a rhevm project to login.
    RHEV_URL
        An url to API of rhevm project.

    :param instance_name: A string. RHEVM Instance name to create.
    :param template_name: A string. RHEVM image name from which instance
        to be created.
    :param int timeout: The polling timeout in minutes to create rhevm
    instance.
    """
    with get_rhevm4_client().build() as rhevm_client:
        timeup = time.time() + int(timeout) * 60
        vservice = rhevm_client.system_service().vms_service()
        while True:
            if time.time() > timeup:
                logger.warning(
                    'Timeout in turning VM instance {0}.'.format(status))
                sys.exit(1)
            vm = vservice.list(search='name={}'.format(instance_name))[0]
            vm_status = vm.status.name
            logger.info('Current Status: {0}'.format(vm_status))
            if vm_status.lower() == status.lower():
                return True
            time.sleep(5)


def create_rhevm4_template(host, cluster, new_template, storage):
    """ Creates RHEVM4 template from Virtual machines

    :param string host: The Virtual machine name of which, template is to be
        created.
    :param string cluster: The Cluster name of the RHEVM, in which the
        template is to be created.
    :param string new_template: The name of the template to be created.
    :param string storage: The name of the storage domain, which will be
        used to create template.
    """
    with get_rhevm4_client().build() as rhevm_client:
        storage_domain = rhevm_client.system_service().storage_domains_service(
            ).list(search='name={}'.format(storage))[0]
        cluster = rhevm_client.system_service().clusters_service(
            ).list(search='name={}'.format(cluster))
        vservice = rhevm_client.system_service().vms_service()
        size = storage_domain.available / 1024 / 1024 / 1024
        vm = vservice.list(search='name={}'.format(host))[0]
        if size > 300 and vm:
            try:
                vservice.vm_service(vm.id).stop()
                logger.info('Waiting for VM to reach Down status')
                wait_till_rhevm4_instance_status(host, 'down')
                logger.info('Template creation in Progress')
                templateconf = types.Template(
                    name=new_template,
                    vm=vm,
                    cluster=cluster
                )
                tservice = rhevm_client.system_service().templates_service()
                tservice.add(template=templateconf)
                wait_till_rhevm4_instance_status(host, 'down', timeout=80)
                if tservice.list(search='name={}'.format(new_template)):
                    logger.info(
                        '{0} template is created successfully'.format(
                            new_template))
            except Exception as ex:
                logger.error(
                    'Failed to Create Template from VM:\n%s' % str(ex))
        else:
            logger.error('Low Storage cannot proceed or VM not found')
            sys.exit()


# Fabric task
def validate_and_create_rhevm4_templates(product):
    """Task to do a sanity check on the satellite and capsule and then
    create their templates after z-stream upgrade

    Environment variables required to run upgrade on RHEVM4 Setup and will be
    fetched from Jenkins:
    ----------------------------------------------------------------------

    RHEV_SAT_HOST
        The rhevm satellite hostname to run upgrade on
    RHEV_CAP_HOST
        The rhevm capsule hostname to run upgrade on
    RHEV_STORAGE
        The storage domain on the rhevm used to create templates
    RHEV_CLUSTER
        Cluster name in RHEV where instance is created
    RHEV_SAT_IMAGE
        The satellite Image from which satellite instance will be created
    RHEV_CAP_IMAGE
        The capsule Image from which capsule instance will be created
    RHEV_SAT_INSTANCE
        The satellite instance name in rhevm of which template is to be
        created, generally the upgraded box
    RHEV_CAP_INSTANCE
        The capsule instance name in rhevm of which template is to be
        created, generally the upgraded box
    """
    # Get the instances name, specified in the jenkins job
    if product not in ['satellite', 'n-1']:
        os_version = os.environ.get('OS_VERSION')
        sat_instance = 'upgrade_satellite_auto_rhel{0}'.format(os_version)
        logger.info('Satellite Instance name {0}'.format(sat_instance))
        cap_instance = 'upgrade_capsule_auto_rhel{0}'.format(os_version)
        logger.info('Capsule Instance name {0}'.format(cap_instance))
        cluster = os.environ.get('RHEV_CLUSTER')
        storage = os.environ.get('RHEV_STORAGE')
        sat_host = os.environ.get('RHEV_SAT_HOST')
        new_sat_template = os.environ.get('RHEV_SAT_IMAGE') + "_new"
        cap_host = os.environ.get('RHEV_CAP_HOST')
        new_cap_template = os.environ.get('RHEV_CAP_IMAGE') + "_new"
        if check_necessary_env_variables_for_upgrade('capsule'):
            execute(check_ntpd, host=sat_host)
            execute(katello_restart, host=sat_host)
            execute(capsule_sync, cap_host, host=sat_host)
            execute(check_ntpd, host=cap_host)
            execute(katello_restart, host=cap_host)
            thread.start_new_thread(
                create_rhevm4_template,
                (
                    sat_instance,
                    cluster,
                    new_sat_template,
                    storage)
            )
            thread.start_new_thread(
                create_rhevm4_template,
                (
                    cap_instance,
                    cluster,
                    new_cap_template,
                    storage)
            )
            wait_till_rhevm4_instance_status(
                sat_instance, 'Image Locked', timeout=30)
            wait_till_rhevm4_instance_status(
                sat_instance, 'down', timeout=240)
