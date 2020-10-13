"""All the variants those changes during upgrade and the helper functions"""
import os

from upgrade_tests.helpers.constants import SUPPORTED_SAT_VERSIONS


class VersionError(Exception):
    """Error due to Unsupported Satellite Version"""


# The dictionary of entity variants where the key is a component name
# and value is list of all the component entity variants list those changes
# during satellite versions
#
# Structure of variants directory:
# {'component_name_e.g_filter,repository':
#        [
#        [variant1_6.1, variant1_6.2],
#        [variant2_6.1, variant2_6.2],
#        ]
# }
#
# Note: The variants should be listed from 6.1 onwards
_entity_varients = {
    'capsule': [
        ['tftp, dns, dhcp, puppet, puppet ca, bmc, pulp node, templates, discovery, openscap, dynflow, ssh']*3 + # noqa
        ['puppet, puppet ca, pulp node, templates, discovery, tftp, dns, dhcp, bmc, openscap, dynflow, ssh, ansible'] +  # noqa
        ['templates, discovery, bmc, openscap, dynflow, ssh, ansible, pulp node, dns, tftp, dhcp, puppet ca, puppet, httpboot'] +  # noqa
        ['templates, discovery, bmc, openscap, dynflow, ssh, ansible, pulp node, dns, tftp, puppet ca, puppet, dhcp, httpboot'] +  # noqa
        ['templates, discovery, bmc, openscap, dynflow, ssh, ansible, pulp node, dns, tftp, puppet, dhcp, httpboot, puppet ca'],
        ['tftp, dns, dhcp, puppet, puppet ca, bmc, pulp, discovery, openscap, dynflow, ssh']*2 +  # noqa
        ['tftp, dns, dhcp, puppet, puppet ca, pulp, discovery, bmc, openscap, dynflow, ssh, ansible'] +  # noqa
        ['tftp, dns, dhcp, puppet, puppet ca, pulp, discovery, bmc, openscap, dynflow, ssh, ansible, templates'] +  # noqa
        ['discovery, bmc, openscap, dynflow, ssh, ansible, templates, pulp, dns, tftp, dhcp, puppet ca, puppet, httpboot'] +  # noqa
        ['discovery, bmc, openscap, dynflow, ssh, ansible, templates, pulp, dns, tftp, puppet ca, puppet, dhcp, httpboot'] + # noqa
        ['discovery, bmc, openscap, dynflow, ssh, ansible, templates, pulp, dns, tftp, puppet, dhcp, httpboot, puppet ca']
    ],
    'compute-resource': [
        ['rhev']*2+['rhv']*5],
    'filter': [
        # Resource Type Variants
        ['lookupkey']+['variablelookupkey']*6,
        ['(miscellaneous)']+['foremanopenscap::arfreport']*6,
        ['organization']+['katello::subscription']*6,
        ['configtemplate']+['provisioningtemplate']*6,
        ['authsourceldap']*3+['authsource']*4,
        ['templateinvocation']*3+['(miscellaneous)']*4,
        ['docker/imagesearch']*3+['(miscellaneous)']*4,
        # Permissions Variants
        ['view_templates, create_templates, edit_templates, '
         'destroy_templates, deploy_templates'] +
        ['view_provisioning_templates, create_provisioning_templates, '
         'edit_provisioning_templates, destroy_provisioning_templates, '
         'deploy_provisioning_templates']*6,
        ["escalate_roles"]*6 + ["escalate_roles, generate_foreman_rh_cloud, view_foreman_rh_cloud"],
        ['viewer']*2+['customized viewer']*5,
        ['site manager']*2+['customized site manager']*5,
        ['manager']*2+['customized manager']*5,
        ["variablelookupkey"]*6 + ["(miscellaneous)"],
        ["view_external_variables"]*6 + [''],
        ['discovery reader']*2+['customized discovery reader']*5,
        ['discovery manager']*2+['customized discovery manager']*5,
        ['compliance viewer']*2+['customized compliance viewer']*5,
        ['compliance manager']*2+['customized compliance manager']*5,
        ['anonymous']*2+['default role']*5,
        ['import_templates, export_templates']*5 +
        ['import_templates, export_templates, view_template_syncs']*2,
        ['commonparameter']*2+['parameter']*5,
        ['execute_template_invocation']*3+['']*4,
        ['create_job_invocations, view_job_invocations']*3 +
        ['create_job_invocations, view_job_invocations, cancel_job_invocations']*4, # noqa
        ['execute_template_invocation, filter_autocompletion_for_template_invocation']*3 + # noqa
        ['filter_autocompletion_for_template_invocation, create_template_invocations']*4, # noqa
        ['view_hostgroups, create_hostgroups, edit_hostgroups, destroy_hostgroups']*3 + # noqa
        ['view_hostgroups, create_hostgroups, edit_hostgroups, destroy_hostgroups, play_roles_on_hostgroup']*4, # noqa
        ['view_registries, create_registries, destroy_registries']*3 +
        ['view_registries, create_registries, destroy_registries, search_repository_image_search']*4, # noqa
        ['search_repository_image_search']*3 + ['']*4,
        ['view_gpg_keys, create_gpg_keys, edit_gpg_keys, destroy_gpg_keys']*3 +
        ['view_gpg_keys, create_gpg_keys, edit_gpg_keys, destroy_gpg_keys, view_content_credentials, create_content_credentials, edit_content_credentials, destroy_content_credentials']*4, # noqa
        ['view_subscriptions, attach_subscriptions, unattach_subscriptions, import_manifest, delete_manifest']*3 + # noqa
        ['view_subscriptions, attach_subscriptions, unattach_subscriptions, import_manifest, delete_manifest, manage_subscription_allocations']*4, # noqa
        ['execute_template_invocation, filter_autocompletion_for_template_invocation']*3 + # noqa
        ['filter_autocompletion_for_template_invocation, create_template_invocations, view_template_invocations']*4, # noqa
        ['view_gpg_keys']*3 + ['view_gpg_keys, view_content_credentials']*4,
        ["view_mail_notifications"]*6 + ["view_mail_notifications, edit_user_mail_notifications"],
        ["view_external_variables, create_external_variables, edit_external_variables, destroy_external_variables"] * 6 + [''],
        ["view_compute_resources, create_compute_resources, edit_compute_resources, destroy_compute_resources, view_compute_resources_vms, create_compute_resources_vms, edit_compute_resources_vms, destroy_compute_resources_vms, power_compute_resources_vms, console_compute_resources_vms"] * 6 +
        ["view_compute_resources, create_compute_resources, edit_compute_resources, destroy_compute_resources, view_compute_resources_vms, create_compute_resources_vms, edit_compute_resources_vms, destroy_compute_resources_vms, power_compute_resources_vms, console_compute_resources_vms, power_vm_compute_resources, destroy_vm_compute_resources"],
        ["console_compute_resources_vms, power_compute_resources_vms, destroy_compute_resources_vms, edit_compute_resources_vms, create_compute_resources_vms, view_compute_resources_vms, destroy_compute_resources, edit_compute_resources, create_compute_resources, view_compute_resources"] * 6 +
        ["view_compute_resources, create_compute_resources, edit_compute_resources, destroy_compute_resources, view_compute_resources_vms, create_compute_resources_vms, edit_compute_resources_vms, destroy_compute_resources_vms, power_compute_resources_vms, console_compute_resources_vms"],
        ["access_dashboard, view_plugins, view_statistics, view_tasks, view_cases, attachments, configuration, app_root, view_log_viewer, logs, download_bootdisk, my_organizations, rh_telemetry_api, rh_telemetry_view, rh_telemetry_configurations, create_arf_reports, view_rh_search, strata_api, generate_ansible_inventory, view_statuses"] * 6 +
        ["access_dashboard, view_plugins, view_statistics, view_tasks, view_cases, attachments, configuration, app_root, view_log_viewer, logs, download_bootdisk, my_organizations, rh_telemetry_api, rh_telemetry_view, rh_telemetry_configurations, create_arf_reports, view_rh_search, strata_api, generate_ansible_inventory, view_statuses, generate_foreman_rh_cloud, view_foreman_rh_cloud"],
        ['view_hosts, create_hosts, build_hosts, view_discovered_hosts, provision_discovered_hosts, edit_discovered_hosts, destroy_discovered_hosts, submit_discovered_hosts, auto_provision_discovered_hosts']*3 + # noqa
        ['view_hosts, create_hosts, edit_hosts, build_hosts, view_discovered_hosts, provision_discovered_hosts, edit_discovered_hosts, destroy_discovered_hosts, submit_discovered_hosts, auto_provision_discovered_hosts']*4, # noqa
        ['view_hosts, create_hosts, edit_hosts, destroy_hosts, build_hosts, power_hosts, console_hosts, puppetrun_hosts, ipmi_boot_hosts, view_discovered_hosts, provision_discovered_hosts, edit_discovered_hosts, destroy_discovered_hosts, submit_discovered_hosts, auto_provision_discovered_hosts']*3 +  # noqa
        ['view_hosts, create_hosts, edit_hosts, destroy_hosts, build_hosts, power_hosts, console_hosts, puppetrun_hosts, ipmi_boot_hosts, view_discovered_hosts, provision_discovered_hosts, edit_discovered_hosts, destroy_discovered_hosts, submit_discovered_hosts, auto_provision_discovered_hosts, play_roles_on_host']*2 +
        ["view_hosts, create_hosts, edit_hosts, destroy_hosts, build_hosts, power_hosts, console_hosts, puppetrun_hosts, ipmi_boot_hosts, view_discovered_hosts, provision_discovered_hosts, edit_discovered_hosts, destroy_discovered_hosts, submit_discovered_hosts, auto_provision_discovered_hosts, play_roles_on_host, cockpit_hosts"] +
        ["view_hosts, create_hosts, edit_hosts, destroy_hosts, build_hosts, power_hosts, console_hosts, puppetrun_hosts, ipmi_boot_hosts, view_discovered_hosts, provision_discovered_hosts, edit_discovered_hosts, destroy_discovered_hosts, submit_discovered_hosts, auto_provision_discovered_hosts, play_roles_on_host, cockpit_hosts, forget_status_hosts"],  # noqa
        ['auto_provision_discovered_hosts,build_hosts,console_hosts,create_hosts,destroy_discovered_hosts,destroy_hosts,edit_discovered_hosts,edit_hosts,ipmi_boot_hosts,play_roles_on_host,power_hosts,provision_discovered_hosts,puppetrun_hosts,submit_discovered_hosts,view_discovered_hosts,view_hosts']*4 +  # noqa
        ['auto_provision_discovered_hosts,build_hosts,cockpit_hosts,console_hosts,create_hosts,destroy_discovered_hosts,destroy_hosts,edit_discovered_hosts,edit_hosts,ipmi_boot_hosts,play_roles_on_host,power_hosts,provision_discovered_hosts,puppetrun_hosts,submit_discovered_hosts,view_discovered_hosts,view_hosts']*3  # noqa
    ],
    'organization': [
        ['default_organization']*3+['default organization']*4],  # noqa
    'role': [
        # Role Variants
        ['viewer']*2+['customized viewer']*5,
        ['site manager']*2+['customized site manager']*5,
        ['manager']*2+['customized manager']*5,
        ['discovery reader']*2+['customized discovery reader']*5,  # noqa
        ['discovery manager']*2+['customized discovery manager']*5,  # noqa
        ['compliance viewer']*2+['customized compliance viewer']*5,  # noqa
        ['compliance manager']*2+['customized compliance manager']*5,  # noqa
        ['anonymous']*2+['default role']*5],
    'settings': [
        # Value Variants
        ['immediate']*2+['on_demand']*5,
        ['']*2+['/etc/pki/katello/certs/katello-apache.crt']*5,
        ['']*2+['/etc/pki/katello/private/katello-apache.key']*5,
        ['false']*2+['true']*5,
        ['["lo", "usb*", "vnet*", "macvtap*"]']*3 +
        ['["lo", "usb*", "vnet*", "macvtap*", "_vdsmdummy_", "veth*", '
         '"docker*", "tap*", "qbr*", "qvb*", "qvo*", "qr-*", "qg-*", '
         '"vlinuxbr*", "vovsbr*"]']*4,
        ['["lo", "en*v*", "usb*", "vnet*", "macvtap*", "_vdsmdummy_", '
         '"veth*", "docker*", "tap*", "qbr*", "qvb*", "qvo*", "qr-*", '
         '"qg-*", "vlinuxbr*", "vovsbr*"]']*4 +
        ['["lo", "en*v*", "usb*", "vnet*", "macvtap*", "_vdsmdummy_", '
         '"veth*", "docker*", "tap*", "qbr*", "qvb*", "qvo*", "qr-*", '
         '"qg-*", "vlinuxbr*", "vovsbr*", "mountpoints", "partitions", '
         '"blockdevice*"]'] +
        ['["lo", "en*v*", "usb*", "vnet*", "macvtap*", "_vdsmdummy_", '
         '"veth*", "docker*", "tap*", "qbr*", "qvb*", "qvo*", "qr-*", '
         '"qg-*", "vlinuxbr*", "vovsbr*"]']*2,
        ['']*5 + ['*****']*2,
        [f"{os.environ.get('REMOTE_EXECUTION_SSH_PASSWORD')}"]*5 + ['*****']*2,
        [f"{os.environ.get('OAUTH_CONSUMER_KEY')}"]*5 + ['*****']*2,
        [f"{os.environ.get('OAUTH_CONSUMER_SECRET')}"]*5 + ['*****']*2,
        ['ansible inventory']*6 + ['ansible - ansible inventory'],
        ['']*6 + ["external"],
        ['']*6 + ["none"],
        ['']*6 + ["[]"],
        ['false']*6 + ["keep"],
        ['false']*6 + ["none"],
        # Description Variants
        ['fact name to use for primary interface detection and hostname']*2 +
        ['fact name to use for primary interface detection']*5,
        ['automatically reboot discovered host during provisioning']*2 +
        ['automatically reboot or kexec discovered host during provisioning']*5,  # noqa
        ['default provisioning template for new atomic operating systems']*2 +
        ['default provisioning template for new atomic operating systems '
         'created from synced content']*5,
        ['default finish template for new operating systems']*2 +
        ['default finish template for new operating systems created '
         'from synced content']*5,
        ['default ipxe template for new operating systems']*2 +
        ['default ipxe template for new operating systems created from '
         'synced content']*5,
        ['default kexec template for new operating systems']*2 +
        ['default kexec template for new operating systems created '
         'from synced content']*5,
        ['default provisioning template for new operating systems']*2 +
        ['default provisioning template for operating systems created'
         ' from synced content']*5,
        ['default partitioning table for new operating systems']*2 +
        ['default partitioning table for new operating systems created'
         ' from synced content']*5,
        ['default pxelinux template for new operating systems']*2 +
        ['default pxelinux template for new operating systems created'
         ' from synced content']*5,
        ['default user data for new operating systems']*2 +
        ['default user data for new operating systems created from '
         'synced content']*5,
        ['default metadata export mode, refresh re-renders metadata, keep will keep '
         'existing metadata, remove exports template withou metadata']*5 +
        ['default metadata export mode, refresh re-renders metadata, '
         'keep will keep existing metadata, remove exports template without metadata']*2,
        ['negate the prefix (for purging) / filter (for importing/exporting)']*5 +
        ['negate the filter for import/export']*2,
        ['the string all imported templates should begin with']*5 +
        ['the string that will be added as prefix to imported templates']*2,
        ['target path to import and export. different protocols can be used, '
         'e.g. /tmp/dir, git://example.com, https://example.com, ssh://example.com']*5 +
        ['target path to import/export. different protocols can be used, '
         'for example /tmp/dir, git://example.com, https://example.com, '
         'ssh://example.com. when exporting to /tmp, note that production '
         'deployments may be configured to use private tmp.']*2,
        ['how the logic of solving dependencies in a content view is managed. '
         'conservative will only add packages to solve the dependencies if '
         'the packaged needed doesn\'t exist. greedy will pull in the latest package '
         'to solve a dependency even if it already does exist in the repository.']*5 +
        ['how the logic of solving dependencies in a content view is managed. '
         'conservative will only add packages to solve the dependencies if the package '
         'needed doesn\'t exist. greedy will pull in the latest package to '
         'solve a dependency even if it already does exist in the repository.']*2,
        ["hosts that will be trusted in addition to smart proxies for access to "
         "fact/report importers and enc output"]*6 +
        ["list of hostnames, ipv4, ipv6 addresses or subnets to be trusted in addition "
         "to smart proxies for access to fact/report importers and enc output"],
        ["should importing lock templates?"]*6 + ["how to handle lock for imported templates?"],
        ["sets a proxy for all outgoing http connections."]*6 +
        ["sets a proxy for all outgoing http connections from foreman. "
         "system-wide proxies must be configured at operating system level."],
        ['should the ip addresses on host interfaces be preferred over the fqdn? it is useful, '
         'when dns not resolving the fqdns properly. you may override this per host by setting '
         'a parameter called remote_execution_connect_by_ip.']*6 +
        ["should the ip addresses on host interfaces be preferred over the fqdn? it is"
         " useful when dns not resolving the fqdns properly. you may override this per host by "
         "setting a parameter called remote_execution_connect_by_ip. this setting only applies "
         "to ipv4. when the host has only an ipv6 address on the interface used for remote execution, "
         "hostname will be used even if this setting is set to true."],
        ["name of the external auth source where unknown externally authentication users "
         "(see authorize_login_delegation) should be created (keep unset to prevent "
         "the autocreation)"]*6 +
        ["name of the external auth source where unknown externally authentication users "
         "(see authorize_login_delegation) should be created (if you want to prevent the "
         "autocreation, keep unset)"],
        ['search for remote execution proxy outside of the proxies assigned to the host.'
         ' if locations or organizations are enabled, the search will be limited '
         'to the host\'s organization or location.']*5 +
        ['search for remote execution proxy outside of the proxies assigned to the host.'
         ' the search will be limited to the host\'s organization and location.']*2,
        ['import or export names matching this regex (case-insensitive; snippets '
         'are not filtered)']*5 +
        ['import/export names matching this regex (case-insensitive; '
         'snippets are not filtered)']*2,
        ['when unregistering host via subscription-manager, also delete '
         'server-side host record']*2 +
        ['when unregistering a host via subscription-manager, also delete'
         ' the host record. managed resources linked to host such as virtual'
         ' machines and dns records may also be deleted.']*5,
        ['private key that foreman will use to encrypt websockets']*2 +
        ['private key file that foreman will use to encrypt websockets']*5,
        ['duration in minutes after the puppet interval for servers to be classed as out of sync.']*3 +  # noqa
        ['duration in minutes after servers are classed as out of sync.']*4,
        ['satellite kickstart default user data'] * 3 + ['kickstart default user data']*4,  # noqa
        ['satellite kickstart default'] * 3 + ['kickstart default']*4,
        ['satellite kickstart default finish'] * 3 + ['kickstart default finish']*4,  # noqa
        ['satellite atomic kickstart default'] * 3 + ['atomic kickstart default']*4,  # noqa
        ['default_location'] * 3 + ['default location']*4,
        ['what command should be used to switch to the effective user. one of ["sudo", "su"]']*4 +  # noqa
        ['what command should be used to switch to the effective user. one of ["sudo", "dzdo", "su"]']*3,  # noqa
        ["exclude pattern for all types of imported facts (rhsm, puppet e.t.c.). those facts won't be stored "  # noqa
         "in foreman's database. you can use * wildcard to match names with indexes e.g. macvtap*"]*4 +  # noqa
        ["exclude pattern for all types of imported facts (puppet, ansible, rhsm). those facts won't be "  # noqa
         "stored in foreman's database. you can use * wildcard to match names with indexes e.g. ignore* will "  # noqa
         "filter out ignore, ignore123 as well as a::ignore or even a::ignore123::b"]*3,
        ["url hosts will retrieve templates from during build (normally http as many installers don't support https)"]*4 +  # noqa
        ["url hosts will retrieve templates from during build, when it starts with https unattended/userdata controllers "  # noqa
         "cannot be accessed via http"]*3],
    'subscription': [
        # Validity Variants
        ['-1']*2+['unlimited']*5],
    'template': [
        # name variants
        ['idm_register']*3+['deprecated idm_register']*4,
        ['satellite atomic kickstart default']*3+['deprecated satellite atomic kickstart default']*4, # noqa
        ['satellite kickstart default']*3+['deprecated satellite kickstart default']*4,  # noqa
        ['satellite kickstart default finish']*3+['deprecated satellite kickstart default finish']*4, # noqa
        ['satellite kickstart default user data']*3+['deprecated satellite kickstart default user data']*4 # noqa
    ]
}

