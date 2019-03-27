"""Module which publish all satellite6 upgrade tasks"""

from automation_tools import partition_disk

from upgrade.runner import (
    product_upgrade,
    setup_products_for_upgrade
)
from upgrade.satellite import (
    satellite6_setup,
    satellite6_upgrade,
    satellite6_zstream_upgrade
)
from upgrade.helpers.docker import (
    docker_execute_command,
    generate_satellite_docker_clients_on_rhevm,
    refresh_subscriptions_on_docker_clients,
    docker_cleanup_containers
)
from upgrade.helpers.openstack import (
    create_openstack_instance,
    delete_openstack_instance,
)
from upgrade.helpers.rhevm4 import (
    create_rhevm4_instance,
    delete_rhevm4_instance,
    wait_till_rhevm4_instance_status,
    validate_and_create_rhevm4_templates
)
from upgrade.helpers.tasks import (
    sync_capsule_repos_to_upgrade,
    sync_tools_repos_to_upgrade,
    setup_foreman_maintain,
    setup_satellite_clone,
    upgrade_using_foreman_maintain,
    upgrade_puppet3_to_puppet4
)
from upgrade.helpers.tools import (
    copy_ssh_key,
    disable_old_repos,
    get_hostname_from_ip,
    get_sat_cap_version,
    host_pings,
    host_ssh_availability_check,
    reboot
)
from upgrade_tests.helpers.existence import (
    set_datastore,
    set_templatestore,
)
from upgrade_tests.helpers.scenarios import (
    upload_manifest,
    delete_manifest,
)