"""Module which publish all satellite6 upgrade tasks"""
# flake8:noqa pylint:disable=F401
from automation_tools import partition_disk
from automation_tools import product_install
from automation_tools import vm_create
from automation_tools import vm_destroy

from upgrade.helpers.docker import docker_cleanup_containers
from upgrade.helpers.docker import docker_execute_command
from upgrade.helpers.docker import generate_satellite_docker_clients_on_rhevm
from upgrade.helpers.docker import refresh_subscriptions_on_docker_clients
from upgrade.helpers.openstack import create_openstack_instance
from upgrade.helpers.openstack import delete_openstack_instance
from upgrade.helpers.tasks import create_capsule_ak
from upgrade.helpers.tasks import generate_custom_certs
from upgrade.helpers.tasks import job_execution_time
from upgrade.helpers.tasks import sync_capsule_repos_to_satellite
from upgrade.helpers.tasks import update_scap_content
from upgrade.helpers.tasks import upgrade_using_foreman_maintain
from upgrade.helpers.tools import copy_ssh_key
from upgrade.helpers.tools import disable_old_repos
from upgrade.helpers.tools import get_hostname_from_ip
from upgrade.helpers.tools import get_sat_cap_version
from upgrade.helpers.tools import host_pings
from upgrade.helpers.tools import host_ssh_availability_check
from upgrade.helpers.tools import reboot
from upgrade.runner import product_setup_for_db_upgrade
from upgrade.runner import product_setup_for_upgrade_on_brokers_machine
from upgrade.runner import product_upgrade
from upgrade.satellite import satellite_setup
from upgrade.satellite import satellite_upgrade
from upgrade_tests.helpers.existence import set_datastore
from upgrade_tests.helpers.existence import set_templatestore
from upgrade_tests.helpers.scenarios import delete_manifest
from upgrade_tests.helpers.scenarios import upload_manifest