template_varients = {
    'template': [
        # Preseed default user data, Preseed default finish, Atomic Kickstart default,
        # AutoYaST default user data, AutoYaST default, Preseed default user data,
        # XenServer default finish, AutoYaST SLES default
        '- /usr/bin/wget --quiet --output-document=/dev/null --no-check-certificate ',
        "+ <%= snippet 'built' %>"
        # Preseed default finish
        '+ <%= snippet_if_exists(template_name + " custom snippet") %>',
        "- /usr/bin/wget --no-proxy --quiet --output-document=/dev/null --no-check-certificate <%= foreman_url('built') %>",  # noqa
        "+ <%= snippet 'efibootmgr_netboot' %>",
        # freeipa_register
        '-   <% if @host.operatingsystem.major.to_i > 6 -%>',
        '+   <% os_major = @host.operatingsystem.major.to_i %>',
        '+   <% if os_major == 7 -%>',
        '+   <% elsif os_major > 7 %>',
        '+     /usr/libexec/openssh/sshd-keygen',
        # Atomic Kickstart default
        "+ <%= snippet 'efibootmgr_netboot' %>",
        "- curl -s -o /dev/null --insecure <%= foreman_url('built') %>",
        # PXEGrub2 global default
        "+ echo Default PXE global template entry is set to \'<%= global_setting(\"default_pxe_item_global\", \"local\") %>\'",  # noqa
        '+ <%= snippet "pxegrub2_mac" %>',
        '+ ',
        '+ # Only grub2 from redhat has MAC-based config loading patch, load explicitly',
        '- # On Debian/Ubuntu grub2 does not have patch for loading MAC-based configs. Also due to bug',  # noqa
        '- # in RHEL 7.4 files are loaded with an extra ":" character at the end. This workarounds both',  # noqa
        '- # cases, make sure "regexp.mod" file is present on the TFTP. For more info see:',
        '- # https://bugzilla.redhat.com/show_bug.cgi?id=1370642#c70',
        '- insmod regexp',
        '- regexp --set=1:m1 --set=2:m2 --set=3:m3 --set=4:m4 --set=5:m5 --set=6:m6 \'^([0-9a-f]{1,2})\\:([0-9a-f]{1,2})\\:([0-9a-f]{1,2})\\:([0-9a-f]{1,2})\\:([0-9a-f]{1,2})\\:([0-9a-f]{1,2})\' "$net_default_mac"',  # noqa
        '- mac=${m1}-${m2}-${m3}-${m4}-${m5}-${m6}',
        '+ # And if that fails render chain and discovery menu',
        '- ',
        # Preseed default PXEGrub2
        '+ <%= snippet_if_exists(template_name + " custom menu") %>',
        # redhat_register
        '+ -%>',
        '+ <%#',
        '+ #',
        '+ #   subscription_manager_override_repos_cost = <cost>  Override repository cost',
        "+   <% if host_param('subscription_manager_override_repos_cost') %>",
        '+     for repo in $(subscription-manager repos --list-enabled | grep "Repo ID:" | awk -F\' \' \'{ print $3 }\'); do',  # noqa
        '+       <%= "subscription-manager repo-override --list --repo $repo | grep \'cost:\' &>/dev/null || subscription-manager repo-override --repo $repo --add=cost:#{host_param(\'subscription_manager_override_repos_cost\')}" %>',  # noqa
        '+     done',
        '+   <% end %>',
        # AutoYaST default user data
        "- /usr/bin/curl -o /dev/null -k '<%= foreman_url('built') %>'",
        # Kickstart default iPXE
        "+ <%- if @host.operatingsystem.name != 'Fedora' && @host.operatingsystem.major.to_i >= 7 && host_param_true?('fips_enabled') %>",  # noqa
        "+ <%-   fips = 'fips=1' -%>",
        '+ <%- else -%>',
        "+ <%-   fips = '' -%>",
        '+ <%- end -%>',
        '- kernel <%= "#{@host.url_for_boot(:kernel)}" %> initrd=initrd.img ks=<%= foreman_url(\'provision\')%><%= static %> inst.stage2=<%= @host.operatingsystem.medium_uri(@host) %> <%= stage2 %> ksdevice=<%= @host.mac %> network kssendmac ks.sendmac inst.ks.sendmac <%= net_options %>',  # noqa
        '+ kernel <%= "#{@host.url_for_boot(:kernel)}" %> initrd=initrd.img ks=<%= foreman_url(\'provision\')%><%= static %> inst.stage2=<%= @host.operatingsystem.medium_uri(@host) %> <%= stage2 %> ksdevice=<%= @host.mac %> network kssendmac ks.sendmac inst.ks.sendmac <%= net_options %> <%= fips %>',  # noqa
        '+ imgstat',
        '+ sleep 2',
        # AutoYaST SLES default
        '+ <% if os_major >= 15 -%>',
        '+   <ntp-client>',
        '+     <ntp_policy>auto</ntp_policy>',
        '+     <ntp_servers config:type="list">',
        '+       <ntp_server>',
        "+         <address><%= host_param('ntp-server') || '0.opensuse.pool.ntp.org' %></address>",  # noqa
        '+         <iburst config:type="boolean">false</iburst>',
        '+         <offline config:type="boolean">true</offline>',
        '+       </ntp_server>',
        '+     </ntp_servers>',
        '+     <ntp_sync>15</ntp_sync>',
        '+   </ntp-client>',
        '+ <% else -%>',
        '+ <% end -%>',
        '+     <products config:type="list">',
        '+       <product>SLES</product>',
        '+     </products>',
        '+     <patterns config:type="list">',
        '+       <pattern>enhanced_base</pattern>',
        '+     </patterns>',
        "- /usr/bin/curl -o /dev/null -k '<%= foreman_url('built') %>'",
        '+ <% if os_major >= 15 -%>',
        '+       <listentry>',
        "+         <media_url><%= host_param('sle-module-basesystem-url') %></media_url>",
        '+         <product_dir>/Module-Basesystem</product_dir>',
        '+         <product>sle-module-basesystem</product>',
        '+       </listentry>',
        "+ <% if host_param_true?('enable-puppetlabs-pc1-repo') or host_param_true?('enable-puppetlabs-puppet5-repo') -%>",  # noqa
        '+ <%',
        "+   puppet_repo_url_base = 'http://yum.puppetlabs.com'",
        "- <% if host_param_true?('enable-puppetlabs-pc1-repo') -%>",
        "+   if host_param_true?('enable-puppetlabs-pc1-repo')",
        '+     puppet_repo_url = "#{puppet_repo_url_base}/sles/#{os_major}/PC1/#{@host.architecture}/"',  # noqa
        "+   elsif host_param_true?('enable-puppetlabs-puppet5-repo')",
        '+     puppet_repo_url = "#{puppet_repo_url_base}/puppet5/sles/#{os_major}/#{@host.architecture}/"',  # noqa
        '+   end',
        '-         <media_url><![CDATA[http://yum.puppetlabs.com/sles/<%= os_major %>/PC1/<%= @host.architecture %>/]]></media_url>',  # noqa
        '+         <media_url><![CDATA[<%= puppet_repo_url %>]]></media_url>',
        # AutoYaST default
        '+   os_major = @host.operatingsystem.major.to_i',
        '+   <%# NTP client configuration has incompatible changes in Leap 15 -%>',
        '+   <% if os_major <= 12 || os_major == 42 -%>',
        '+   <ntp-client>',
        '+    <ntp_policy>auto</ntp_policy>',
        '+    <ntp_servers config:type="list">',
        '+     <ntp_server>',
        '+      <iburst config:type="boolean">false</iburst>',
        "+      <address><%= host_param('ntp-server') || '0.opensuse.pool.ntp.org' %></address>",
        '+      <offline config:type="boolean">true</offline>',
        '+     </ntp_server>',
        '+    </ntp_servers>',
        '+    <ntp_sync>systemd</ntp_sync>',
        '+    </ntp-client>',
        "- /usr/bin/curl -o /dev/null -k '<%= foreman_url('built') %>'",
        # Alterator default finish
        "- /usr/bin/wget -q -O /dev/null --no-check-certificate <%= foreman_url('built') %>",
        # iPXE global default
        '- item --key l local     Continue local boot',
        '+ item --key l local     Local boot (next entry)',
        '- item --key d discovery Foreman Discovery',
        '+ item --key d discovery Discovery from ${next-server}:8000 (httpboot module)',
        '+ item --key d discovery8448 Discovery from ${next-server}:8448 (httpboot module)',
        '+ item --key d discovery80 Discovery from ${next-server}:80 (custom script)',
        '- kernel ${next-server}/boot/fdi-image/vmlinuz0 rootflags=loop root=live:/fdi.iso rootfstype=auto ro rd.live.image acpi=force rd.luks=0 rd.md=0 rd.dm=0 rd.lvm=0 rd.bootif=0 rd.neednet=0 nomodeset proxy.url=<%= foreman_server_url %> proxy.type=foreman BOOTIF=01-${net0/mac}',  # noqa
        '+ kernel http://${next-server}:8000/boot/fdi-image/vmlinuz0 initrd=initrd0.img rootflags=loop root=live:/fdi.iso rootfstype=auto ro rd.live.image acpi=force rd.luks=0 rd.md=0 rd.dm=0 rd.lvm=0 rd.bootif=0 rd.neednet=0 nomodeset nokaslr proxy.url=<%= foreman_server_url %> proxy.type=foreman BOOTIF=01-${net0/mac}',  # noqa
        '- initrd ${next-server}/boot/fdi-image/initrd0.img',
        '+ initrd http://${next-server}:8000/boot/fdi-image/initrd0.img',
        '+ imgstat',
        '+ sleep 2',
        '+ :discovery80',
        '+ dhcp',
        '+ kernel http://${next-server}/httpboot/boot/fdi-image/vmlinuz0 initrd=initrd0.img rootflags=loop root=live:/fdi.iso rootfstype=auto ro rd.live.image acpi=force rd.luks=0 rd.md=0 rd.dm=0 rd.lvm=0 rd.bootif=0 rd.neednet=0 nomodeset nokaslr proxy.url=<%= foreman_server_url %> proxy.type=foreman BOOTIF=01-${net0/mac}',  # noqa
        '+ initrd http://${next-server}/httpboot/boot/fdi-image/initrd0.img',
        '+ imgstat',
        '+ sleep 2',
        '+ boot || goto failed',
        '+ goto start',
        '+ :discovery8000',
        '+ kernel http://${next-server}:8000/httpboot/boot/fdi-image/vmlinuz0 initrd=initrd0.img rootflags=loop root=live:/fdi.iso rootfstype=auto ro rd.live.image acpi=force rd.luks=0 rd.md=0 rd.dm=0 rd.lvm=0 rd.bootif=0 rd.neednet=0 nomodeset nokaslr proxy.url=<%= foreman_server_url %> proxy.type=foreman BOOTIF=01-${net0/mac}',  # noqa
        '+ initrd http://${next-server}:8000/httpboot/boot/fdi-image/initrd0.img',
        '+ boot || goto failed',
        # Example foreman_bootdisk host template
        '+ # Note: When multiple DNS servers are specified, only the first',
        '+ # server will be used. See: http://ipxe.org/cfg/dns',
        '- <% if interface.subnet.dns_primary.present? %>',
        '- # Note, iPXE can only use one DNS server',
        '- echo Using DNS <%= interface.subnet.dns_primary %>',
        '- set dns <%= interface.subnet.dns_primary %>',
        '+ <% dns = interface.subnet.dns_servers.first -%>',
        '+ <% if dns.present? -%>',
        '+ echo Using DNS <%= dns %>',
        '+ set dns <%= dns %>',
        # Preseed default user data
        "- /usr/bin/wget --quiet --output-document=/dev/null --no-check-certificate <%= foreman_url('built') %>",  # noqa
        # pxelinux_discovery
        '-   APPEND initrd=boot/fdi-image/initrd0.img rootflags=loop root=live:/fdi.iso rootfstype=auto ro rd.live.image acpi=force rd.luks=0 rd.md=0 rd.dm=0 rd.lvm=0 rd.bootif=0 rd.neednet=0 nomodeset proxy.url=<%= foreman_server_url %> proxy.type=foreman',  # noqa
        '+   APPEND initrd=boot/fdi-image/initrd0.img rootflags=loop root=live:/fdi.iso rootfstype=auto ro rd.live.image acpi=force rd.luks=0 rd.md=0 rd.dm=0 rd.lvm=0 rd.bootif=0 rd.neednet=0 nokaslr nomodeset proxy.url=<%= foreman_server_url %> proxy.type=foreman',  # noqa
        '- kernel http://foreman_url/pub/vmlinuz0 rootflags=loop root=live:/fdi.iso rootfstype=auto ro rd.live.image acpi=force rd.luks=0 rd.md=0 rd.dm=0 rd.lvm=0 rd.bootif=0 rd.neednet=0 nomodeset proxy.url=https://foreman_url proxy.type=foreman BOOTIF=01-${net0/mac}',  # noqa
        '+ kernel http://foreman_url/pub/vmlinuz0 rootflags=loop root=live:/fdi.iso rootfstype=auto ro rd.live.image acpi=force rd.luks=0 rd.md=0 rd.dm=0 rd.lvm=0 rd.bootif=0 rd.neednet=0 nokaslr nomodeset proxy.url=https://foreman_url proxy.type=foreman BOOTIF=01-${net0/mac}',  # noqa
        # Preseed default
        "+   ansible_enabled = plugin_present?('foreman_ansible')",
        "+   additional_packages = ['lsb-release']",
        "+   additional_packages << host_param('additional-packages')",
        "+   additional_packages << 'python' if ansible_enabled",
        "+   additional_packages << 'salt-minion' if salt_enabled",
        '+   additional_packages = additional_packages.join(" ").split().uniq().join(" ")',
        '- d-i pkgsel/include string <%= salt_package %> lsb-release',
        '+ d-i pkgsel/include string <%= additional_packages %>'
        # pxegrub2_discovery
        '+ <% ["efi", ""].each do |suffix| %>',
        "- menuentry 'Foreman Discovery Image' --id discovery {",
        "+ menuentry 'Foreman Discovery Image <%= suffix %>' --id discovery<%= suffix %> {",
        '-   linuxefi boot/fdi-image/vmlinuz0 rootflags=loop root=live:/fdi.iso rootfstype=auto ro rd.live.image acpi=force rd.luks=0 rd.md=0 rd.dm=0 rd.lvm=0 rd.bootif=0 rd.neednet=0 nomodeset proxy.url=<%= foreman_server_url %> proxy.type=foreman BOOTIF=01-$mac',  # noqa
        '+   linux<%= suffix %> boot/fdi-image/vmlinuz0 rootflags=loop root=live:/fdi.iso rootfstype=auto ro rd.live.image acpi=force rd.luks=0 rd.md=0 rd.dm=0 rd.lvm=0 rd.bootif=0 rd.neednet=0 nokaslr nomodeset proxy.url=<%= foreman_server_url %> proxy.type=foreman BOOTIF=01-$mac',  # noqa
        '-   initrdefi boot/fdi-image/initrd0.img',
        '+   initrd<%= suffix %> boot/fdi-image/initrd0.img',
        '+ <% end %>',
        # Kickstart default
        '+ - fips_enabled: boolean (default=false)',
        "- repo --name <%= medium[:name] %> --baseurl <%= medium[:url] %> <%= medium[:install] ? ' --install' : '' %>",  # noqa
        "+ repo --name <%= medium[:name] %> --baseurl <%= medium[:url] %> <%= medium[:install] ? ' --install' : '' %><%= proxy_string %>",  # noqa
        '+ <%= snippet_if_exists(template_name + " custom packages") %>',
        "+ <% if host_param_true?('fips_enabled') -%>",
        "+ <%=   snippet 'fips_packages' %>",
        '+ <% end -%>',
        '+ ',
        '+ <%= snippet_if_exists(template_name + " custom pre") %>',
        '- %post',
        '+ <%#',
        '+ Main post script, if it fails the last post is still executed.',
        '+ %>',
        '+ %post --log=/mnt/sysimage/root/install.post.log',
        '- (',
        '+ <%= snippet_if_exists(template_name + " custom post") %>',
        "+ <%= snippet 'efibootmgr_netboot' %>",
        '+ ',
        '+ touch /tmp/foreman_built',
        '+ <%= section_end -%>',
        '+ ',
        '+ <%#',
        '+ The last post section halts Anaconda to prevent endless loop',
        '+ %>',
        '+ <% if (is_fedora && os_major < 20) || (rhel_compatible && os_major < 7) -%>',
        '+ %post',
        '+ <% else -%>',
        '+ %post --erroronfail',
        '+ <% end -%>',
        '+ if test -f /tmp/foreman_built; then',
        '+   echo "calling home: build is done!"',
        "+   <%= indent(2, skip1: true) { snippet('built', :variables => { :endpoint => 'built', :method => 'POST', :body_file => '/mnt/sysimage/root/install.post.log' }) } -%>",  # noqa
        '+ else',
        '+   echo "calling home: build failed!"',
        "+   <%= indent(2, skip1: true) { snippet('built', :variables => { :endpoint => 'failed', :method => 'POST', :body_file => '/mnt/sysimage/root/install.post.log' }) } -%>",  # noqa
        '+ fi',
        '+ ',
        '- ',
        '- # Inform the build system that we are done.',
        '- echo "Informing Foreman that we are built"',
        "- wget -q -O /dev/null --no-check-certificate <%= foreman_url('built') %>",
        '- ) 2>&1 | tee /root/install.post.log',
        '- exit 0',
        '- ',
        # Kickstart default user data
        "- /usr/bin/curl -o /dev/null -k '<%= foreman_url('built') %>'",
        # Preseed default PXELinux
        '+ ',
        '+ <%= snippet_if_exists(template_name + " custom menu") %>',
        # coreos_cloudconfig
        '+       hostname: <%= @host.name %>',
        #  Discovery Debian kexec
        '-   options = ["nomodeset", "auto=true"]',
        '+   options = ["nomodeset", "nokaslr", "auto=true"]',
        # Kickstart default PXEGrub
        "+   if @host.operatingsystem.name != 'Fedora' && @host.operatingsystem.major.to_i >= 7 && host_param_true?('fips_enabled')",  # noqa
        "+     options.push('fips=1')",
        '+   end',
        '+ ',
        '+ ',
        '+ <%= snippet_if_exists(template_name + " custom menu") %>',
        # Discovery Red Hat kexec
        "+   if @host.operatingsystem.name != 'Fedora' && @host.operatingsystem.major.to_i >= 7 && host_param_true?('fips_enabled')",  # noqa
        "+     options.push('fips=1')",
        '+   end',
        '-   "append": "ks=<%= foreman_url(\'provision\') + "&static=yes" %> inst.ks.sendmac <%= "ip=#{ip}::#{gw}:#{mask}:::none nameserver=#{dns} ksdevice=bootif BOOTIF=#{bootif} nomodeset " + options.compact.join(\' \') %>",',  # noqa
        '+   "append": "ks=<%= foreman_url(\'provision\') + "&static=yes" %> inst.ks.sendmac <%= "ip=#{ip}::#{gw}:#{mask}:::none nameserver=#{dns} ksdevice=bootif BOOTIF=#{bootif} nomodeset nokaslr " + options.compact.join(\' \') %>",',  # noqa
        '-   "append": "ks=<%= foreman_url(\'provision\') + "&static=yes" %> kssendmac nicdelay=5 <%= "ip=#{ip} netmask=#{mask} gateway=#{gw} dns=#{dns} ksdevice=#{mac} BOOTIF=#{bootif} " + options.compact.join(\' \') %>",',  # noqa
        '+   "append": "ks=<%= foreman_url(\'provision\') + "&static=yes" %> kssendmac nicdelay=5 <%= "ip=#{ip} netmask=#{mask} gateway=#{gw} dns=#{dns} ksdevice=#{mac} BOOTIF=#{bootif} nomodeset nokaslr " + options.compact.join(\' \') %>",',  # noqa
        # Kickstart default PXELinux
        "+   if @host.operatingsystem.name != 'Fedora' && @host.operatingsystem.major.to_i >= 7 && host_param_true?('fips_enabled')",  # noqa
        "+     options.push('fips=1')",
        '+   end',
        '+ ',
        '+ ',
        '+ <%= snippet_if_exists(template_name + " custom menu") %>',
        # pxegrub2_chainload
        '-   paths = ["fedora", "redhat", "centos", "debian", "ubuntu", "sles", "opensuse", "Microsoft", "EFI"]',  # noqa
        '+   paths = [',
        "+     '/EFI/fedora/shim.efi',",
        "+     '/EFI/fedora/grubx64.efi',",
        "+     '/EFI/redhat/shim.efi',",
        "+     '/EFI/redhat/grubx64.efi',",
        "+     '/EFI/centos/shim.efi',",
        "+     '/EFI/centos/grubx64.efi',",
        "+     '/EFI/debian/grubx64.efi',",
        "+     '/EFI/ubuntu/grubx64.efi',",
        "+     '/EFI/sles/grubx64.efi',",
        "+     '/EFI/opensuse/grubx64.efi',",
        "+     '/EFI/Microsoft/boot/bootmgfw.efi'",
        '+   ]',
        '+ insmod part_gpt',
        '+ insmod fat',
        '+ insmod chain',
        '+ ',
        "- menuentry 'Chainload Grub2 EFI from ESP' --id local {",
        "+ menuentry 'Chainload Grub2 EFI from ESP' --id local_chain_hd0 {",
        '-   unset root',
        '-   echo Chainloading Grub2 EFI from ESP, available devices:',
        '+   echo Chainloading Grub2 EFI from ESP, enabled devices for booting:',
        '-   echo -n "Probing ESP partition ... "',
        '-   search --file --no-floppy --set=root /EFI/BOOT/BOOTX64.EFI',
        '-   echo found $root',
        '+ <%',
        '+   paths.each do |path|',
        '+ -%>',
        '+   echo "Trying <%= path %> "',
        '+   unset chroot',
        '+   search --file --no-floppy --set=chroot <%= path %>',
        '+   if [ -f ($chroot)<%= path %> ]; then',
        '+     chainloader ($chroot)<%= path %>',
        '+     echo "Found <%= path %> at $chroot, attempting to chainboot it..."',
        '-   sleep 2',
        '+     sleep 2',
        '+     boot',
        '-   if [ -f ($root)/EFI/BOOT/grubx64.efi ]; then',
        '-     chainloader ($root)/EFI/BOOT/grubx64.efi',
        '-   <% paths.each do |path| %>',
        '-   elif [ -f ($root)/EFI/<%= path %>/grubx64.efi ]; then',
        '-     chainloader ($root)/EFI/<%= path %>/grubx64.efi',
        '-   <% end -%>',
        '-   else',
        '-     echo File grubx64.efi not found on ESP.',
        "-     echo Update 'pxegrub2_chainload' paths array with:",
        '-     ls ($root)/EFI',
        '-     echo The system will halt in 2 minutes or',
        '-     echo press ESC to halt immediately.',
        '-     sleep -i 120',
        '-     halt --no-apm',
        '+ <%',
        '+   end',
        '+ -%>',
        '+   echo Partition with known EFI file not found, you may want to drop to grub shell',
        "+   echo and investigate available files updating 'pxegrub2_chainload' template and",
        '+   echo the list of known filepaths for probing. Contents of \\EFI directory:',
        '+   ls ($chroot)/EFI',
        '+   echo The system will halt in 2 minutes or press ESC to halt immediately.',
        '+   sleep -i 120',
        '+   halt --no-apm',
        "- menuentry 'Chainload into BIOS bootloader on first disk' --id local_chain_hd0 {",
        "+ menuentry 'Chainload into BIOS bootloader on first disk' --id local_chain_legacy_hd0 {",
        '+   boot',
        "- menuentry 'Chainload into BIOS bootloader on second disk' --id local_chain_hd1 {",
        "+ menuentry 'Chainload into BIOS bootloader on second disk' --id local_chain_legacy_hd1 {",  # noqa
        '+   boot',
        # Kickstart default PXEGrub2
        "+   if @host.operatingsystem.name != 'Fedora' && @host.operatingsystem.major.to_i >= 7 && host_param_true?('fips_enabled')",  # noqa
        "+     options.push('fips=1')",
        '+   end',
        '+ ',
        '-   # efi grub commands are RHEL7+ only, this prevents "Kernel is too old"',
        '+   # Grub EFI commands are RHEL7+ only (prevents "Kernel is too old") or for non-EFI arch',  # noqa
        "-   if @host.operatingsystem.family == 'Redhat' && major < 7",
        "+   if (@host.operatingsystem.family == 'Redhat' && major < 7) || !@host.pxe_loader.include?('EFI')",  # noqa
        '+ ',
        '+ <%= snippet_if_exists(template_name + " custom menu") %>',
        # PXEGrub2 default local boot
        '+ echo Default PXE local template entry is set to \'<%= global_setting("default_pxe_item_local", "local") %>\'',  # noqa
        '+ <%= snippet "pxegrub2_mac" %>',
        '+ <%= snippet "pxegrub2_discovery" %>',
        # Kickstart oVirt-RHVH
        "+ <%= snippet 'efibootmgr_netboot' %>",
        # puppet_setup
        '-   <%= host_param_true?(\'run-puppet-in-installer\') ? \'\' : \'"--tags no_such_tag",\' %>',  # noqa
        '+   <%= host_param_true?(\'run-puppet-in-installer\') || @full_puppet_run ? \'\' : \'"--tags no_such_tag",\' %>',  # noqa
        '- <%= bin_path %>/puppet agent --config <%= etc_path %>/puppet.conf --onetime <%= host_param_true?(\'run-puppet-in-installer\') ? \'\' : \'--tags no_such_tag\' %> <%= @host.puppetmaster.blank? ? \'\' : "--server #{@host.puppetmaster}" %> --no-daemonize',  # noqa
        '+ <%= bin_path %>/puppet agent --config <%= etc_path %>/puppet.conf --onetime <%= host_param_true?(\'run-puppet-in-installer\') || @full_puppet_run ? \'\' : \'--tags no_such_tag\' %> <%= @host.puppetmaster.blank? ? \'\' : "--server #{@host.puppetmaster}" %> --no-daemonize',  # noqa
        '+ <% end -%>',
        '- <% end -%>',
        # puppet.conf
        "+ <% if host_param_true?('fips_enabled') -%>",
        '+ digest_algorithm = sha256',
        '+ <% end -%>',
        # pxegrub_discovery
        '-   kernel boot/fdi-image/vmlinuz0 rootflags=loop root=live:/fdi.iso rootfstype=auto ro rd.live.image acpi=force rd.luks=0 rd.md=0 rd.dm=0 rd.lvm=0 rd.bootif=0 rd.neednet=0 nomodeset proxy.url=<%= foreman_server_url %> proxy.type=foreman BOOTIF=01-$net_default_mac',  # noqa
        '+   kernel boot/fdi-image/vmlinuz0 rootflags=loop root=live:/fdi.iso rootfstype=auto ro rd.live.image acpi=force rd.luks=0 rd.md=0 rd.dm=0 rd.lvm=0 rd.bootif=0 rd.neednet=0 nokaslr nomodeset proxy.url=<%= foreman_server_url %> proxy.type=foreman BOOTIF=01-$net_default_mac',  # noqa
        # XenServer default finish
        "- /usr/bin/wget --output-document=/dev/null <%= foreman_url('built') %>",
    ],
    'partition-table': [],
    'job-template': [
        # Ansible Roles - Ansible Default
        '-   tasks:',
        '+   pre_tasks:',
        '-         var: foreman_params',
        '+         var: foreman',
        # Run Command - Ansible Default
        '-     - shell: |',
        '+     - shell:',
        '+         cmd: |',
        "- <%=     indent(8) { input('command') } %>",
        "+ <%=       indent(10) { input('command') } %>",
        # Run Command - Ansible Roles
        '-   roles:',
        '- <%- if @host.all_ansible_roles.present? -%>',
        '- <%=   @host.all_ansible_roles.map { |role| "    - #{role.name.strip}" '
        '}.join("\\n") %>',
        '- <%- end -%>',
        '+   tasks:',
        '+     - name: Apply roles',
        '+       include_role:',
        '+         name: "{{ role }}"',
        '+       loop: "{{ foreman_ansible_roles }}"',
        '+       loop_control:',
        '+         loop_var: role',
    ]
}

# Depreciated component entities satellite version wise
_depreciated = {
    '6.4': {
        'settings': [
            'use_pulp_oauth', 'use_gravatar', 'trusted_puppetmaster_hosts', 'force_post_sync_actions']  # noqa
    },
    '6.6': {
        'settings': [
            'remote_execution_without_proxy', 'top_level_ansible_vars']
    },
    '6.7': {
        'settings': ["host_update_lock", "dns_conflict_timeout",
                     "host_group_matchers_inheritance",
                     "ansible_implementation", "puppet_server"]
    },
    '6.8': {
        'settings': ["dynflow_allow_dangerous_actions", "parametrized_classes_in_enc",
                     "enable_smart_variables_in_enc",
                     "default_variables_lookup_path"]
    }

}


def depreciated_attrs_less_component_data(component, attr_data):
    """Removes the depreciated attribute entities of a component from all
    entities of a component attribute

    e.g if some settings are removed in some version then this function removes
    those settings before actual comparision

    :param string component: The component of which the attrs are depreciated
    :param list attr_data: List of component attribute entities
        e.g All the setting names / setting values etc.
    :return list: attr_data with removed depreciated component entities from
        the _depreciated dict
    """
    ver = os.environ.get('TO_VERSION')
    if _depreciated.get(ver):
        if _depreciated[ver].get(component):
            for depr_attr_entity in _depreciated[ver][component]:
                if depr_attr_entity in attr_data:
                    attr_data.remove(depr_attr_entity)
    return attr_data


def assert_varients(component, pre, post):
    """Alternates the result of assert if the value of entity attribute is
    'expected' to change during upgrade

    It takes help from the entity_varients directory above for known changes

    e.g IF filters resource type 'lookupkey' in 6.1 is expected to change to
    'variablelookupkey' when upgraded to 6.2, then
    It returns true to pass the test as its expected

    :param string component: The sat component name of which entity attribute
        values are expected to varied during upgrade
    :param string pre: The preupgrade value of attribute
    :param string post: The postupgrade value of attribute
    :returns bool: Returns True, If the preupgrade and postupgrade values are
        expected changes and listed in entity variants directory.
        Else compares the actual preupgrade and postupgrade values and returns
        True/False accordingly
    """
    if os.environ.get('FROM_VERSION') not in SUPPORTED_SAT_VERSIONS:
        raise VersionError(
            'Unsupported preupgrade version {} provided for '
            'entity variants existence tests'.format(os.environ.get('FROM_VERSION')))

    if os.environ.get('TO_VERSION') not in SUPPORTED_SAT_VERSIONS:
        raise VersionError(
            'Unsupported postupgrade version {} provided for '
            'entity variants existence tests'.format(os.environ.get('TO_VERSION')))

    if component in _entity_varients:
        for single_list in _entity_varients[component]:
            if pre == single_list[SUPPORTED_SAT_VERSIONS.index(os.environ.get('FROM_VERSION'))]:
                if post == single_list[SUPPORTED_SAT_VERSIONS.index(os.environ.get('TO_VERSION'))]:
                    return True
    return pre == post
