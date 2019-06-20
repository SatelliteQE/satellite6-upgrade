"""All the variants those changes during upgrade and the helper functions"""

import os


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
        ['puppet, puppet ca, pulp node, templates, discovery, tftp, dns, dhcp, bmc, openscap, dynflow, ssh, ansible']*2, # noqa
        ['tftp, dns, dhcp, puppet, puppet ca, bmc, pulp, discovery, openscap, dynflow, ssh']*3 +  # noqa
        ['tftp, dns, dhcp, puppet, puppet ca, pulp, discovery, bmc, openscap, dynflow, ssh, ansible'] +  # noqa
        ['tftp, dns, dhcp, puppet, puppet ca, pulp, discovery, bmc, openscap, dynflow, ssh, ansible, templates']  # noqa
    ],
    'compute-resource': [
        ['rhev']*2+['rhv']*3],
    'filter': [
        # Resource Type Variants
        ['lookupkey']+['variablelookupkey']*4,
        ['(miscellaneous)']+['foremanopenscap::arfreport']*4,
        ['organization']+['katello::subscription']*4,
        ['configtemplate']+['provisioningtemplate']*4,
        ['authsourceldap']*3+['authsource']*2,
        ['templateinvocation']*3+['(miscellaneous)']*2,
        ['docker/imagesearch']*3+['(miscellaneous)']*2,
        # Permissions Variants
        ['view_templates, create_templates, edit_templates, '
         'destroy_templates, deploy_templates'] +
        ['view_provisioning_templates, create_provisioning_templates, '
         'edit_provisioning_templates, destroy_provisioning_templates, '
         'deploy_provisioning_templates']*4,
        ['viewer']*2+['customized viewer']*3,
        ['site manager']*2+['customized site manager']*3,
        ['manager']*2+['customized manager']*3,
        ['discovery reader']*2+['customized discovery reader']*3,
        ['discovery manager']*2+['customized discovery manager']*3,
        ['compliance viewer']*2+['customized compliance viewer']*3,
        ['compliance manager']*2+['customized compliance manager']*3,
        ['anonymous']*2+['default role']*3,
        ['commonparameter']*2+['parameter']*3,
        ['execute_template_invocation']*3+['']*2,
        ['create_job_invocations, view_job_invocations']*3 +
        ['create_job_invocations, view_job_invocations, cancel_job_invocations']*2, # noqa
        ['execute_template_invocation, filter_autocompletion_for_template_invocation']*3 + # noqa
        ['filter_autocompletion_for_template_invocation, create_template_invocations']*2, # noqa
        ['view_hostgroups, create_hostgroups, edit_hostgroups, destroy_hostgroups']*3 + # noqa
        ['view_hostgroups, create_hostgroups, edit_hostgroups, destroy_hostgroups, play_roles_on_hostgroup']*2, # noqa
        ['view_registries, create_registries, destroy_registries']*3 +
        ['view_registries, create_registries, destroy_registries, search_repository_image_search']*2, # noqa
        ['search_repository_image_search']*3 + ['']*2,
        ['view_gpg_keys, create_gpg_keys, edit_gpg_keys, destroy_gpg_keys']*3 +
        ['view_gpg_keys, create_gpg_keys, edit_gpg_keys, destroy_gpg_keys, view_content_credentials, create_content_credentials, edit_content_credentials, destroy_content_credentials']*2, # noqa
        ['view_subscriptions, attach_subscriptions, unattach_subscriptions, import_manifest, delete_manifest']*3 + # noqa
        ['view_subscriptions, attach_subscriptions, unattach_subscriptions, import_manifest, delete_manifest, manage_subscription_allocations']*2, # noqa
        ['execute_template_invocation, filter_autocompletion_for_template_invocation']*3 + # noqa
        ['filter_autocompletion_for_template_invocation, create_template_invocations, view_template_invocations']*2, # noqa
        ['view_gpg_keys']*3 + ['view_gpg_keys, view_content_credentials']*2,
        ['view_hosts, create_hosts, build_hosts, view_discovered_hosts, provision_discovered_hosts, edit_discovered_hosts, destroy_discovered_hosts, submit_discovered_hosts, auto_provision_discovered_hosts']*3 + # noqa
        ['view_hosts, create_hosts, edit_hosts, build_hosts, view_discovered_hosts, provision_discovered_hosts, edit_discovered_hosts, destroy_discovered_hosts, submit_discovered_hosts, auto_provision_discovered_hosts']*2, # noqa
        ['view_hosts, create_hosts, edit_hosts, destroy_hosts, build_hosts, power_hosts, console_hosts, puppetrun_hosts, ipmi_boot_hosts, view_discovered_hosts, provision_discovered_hosts, edit_discovered_hosts, destroy_discovered_hosts, submit_discovered_hosts, auto_provision_discovered_hosts']*3 + # noqa
        ['view_hosts, create_hosts, edit_hosts, destroy_hosts, build_hosts, power_hosts, console_hosts, puppetrun_hosts, ipmi_boot_hosts, view_discovered_hosts, provision_discovered_hosts, edit_discovered_hosts, destroy_discovered_hosts, submit_discovered_hosts, auto_provision_discovered_hosts, play_roles_on_host']*2 # noqa
    ],
    'organization': [
        ['default_organization']*3+['default organization']*2],  # noqa
    'role': [
        # Role Variants
        ['viewer']*2+['customized viewer']*3,
        ['site manager']*2+['customized site manager']*3,
        ['manager']*2+['customized manager']*3,
        ['discovery reader']*2+['customized discovery reader']*3,  # noqa
        ['discovery manager']*2+['customized discovery manager']*3,  # noqa
        ['compliance viewer']*2+['customized compliance viewer']*3,  # noqa
        ['compliance manager']*2+['customized compliance manager']*3,  # noqa
        ['anonymous']*2+['default role']*3],
    'settings': [
        # Value Variants
        ['immediate']*2+['on_demand']*3,
        ['']*2+['/etc/pki/katello/certs/katello-apache.crt']*3,
        ['']*2+['/etc/pki/katello/private/katello-apache.key']*3,
        ['false']*2+['true']*3,
        ['["lo", "usb*", "vnet*", "macvtap*"]']*2 +
        ['["lo", "usb*", "vnet*", "macvtap*", "_vdsmdummy_", "veth*", '
         '"docker*", "tap*", "qbr*", "qvb*", "qvo*", "qr-*", "qg-*", '
         '"vlinuxbr*", "vovsbr*"]']*2 +
        ['["lo", "en*v*", "usb*", "vnet*", "macvtap*", "_vdsmdummy_", "veth*", "docker*", '
         '"tap*", "qbr*", "qvb*", "qvo*", "qr-*", "qg-*", "vlinuxbr*", "vovsbr*"]'],
        # Description Variants
        ['fact name to use for primary interface detection and hostname']*2 +
         ['fact name to use for primary interface detection']*3,
        ['automatically reboot discovered host during provisioning']*2 +
         ['automatically reboot or kexec discovered host during provisioning']*3,  # noqa
        ['default provisioning template for new atomic operating systems']*2 +
         ['default provisioning template for new atomic operating systems '
         'created from synced content']*3,
        ['default finish template for new operating systems']*2 +
         ['default finish template for new operating systems created '
         'from synced content']*3,
        ['default ipxe template for new operating systems']*2 +
         ['default ipxe template for new operating systems created from '
         'synced content']*3,
        ['default kexec template for new operating systems']*2 +
         ['default kexec template for new operating systems created '
         'from synced content']*3,
        ['default provisioning template for new operating systems']*2 +
         ['default provisioning template for operating systems created'
         ' from synced content']*3,
        ['default partitioning table for new operating systems']*2 +
         ['default partitioning table for new operating systems created'
         ' from synced content']*3,
        ['default pxelinux template for new operating systems']*2 +
         ['default pxelinux template for new operating systems created'
         ' from synced content']*3,
        ['default user data for new operating systems']*2 +
         ['default user data for new operating systems created from '
         'synced content']*3,
        ['when unregistering host via subscription-manager, also delete '
         'server-side host record']*2 +
         ['when unregistering a host via subscription-manager, also delete'
         ' the host record. managed resources linked to host such as virtual'
         ' machines and dns records may also be deleted.']*3,
        ['private key that foreman will use to encrypt websockets']*2 +
         ['private key file that foreman will use to encrypt websockets']*3,
        ['duration in minutes after the puppet interval for servers to be classed as out of sync.']*3 +  # noqa
         ['duration in minutes after servers are classed as out of sync.']*2,
        ['satellite kickstart default user data'] * 3 + ['kickstart default user data']*2,  # noqa
        ['satellite kickstart default'] * 3 + ['kickstart default']*2,
        ['satellite kickstart default finish'] * 3 + ['kickstart default finish']*2,  # noqa
        ['satellite atomic kickstart default'] * 3 + ['atomic kickstart default']*2,  # noqa
        ['default_location'] * 3 + ['default location']*2,
        ['what command should be used to switch to the effective user. one of ["sudo", "su"]']*3 +  # noqa
         ['what command should be used to switch to the effective user. one of ["sudo", "dzdo", "su"]']*2,  # noqa
        ['https://access.redhat.com/blogs/1169563/feed']*4 +
         ['https://www.redhat.com/en/rss/blog/channel/red-hat-satellite']],  # noqa
    'subscription': [
        # Validity Variants
        ['-1']*2+['unlimited']*3],
    'template': [
        # name variants
        ['idm_register']*3+['deprecated idm_register']*2,
        ['satellite atomic kickstart default']*3+['deprecated satellite atomic kickstart default']*2, # noqa
        ['satellite kickstart default']*3+['deprecated satellite kickstart default']*2,  # noqa
        ['satellite kickstart default finish']*3+['deprecated satellite kickstart default finish']*2, # noqa
        ['satellite kickstart default user data']*3+['deprecated satellite kickstart default user data']*2 # noqa
    ]
}

template_varients = {
    'template': [
        # Junos default ZTP config, Junos default finish, Junos default SLAX
        '+ oses:', '+ - Junos',
        # Kickstart default finish
        "+ <% if host_enc['parameters']['realm'] && @host.realm && (@host.realm.realm_type == 'FreeIPA' || @host.realm.realm_type == 'Red Hat Identity Management') -%>",  # noqa
        '+ ',
        '+ <%= snippet "blacklist_kernel_modules" %>',
        "- <% if host_enc['parameters']['realm'] && @host.realm && @host.realm.realm_type == 'FreeIPA' -%>",  # noqa
        # Preseed default finish
        '+ <%= snippet "blacklist_kernel_modules" %>',
        '+ ',
        # WAIK default PXELinux
        '+ oses:',
        '+ - Windows',
        # Atomic Kickstart default
        '+ # Use medium_uri/content/repo/ as the URL if you',
        '+ ostreesetup --nogpg --osname=fedora-atomic --remote=fedora-atomic-ostree --url=<%= fedora_atomic_url %> --ref=fedora-atomic/f<%= @host.os.major %>/<%= @host.architecture %>/docker-host',  # noqa
        '+ ostreesetup --nogpg --osname=centos-atomic-host --remote=centos-atomic-host-ostree --url=<%= host_param_true?(\'atomic-upstream\') ? "http://mirror.centos.org/centos/#{@host.os.major}/atomic/#{@host.architecture}/repo/" : medium_uri %> --ref=centos-atomic-host/<%= @host.os.major %>/<%= @host.architecture %>/standard',  # noqa
        '+ ostreesetup --nogpg --osname=rhel-atomic-host --remote=rhel-atomic-host-ostree --url=file:///install/ostree --ref=rhel-atomic-host/<%= @host.os.major %>/<%= @host.architecture %>/standard',  # noqa
        '+ rm -f /etc/ostree/remotes.d/*.conf',
        '- # Use @host.operatingsystem.medium_uri(@host)}/content/repo/ as the URL if you',
        '- ostreesetup --nogpg --osname=fedora-atomic --remote=fedora-atomic --url=<%= fedora_atomic_url %> --ref=fedora-atomic/f<%= @host.os.major %>/<%= @host.architecture %>/docker-host',  # noqa
        '- ostreesetup --nogpg --osname=centos-atomic-host --remote=centos-atomic-host --url=<%= host_param_true?(\'atomic-upstream\') ? "http://mirror.centos.org/centos/#{@host.os.major}/atomic/#{@host.architecture}/repo/" : @host.operatingsystem.medium_uri(@host) %> --ref=centos-atomic-host/<%= @host.os.major %>/<%= @host.architecture %>/standard',  # noqa
        '- ostreesetup --nogpg --osname=rhel-atomic-host --remote=rhel-atomic-host --url=file:///install/ostree --ref=rhel-atomic-host/<%= @host.os.major %>/<%= @host.architecture %>/standard',  # noqa
        # remote_execution_ssh_keys
        '+ # SSH key is in remote_execution_ssh_keys, you can SSH into a host. This ',
        '+ # works in combination with Remote Execution plugin by querying smart proxies',
        '+ # to build an array.',
        '+ #',
        '+ # To use this snippet without the plugin provide the SSH keys as host parameter',
        '+ # remote_execution_ssh_keys. It expects the same format like the authorized_keys',
        '+ # file.',
        '+ <%= host_param(\'remote_execution_ssh_keys\').is_a?(String) ? host_param(\'remote_execution_ssh_keys\') : host_param(\'remote_execution_ssh_keys\').join("\\n") %>',  # noqa
        '- # SSH key is in remote_execution_ssh_keys, you can SSH into a host. This only',
        '- # works in combination with Remote Execution plugin.',
        '- # The Remote Execution plugin queries smart proxies to build the',
        '- # remote_execution_ssh_keys array which is then made available to this template',
        "- # via the host's parameters. There is currently no way of supplying this",
        '- # parameter manually.',
        '- # See http://projects.theforeman.org/issues/16107 for details.',
        '- <%= host_param(\'remote_execution_ssh_keys\').join("\\n") %>',
        # kickstart_ifcfg_generic_interface
        '- <%- if @interface.virtual? && ((!@subnet.nil? && @subnet.has_vlanid?) || @interface.vlanid.present?) -%>',  # noqa
        '+ <%- if @interface.virtual? && (!@subnet.nil? && (@subnet.has_vlanid? || @interface.vlanid.present?)) -%>',  # noqa
        # Preseed default PXEGrub2
        '+   ',
        '+   # send PXELinux "IPAPPEND 2" option along',
        '+   options.push("BOOTIF=01-$net_default_mac")',
        '+ ',
        # redhat_register
        '+ #   redhat_install_host_tools = [true|false]    Install the katello-host-tools yum/dnf plugins.',  # noqa
        '+ #',
        '+ #   redhat_install_host_tracer_tools = [true|false]  Install the katello-host-tools Tracer yum/dnf plugin.',  # noqa
        '+ #',
        '+ #',
        '+ #   syspurpose_role                             Sets the system purpose role',
        '+ #',
        '+ #   syspurpose_usage                            Sets the system purpose usage',
        '+ #',
        '+ #   syspurpose_sla                              Sets the system purpose SLA',
        '+ #',
        '+ #   syspurpose_addons                           Sets the system purpose add-ons. Separate multiple',  # noqa
        '+ #                                               values with commas.',
        '+       redhat_install_host_tools = true',
        '+       redhat_install_host_tracer_tools = false',
        "+       redhat_install_host_tools = host_param_true?('redhat_install_host_tools')",
        "+       redhat_install_host_tracer_tools = host_param_true?('redhat_install_host_tracer_tools')",  # noqa
        '+     fi',
        '+   <% end %>',
        '+ ',
        "+   <%- if (host_param('syspurpose_role') || host_param('syspurpose_usage') || host_param('syspurpose_sla') || host_param('syspurpose_addons')) %>",  # noqa
        '+     <%- if !atomic %>',
        '+       if [ -f /usr/bin/dnf ]; then',
        '+         dnf -y install subscription-manager-syspurpose',
        '+       else',
        '+         yum -t -y install subscription-manager-syspurpose',
        '+       fi',
        '+     <%- end %>',
        '+ ',
        '+     if [ -f /usr/sbin/syspurpose ]; then',
        "+       <%- if host_param('syspurpose_role') %>",
        '+         syspurpose set-role "<%= host_param(\'syspurpose_role\') %>"',
        '+       <%- end %>',
        "+       <%- if host_param('syspurpose_usage') %>",
        '+         syspurpose set-usage "<%= host_param(\'syspurpose_usage\') %>"',
        '+       <%- end %>',
        "+       <%- if host_param('syspurpose_sla') %>",
        '+         syspurpose set-sla "<%= host_param(\'syspurpose_sla\') %>"',
        '+       <%- end %>',
        "+       <%- if host_param('syspurpose_addons') %>",
        "+         <%- addons = host_param('syspurpose_addons').split(',')",
        '+               .map { |add_on| "\'#{add_on.strip}\'" }.join(" ") %>',
        '+         syspurpose add-addons <%= addons %>',
        '+       <%- end %>',
        '+     else',
        '+       echo "Syspurpose CLI not found."',
        '+   <% if !atomic %>',
        '+     <% if redhat_install_agent || redhat_install_host_tools || redhat_install_host_tracer_tools %>',  # noqa
        '+        if [ -f /usr/bin/dnf ]; then',
        '+          PACKAGE_MAN="dnf -y"',
        '+        else',
        '+          PACKAGE_MAN="yum -t -y"',
        '+        fi',
        '+     <% end %>',
        '+     <% if redhat_install_agent %>',
        '+       $PACKAGE_MAN install katello-agent',
        '+     <% elsif redhat_install_host_tools %>',
        '+       $PACKAGE_MAN install katello-host-tools',
        '+     <% end %>',
        '+ ',
        '+     <% if redhat_install_host_tracer_tools %>',
        '+       $PACKAGE_MAN install katello-host-tools-tracer',
        '+     <% end %>',
        '-   <% if redhat_install_agent && !atomic %>',
        '-     if [ -f /usr/bin/dnf ]; then',
        '-       dnf -y install katello-agent',
        '-     else',
        '-       yum -t -y install katello-agent',
        '-     fi',
        '-     chkconfig goferd on',
        # AutoYaST default user data
        '+ <%= snippet "blacklist_kernel_modules" %>',
        '+ ',
        # Kickstart default iPXE
        "+ <% stage2 = host_param('kickstart_liveimg') ? 'inst.stage2=' + @host.operatingsystem.medium_uri(@host).to_s : '' %>",  # noqa
        '+ ',
        '- kernel <%= "#{@host.url_for_boot(:kernel)}" %> initrd=initrd.img ks=<%= foreman_url(\'provision\')%><%= static %> ksdevice=<%= @host.mac %> network kssendmac ks.sendmac inst.ks.sendmac ip=${netX/ip} netmask=${netX/netmask} gateway=${netX/gateway} dns=${dns}',  # noqa
        '+ kernel <%= "#{@host.url_for_boot(:kernel)}" %> initrd=initrd.img ks=<%= foreman_url(\'provision\')%> inst.stage2=<%= @host.operatingsystem.medium_uri(@host) %> <%= stage2 %> <%= static %> ksdevice=<%= @host.mac %> network kssendmac ks.sendmac inst.ks.sendmac ip=${netX/ip} netmask=${netX/netmask} gateway=${netX/gateway} dns=${dns}',  # noqa
        # AutoYaST SLES default
        '+ <%= snippet "blacklist_kernel_modules" %>',
        '+ ',
        # Preseed default iPXE
        '- <% boot_files_uris = @host.operatingsystem.boot_files_uri(@host.medium,@host.architecture) -%>',  # noqa
        '+ <% boot_files_uris = @host.operatingsystem.boot_files_uri(medium_provider) -%>',
        # AutoYaST default
        '+ <%= snippet "blacklist_kernel_modules" %>',
        '+ ',
        # Boot disk iPXE - host
        '- echo Cannot find interface with MAC <%= interface.mac %>',
        '+ echo Cannot find interface with MAC <%= interface.mac %>, spawning shell',
        '+ shell',
        '- sleep 30',
        # Preseed default user data
        '+ <%= snippet "blacklist_kernel_modules" %>',
        '+ ',
        # Preseed default
        '+ <% @additional_media.each do |medium| -%>',
        '+ d-i apt-setup/local<%= repos %>/repository string <%= medium[:url] %> <%= @host.operatingsystem.release_name %>-<%= medium[:name] %> main',  # noqa
        '+ <%= "d-i apt-setup/local#{repos}/comment string #{medium[:comment]}" if medium[:comment] %>',  # noqa
        '+ <%= "d-i apt-setup/local#{repos}/key string #{medium[:gpgkey]}" if medium[:gpgkey] %>',
        '+ <% repos +=1 -%>',
        '+ <% end -%>',
        '+ ',
        # PXELinux default local boot
        '+ MENU TITLE Booting local disk (ESC to stop)',
        '- PROMPT 0',
        '- MENU TITLE PXE Menu',
        '- TOTALTIMEOUT 6000',
        '- ONTIMEOUT <%= global_setting("default_pxe_item_local", "local_chain_hd0") %>',
        '+ DEFAULT <%= global_setting("default_pxe_item_local", "local_chain_hd0") %>',
        # Kickstart default
        '+ #   redhat_install_host_tools = [true|false]    Install the katello-host-tools yum/dnf plugins.',  # noqa
        '+ #',
        '+ #   redhat_install_host_tracer_tools = [true|false]  Install the katello-host-tools Tracer yum/dnf plugin.',  # noqa
        '+ #',
        '+ #',
        '+ #   syspurpose_role                             Sets the system purpose role',
        '+ #',
        '+ #   syspurpose_usage                            Sets the system purpose usage',
        '+ #',
        '+ #   syspurpose_sla                              Sets the system purpose SLA',
        '+ #',
        '+ #   syspurpose_addons                           Sets the system purpose add-ons. Separate multiple',  # noqa
        '+ #                                               values with commas.',
        '+       redhat_install_host_tools = true',
        '+       redhat_install_host_tracer_tools = false',
        "+       redhat_install_host_tools = host_param_true?('redhat_install_host_tools')",
        "+       redhat_install_host_tracer_tools = host_param_true?('redhat_install_host_tracer_tools')",  # noqa
        '+     fi',
        '+   <% end %>',
        '+ ',
        "+   <%- if (host_param('syspurpose_role') || host_param('syspurpose_usage') || host_param('syspurpose_sla') || host_param('syspurpose_addons')) %>",  # noqa
        '+     <%- if !atomic %>',
        '+       if [ -f /usr/bin/dnf ]; then',
        '+         dnf -y install subscription-manager-syspurpose',
        '+       else',
        '+         yum -t -y install subscription-manager-syspurpose',
        '+       fi',
        '+     <%- end %>',
        '+ ',
        '+     if [ -f /usr/sbin/syspurpose ]; then',
        "+       <%- if host_param('syspurpose_role') %>",
        '+         syspurpose set-role "<%= host_param(\'syspurpose_role\') %>"',
        '+       <%- end %>',
        "+       <%- if host_param('syspurpose_usage') %>",
        '+         syspurpose set-usage "<%= host_param(\'syspurpose_usage\') %>"',
        '+       <%- end %>',
        "+       <%- if host_param('syspurpose_sla') %>",
        '+         syspurpose set-sla "<%= host_param(\'syspurpose_sla\') %>"',
        '+       <%- end %>',
        "+       <%- if host_param('syspurpose_addons') %>",
        "+         <%- addons = host_param('syspurpose_addons').split(',')",
        '+               .map { |add_on| "\'#{add_on.strip}\'" }.join(" ") %>',
        '+         syspurpose add-addons <%= addons %>',
        '+       <%- end %>',
        '+     else',
        '+       echo "Syspurpose CLI not found."',
        '+   <% if !atomic %>',
        '+     <% if redhat_install_agent || redhat_install_host_tools || redhat_install_host_tracer_tools %>',  # noqa
        '+        if [ -f /usr/bin/dnf ]; then',
        '+          PACKAGE_MAN="dnf -y"',
        '+        else',
        '+          PACKAGE_MAN="yum -t -y"',
        '+        fi',
        '+     <% end %>',
        '+     <% if redhat_install_agent %>',
        '+       $PACKAGE_MAN install katello-agent',
        '+     <% elsif redhat_install_host_tools %>',
        '+       $PACKAGE_MAN install katello-host-tools',
        '+     <% end %>',
        '+ ',
        '+     <% if redhat_install_host_tracer_tools %>',
        '+       $PACKAGE_MAN install katello-host-tools-tracer',
        '+     <% end %>',
        '+ - use-ntp: boolean (default depends on OS release)',
        "+   is_fedora = @host.operatingsystem.name == 'Fedora'",
        '+   os_minor = @host.operatingsystem.minor.to_i',
        "+   use_ntp = host_param_true?('use-ntp') || (is_fedora && os_major < 16) || (rhel_compatible && os_major <= 7)",  # noqa
        '+ <% if (is_fedora && os_major < 29) || (rhel_compatible && os_major <= 7) -%>',
        '+ <%',
        "+ if host_param('kickstart_liveimg')",
        "+   img_name = host_param('kickstart_liveimg')",
        "+   liveimg_url = if host_param('kt_activation_keys')",
        "+     repository_url(img_name, 'isos')",
        '+     if img_name.match(%r|^([\\w\\-\\+]+)://|)',
        '+       img_name',
        '+       "#{@host.operatingsystem.medium_uri(@host)}/#{img_name}"',
        '+     end',
        '+ %>',
        '+ liveimg --url=<%= liveimg_url %> <%= proxy_string %>',
        "+ repo --name <%= medium[:name] %> --baseurl <%= medium[:url] %> <%= medium[:install] ? ' --install' : '' %>",  # noqa
        '+ <% if (is_fedora && os_major >= 28) || (rhel_compatible && os_major > 7) -%>',
        "+ authselect --useshadow --passalgo=<%= @host.operatingsystem.password_hash.downcase || 'sha256' %> --kickstart",  # noqa
        "+ authconfig --useshadow --passalgo=<%= @host.operatingsystem.password_hash.downcase || 'sha256' %> --kickstart",  # noqa
        '+ <% if use_ntp -%>',
        '+ timezone --utc <%= host_param(\'time-zone\') || \'UTC\' %> <%= host_param(\'ntp-server\') ? "--ntpservers #{host_param(\'ntp-server\')}" : \'\' %>',  # noqa
        "+ <% if @host.operatingsystem.name == 'OracleLinux' && os_major == 7 && os_minor < 5 -%>",  # noqa
        "+ <% if @host.operatingsystem.name == 'Fedora' && os_major <= 16 -%>",
        '-   <% if redhat_install_agent && !atomic %>',
        '+ bootloader --append="<%= host_param(\'bootloader-append\') || \'nofb quiet splash=quiet\' %> <%= ks_console %>" <%= @grub_pass %>',  # noqa
        '+ bootloader --location=mbr --append="<%= host_param(\'bootloader-append\') || \'nofb quiet splash=quiet\' %>" <%= @grub_pass %>',  # noqa
        '+ <% if use_ntp -%>',
        '+ chrony',
        '+ echo "Updating system time"',
        '+ <% if use_ntp -%>',
        '+ /usr/bin/chronyc makestep',
        "- <% if host_param('kickstart_liveimg') %>",
        "- liveimg --url=<%= host_param('kickstart_liveimg') %> <%= proxy_string %>",
        "- authconfig --useshadow --passalgo=<%= @host.operatingsystem.password_hash || 'sha256' %> --kickstart",  # noqa
        "- <% if @host.operatingsystem.name == 'OracleLinux' && os_major == 7 -%>",
        "- <% if @host.operatingsystem.name == 'Fedora' and os_major <= 16 -%>",
        '- bootloader --append="<%= host_param(\'bootloader-append\') || \'nofb quiet splash=quiet\' %> <%=ks_console%>" <%= grub_pass %>',  # noqa
        '- bootloader --location=mbr --append="<%= host_param(\'bootloader-append\') || \'nofb quiet splash=quiet\' %>" <%= grub_pass %>',  # noqa
        '- #update local time',
        '- echo "updating system time"',
        '-     if [ -f /usr/bin/dnf ]; then',
        '-       dnf -y install katello-agent',
        '-     else',
        '-       yum -t -y install katello-agent',
        '-     fi',
        '-     chkconfig goferd on',
        # Kickstart default user data
        "- <% if host_enc['parameters']['realm'] && @host.realm && @host.realm.realm_type == 'FreeIPA' -%>",  # noqa
        "+ <% if host_enc['parameters']['realm'] && @host.realm && (@host.realm.realm_type == 'FreeIPA' || @host.realm.realm_type == 'Red Hat Identity Management') -%>",  # noqa
        '+ ',
        '+ <%= snippet "blacklist_kernel_modules" %>',
        #  '- name: Debian kexec',
        #  '+ name: Discovery Debian kexec',
        '+ name: Discovery Debian kexec',
        '+   options = ["nomodeset", "auto=true"]',
        "+   options << @host.facts['append']",
        '+   options << "inst.stage2=#{@host.operatingsystem.medium_uri(@host)}" if @host.operatingsystem.name.match(/Atomic/i)',  # noqa
        '+   "kernel": "<%= @kernel_uri %>",',
        '+   "initram": "<%= @initrd_uri %>",',
        '+   "append": "url=<%= foreman_url(\'provision\') + "&static=yes" %> interface=<%= mac %> netcfg/get_ipaddress=<%= ip %> netcfg/get_netmask=<%= mask %> netcfg/get_gateway=<%= gw %> netcfg/get_nameservers=<%= dns %> netcfg/disable_dhcp=true netcfg/get_hostname=<%= @host.name %> BOOTIF=<%= bootif %> <%= options.compact.join(\' \') %>",',  # noqa
        '- name: Debian kexec',
        "-   append = @host.facts['append']",
        '-   options = ["auto=true"]',
        '-   "comment": "WARNING: Both kernel and initram are not set in preview mode due to http://projects.theforeman.org/issues/19737",',  # noqa
        '-   "kernel": "<%= @kexec_kernel %>",',
        '-   "initram": "<%= @kexec_initrd %>",',
        '-   "append": "url=<%= foreman_url(\'provision\') + "&static=yes" %> interface=<%= mac %> netcfg/get_ipaddress=<%= ip %> netcfg/get_netmask=<%= mask %> netcfg/get_gateway=<%= gw %> netcfg/get_nameservers=<%= dns %> netcfg/disable_dhcp=true netcfg/get_hostname=<%= @host.name %> BOOTIF=<%= bootif %> <%= options.join(\' \') %>",',  # noqa
        '-   "append": "url=<%= foreman_url(\'provision\') + "&static=yes" %> interface=<%= mac %> netcfg/get_ipaddress=<%= ip %> netcfg/get_netmask=<%= mask %> netcfg/get_gateway=<%= gw %> netcfg/get_nameservers=<%= dns %> netcfg/disable_dhcp=true netcfg/get_hostname=<%= @host.name %> BOOTIF=<%= bootif %> <%= options.join(\' \') %>",-     options.push("inst.repo=#{@host.operatingsystem.medium_uri(@host)}")',  # noqa
        # Kickstart default PXEGrub
        '-     options.push("inst.repo=#{@host.operatingsystem.medium_uri(@host)}")',
        '+     options.push("inst.repo=#{medium_uri}")',
        "-   if host_param('blacklist')",
        '-     options.push("modprobe.blacklist=" + host_param(\'blacklist\').gsub(\' \', \'\'))',
        "+   if @host.operatingsystem.name.match(/Atomic/i) || host_param('kickstart_liveimg')",
        "+     options.push('inst.stage2=' + @host.operatingsystem.medium_uri(@host).to_s)",
        # Jumpstart default PXEGrub
        '+ oses:',
        '+ - Solaris',
        # - name: Red Hat kexec',
        #  '+ name: Discovery Red Hat kexec'
        '+ name: Discovery Red Hat kexec',
        '+   options = ["nomodeset"]',
        "+   options << @host.facts['append']",
        '+   options << "inst.stage2=#{@host.operatingsystem.medium_uri(@host)}" if @host.operatingsystem.name.match(/Atomic/i)',  # noqa
        '+   "kernel": "<%= @kernel_uri %>",',
        '+   "initram": "<%= @initrd_uri %>",',
        '+   "append": "ks=<%= foreman_url(\'provision\') + "&static=yes" %> inst.ks.sendmac <%= "ip=#{ip}::#{gw}:#{mask}:::none nameserver=#{dns} ksdevice=bootif BOOTIF=#{bootif} nomodeset " + options.compact.join(\' \') %>",',  # noqa
        '+   "append": "ks=<%= foreman_url(\'provision\') + "&static=yes" %> kssendmac nicdelay=5 <%= "ip=#{ip} netmask=#{mask} gateway=#{gw} dns=#{dns} ksdevice=#{mac} BOOTIF=#{bootif} " + options.compact.join(\' \') %>",',  # noqa
        '- name: Red Hat kexec',
        "-   append = @host.facts['append']",
        '-   "comment": "WARNING: Both kernel and initram are not set in preview mode due to http://projects.theforeman.org/issues/19737",',  # noqa
        '-   "kernel": "<%= @kexec_kernel %>",',
        '-   "initram": "<%= @kexec_initrd %>",',
        '-   "append": "ks=<%= foreman_url(\'provision\') + "&static=yes" %> inst.ks.sendmac <%= "ip=#{ip}::#{gw}:#{mask}:::none nameserver=#{dns} ksdevice=bootif BOOTIF=#{bootif} nomodeset #{append}" %>",',  # noqa
        '-   "append": "ks=<%= foreman_url(\'provision\') + "&static=yes" %> kssendmac nicdelay=5 <%= "ip=#{ip} netmask=#{mask} gateway=#{gw} dns=#{dns} ksdevice=#{mac} BOOTIF=#{bootif} nomodeset #{append}" %>",',  # noqa
        '-   "append": "ks=<%= foreman_url(\'provision\') + "&static=yes" %> kssendmac nicdelay=5 <%= "ip=#{ip} netmask=#{mask} gateway=#{gw} dns=#{dns} ksdevice=#{mac} BOOTIF=#{bootif} nomodeset #{append}" %>",+     options.push("inst.repo=#{medium_uri}")',  # noqa
        # Kickstart default PXELinux
        '+     options.push("inst.repo=#{medium_uri}")',
        '+ ',
        "+   if @host.operatingsystem.name.match(/Atomic/i) || host_param('kickstart_liveimg')",
        "+     options.push('inst.stage2=' + @host.operatingsystem.medium_uri(@host).to_s)",
        "+   timeout = host_param('loader_timeout').to_i * 10",
        '+   timeout = 100 if timeout.nil? || timeout <= 0',
        '+ DEFAULT menu',
        '+ MENU TITLE Booting into OS installer (ESC to stop)',
        '+ TIMEOUT <%= timeout %>',
        '+ ONTIMEOUT installer',
        '+ LABEL installer',
        '+   MENU LABEL <%= template_name %>',
        '- LABEL <%= template_name %>',
        '-     options.push("inst.repo=#{@host.operatingsystem.medium_uri(@host)}")',
        '-   ',
        "-   if host_param('blacklist')",
        '-     options.push("modprobe.blacklist=" + host_param(\'blacklist\').gsub(\' \', \'\'))',
        "- TIMEOUT <%= host_param('loader_timeout') || 10 %>",
        '- DEFAULT <%= template_name %>',
        # ansible_provisioning_callback
        '- (crontab -u root -l 2>/dev/null; echo "@reboot /root/ansible_provisioning_call.sh" ) | crontab -u root -',  # noqa
        '+ (chmod +x /root/ansible_provisioning_call.sh; crontab -u root -l 2>/dev/null; echo "@reboot /root/ansible_provisioning_call.sh" ) | crontab -u root -',  # noqa
        # pxegrub2_chainload
        '-   paths = ["fedora", "redhat", "centos", "debian", "ubuntu", "Microsoft", "EFI"]',
        '+   paths = ["fedora", "redhat", "centos", "debian", "ubuntu", "sles", "opensuse", "Microsoft", "EFI"]',  # noqa
        # AutoYaST default iPXE
        '- <% boot_files_uris = @host.operatingsystem.boot_files_uri(@host.medium,@host.architecture) -%>',  # noqa
        '+ <% boot_files_uris = @host.operatingsystem.boot_files_uri(medium_provider) -%>',
        "- kernel <%= kernel %> initrd=initrd.img splash=silent install=<%=@host.os.medium_uri(@host)%> autoyast=<%= foreman_url('provision') %> text-mode=1 useDHCP=1",  # noqa
        "+ kernel <%= kernel %> initrd=initrd.img splash=silent install=<%= medium_uri %> autoyast=<%= foreman_url('provision') %> text-mode=1 useDHCP=1",  # noqa
        # Kickstart default PXEGrub2
        '+     options.push("inst.repo=#{medium_uri}")',
        "+   if @host.operatingsystem.name.match(/Atomic/i) || host_param('kickstart_liveimg')",
        "+     options.push('inst.stage2=' + @host.operatingsystem.medium_uri(@host).to_s)",
        '+   # send PXELinux "IPAPPEND 2" option along',
        '+   options.push("BOOTIF=01-$net_default_mac")',
        '+ ',
        '+ ',
        '+   # efi grub commands are RHEL7+ only, this prevents "Kernel is too old"',
        "+   if @host.operatingsystem.family == 'Redhat' && major < 7",
        '+     linuxcmd = "linux"',
        '+     initrdcmd = "initrd"',
        '+   else',
        '+     linuxcmd = "linuxefi"',
        '+     initrdcmd = "initrdefi"',
        '+   end',
        "+   <%= linuxcmd %> <%= @kernel %> ks=<%= foreman_url('provision') %> <%= pxe_kernel_options %> <%= ksoptions %>",  # noqa
        '+   <%= initrdcmd %> <%= @initrd %>',
        '-     options.push("inst.repo=#{@host.operatingsystem.medium_uri(@host)}")',
        "-   if host_param('blacklist')",
        '-     options.push("modprobe.blacklist=" + host_param(\'blacklist\').gsub(\' \', \'\'))',
        "-   linuxefi <%= @kernel %> ks=<%= foreman_url('provision') %> <%= pxe_kernel_options %> <%= ksoptions %>",  # noqa
        '-   initrdefi <%= @initrd %>',
        # Alterator default PXELinux
        '-     mediumpath  = os.mediumpath @host',
        '+     mediumpath  = os.mediumpath(medium_provider)',
        # Jumpstart default finish, Jumpstart default
        '+ oses:',
        '+ - Solaris',
        # preseed_networking_setup
        '+ <% host_subnet = @host.subnet -%>',
        '+ <% host_dhcp = host_subnet.nil? ? false : host_subnet.dhcp_boot_mode? -%>',
        '+ <% host_subnet6 = @host.subnet6 -%>',
        '+ <% host_dhcp6 = host_subnet6.nil? ? false : host_subnet6.dhcp_boot_mode? -%>',
        "+ iface $real inet <%= host_dhcp ? 'dhcp' : 'static' %>",
        '+ <% unless host_dhcp -%>',
        '+     gateway <%= host_subnet.gateway %>',
        '+     netmask <%= host_subnet.mask %>',
        '+     dns-nameservers <%= host_subnet.dns_primary %> <%= host_subnet.dns_secondary %>',
        '+ <% end -%>',
        '+ <% if @host.ip6 && host_subnet6 && !host_dhcp6 -%>',
        '+ iface $real inet6 static',
        '+     address <%= @host.ip6 %>/<%= host_subnet6.cidr %>',
        '+ <% if host_subnet6.gateway -%>',
        '+     gateway <%= host_subnet6.gateway %>',
        '+ <% end -%>',
        '+ <% end -%>',
        '+ <% @host.managed_interfaces.each do |interface| -%>',
        '+ <% interface_subnet = interface.subnet -%>',
        '+ <% interface_dhcp = interface_subnet.nil? ? false : interface_subnet.dhcp_boot_mode? -%>',  # noqa
        '+ <% interface_subnet6 = interface.subnet6 -%>',
        '+ <% interface_dhcp6 = interface_subnet6.nil? ? false : interface_subnet6.dhcp_boot_mode? -%>',  # noqa
        '+ <% next if !interface.managed? || (interface_subnet.nil? && interface_subnet6.nil?) || interface.primary -%>',  # noqa
        "+ real=`ip -o link | awk '/<%= interface.mac -%>/ {print $2;}' | sed s/:$//`",
        '+ <% if interface_subnet %>',
        "+ iface $real inet <%= interface_dhcp ? 'dhcp' : 'static' %>",
        '+ <% unless interface_dhcp -%>',
        '+     netmask <%= interface_subnet.mask %>',
        '+ <% end -%>',
        '+ <% end -%>',
        '+ <% if interface.ip6 && interface_subnet6 %>',
        '+ <% unless interface_dhcp6 -%>',
        '+ iface $real inet6 static',
        '+     address <%= interface.ip6 %>/<%= interface_subnet6.cidr %>',
        '+ <% if interface_subnet6.gateway -%>',
        '+     gateway <%= interface_subnet6.gateway %>',
        '+ <% end -%>',
        '+ <% end -%>',
        '+ <% end -%>',
        '- <% subnet = @host.subnet -%>',
        '- <% dhcp = subnet.dhcp_boot_mode? -%>',
        "- iface $real inet <%= dhcp ? 'dhcp' : 'static' %>",
        '- <% unless dhcp -%>',
        '-     gateway <%= @host.subnet.gateway  %>',
        '-     netmask <%= @host.subnet.mask  %>',
        '-     dns-nameservers <%= @host.subnet.dns_primary %> <%= @host.subnet.dns_secondary %>',
        '- <% end %>',
        '- <% @host.managed_interfaces.each do |interface| %>',
        '- <% next if !interface.managed? || interface.subnet.nil? || interface.primary -%>',
        '- <% subnet = interface.subnet -%>',
        '- <% dhcp = subnet.nil? ? false : subnet.dhcp_boot_mode? -%>',
        "- real=`ip -o link | awk '/<%= interface.mac -%>/ {print $2;}' | sed s/:$//`",
        "- iface $real inet <%= dhcp ? 'dhcp' : 'static' %>",
        '- <% unless dhcp -%>',
        '-     netmask <%= subnet.mask %>',
        '- <% end %>',
        # Kickstart oVirt-RHVH PXELinux
        '- APPEND initrd=<%= @initrd %> inst.ks=<%= foreman_url("provision") %> inst.stage2=<%= @host.operatingsystem.medium_uri(@host) %> local_boot_trigger=<%= foreman_url("built") %> intel_iommu=on',  # noqa
        '+ APPEND initrd=<%= @initrd %> inst.ks=<%= foreman_url("provision") %> inst.stage2=<%= medium_uri %> local_boot_trigger=<%= foreman_url("built") %> intel_iommu=on',  # noqa
        # Kickstart oVirt-RHVH
        '-   liveimg_url = "#{@host.operatingsystem.medium_uri(@host)}/#{liveimg_name}"',
        '+   liveimg_url = "#{medium_uri}/#{liveimg_name}"',
        # puppet_setup
        '+ <% if @host.puppetca_token.present? -%>',
        "+ <% if os_family == 'Windows' -%>",
        '+ $csr_attributes = @("<%= snippet \'csr_attributes.yaml\' %>".Replace("`n","`r`n"))',
        '+ Out-File -FilePath <%= etc_path %>\\csr_attributes.yaml -InputObject $csr_attributes',
        '+ <% else -%>',
        '+ cat > <%= etc_path %>/csr_attributes.yaml << EOF',
        "+ <%= snippet 'csr_attributes.yaml' %>",
        '+ EOF',
        '+ <% end -%>',
        '+ <% end -%>',
        '+ ',
        # PXELinux global default
        '+ MENU TITLE Booting unknown host (ESC to stop)',
        '- PROMPT 0',
        '- MENU TITLE PXE Menu',
        '- TIMEOUT 200',
        '+ TIMEOUT 5',
        # Boot disk iPXE - generic host
        '+ echo Failed to chainload from any network interface, fallback to static.',
        '+ ifstat',
        '+ echo -n Enter interface name to boot from (e.g. net0):  && read interface',
        '+ isset ${${interface}/mac} && goto get_static_ip',
        '+ echo Interface ${interface} is not initialized, try again',
        '+ goto no_nic',
        '+ ',
        '+ :get_static_ip',
        '+ ifopen ${interface}',
        '+ echo Please enter IP details for ${interface}',
        '+ echo',
        '+ echo -n IP address      :  && read ${interface}/ip',
        '+ echo -n Subnet mask     :  && read ${interface}/netmask',
        '+ echo -n Default gateway :  && read ${interface}/gateway',
        '+ echo -n DNS server      :  && read dns',
        '+ chain <%= url %>${${interface}/mac} || goto boot_failure',
        '+ exit 0',
        '+ ',
        '+ :boot_failure',
        '+ echo Cannot continue, spawning shell',
        '+ shell',
        '- echo Failed to chainload from any network interface',
        '- sleep 30',
        '- exit 1'
    ],
    'partition-table': [
        # Jumpstart Mirrored # Jumpstart default
        '+ oses:', '+ - Solaris',
        # Junos default fake
        '+ oses:', '+ - Junos'
    ],
    'job-template': [
        # Name: Power Action - Ansible Default
        "+         echo <%= input('action') %> host && sleep 3",
        # Power Action - SSH Default
        "-         'reboot'", "+         'shutdown -r +1'",
        # Service Action - SSH Default
        '+   <% case input("action")', "+   when 'enable' %>",
        '+ chkconfig --add <%= input("service") %>', "+   <% when 'disable' %>",
        '+ chkconfig --del <%= input("service") %>', '+   <% else %>', '+   <% end %>',
        # Restart Services - Katello SSH Default
        '+ <%',
        "+ commands = input(:helper).split(',').map { |split| split.strip }",
        "+ reboot = commands.delete('reboot')",
        '+ -%>',
        '+ <%= commands.join("\\n") %>',
        '+ <% if reboot -%>',
        "+ <%= render_template('Power Action - SSH Default', action: 'restart') %>",
        '+ <% end %>',
        '- <%= input(:helper).split(",").map {|split| "#{split}" }.join("\\n") %>',
        '- ',
        # Restart Services - Katello Ansible Default
        '+ <%',
        "+ commands = input(:helper).split(',').map { |split| split.strip }",
        "+ reboot = commands.delete('reboot')",
        '+ -%>',
        "+     'Run Command - Ansible Default',",
        '+     :command => (commands.push(\'katello-tracer-upload\')).join("\\n")',
        '+ <% if reboot %>',
        '+     - reboot:',
        '+ <% end %>',
        "-   'Run Command - Ansible Default',",
        '-   :command => "#{input(:helper)},katello-tracer-upload".split(\',\').map {|split| "#{split}" }.join("\\n")',  # noqa
        #
        "+   supported_families = ['Redhat', 'Debian', 'Suse']",
        '+   action = input("action")',
        '+ ',
        "+   if @host.operatingsystem.family == 'Redhat'",
        "+     package_manager = 'yum'",
        "+   elsif @host.operatingsystem.family == 'Debian'",
        "+     package_manager = 'apt'",
        "+   elsif @host.operatingsystem.family == 'Suse'",
        "+     package_manager = 'zypper'",
        '+   end',
        '+ -%>',
        '+ #!/bin/bash',
        '+ exit_with_message () {',
        "+ <% if package_manager == 'yum' -%>",
        '+   yum -y <%= action %> <%= input("package") %>',
        "+ <% elsif package_manager == 'apt' -%>",
        '+   <%-',
        "+     action = 'install' if action == 'group install'",
        "+     action = 'remove' if action == 'group remove'",
        "+     if action == 'group update' || action == 'update'",
        "+       if input('package').blank?",
        "+         action = 'upgrade'",
        '+       else',
        "+         action = '--only-upgrade install'",
        '+       end',
        '+     end',
        '+   -%>',
        '+   apt-get -y update',
        '+   apt-get -y <%= action %> <%= input("package") %>',
        "+ <% elsif package_manager == 'zypper' -%>",
        '+   <%-',
        '+     if action == "group install"',
        '+       action = "install -t pattern"',
        '+     elsif action == "group remove"',
        '+       action = "remove -t pattern"',
        '+     end',
        '+   -%>',
        '+   zypper -n <%= action %> <%= input("package") %>',
        "-   supported_families = ['Redhat', 'Debian']",
        '- %>',
        '- function exit_with_message() {',
        "- <% if @host.operatingsystem.family == 'Redhat' -%>",
        '-   yum -y <%= input("action") %> <%= input("package") %>',
        "- <% elsif @host.operatingsystem.family == 'Debian' -%>",
        '-   apt-get -y <%= input("action") %> <%= input("package") %>']
}

# Depreciated component entities satellite version wise
_depreciated = {
    '6.4': {
        'settings': [
            'use_pulp_oauth', 'use_gravatar', 'trusted_puppetmaster_hosts', 'force_post_sync_actions']  # noqa
    },
    '6.5': {
        'settings': [
            'modulepath', 'legacy_puppet_hostname']
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
    supported_versions = ['6.1', '6.2', '6.3', '6.4', '6.5']
    from_version = os.environ.get('FROM_VERSION')
    to_version = os.environ.get('TO_VERSION')
    if from_version not in supported_versions:
        raise VersionError(
            'Unsupported preupgrade version {} provided for '
            'entity variants existence tests'.format(from_version))

    if to_version not in supported_versions:
        raise VersionError(
            'Unsupported postupgrade version {} provided for '
            'entity variants existence tests'.format(to_version))

    if component in _entity_varients:
        for single_list in _entity_varients[component]:
            if pre == single_list[supported_versions.index(from_version)]:
                if post == single_list[supported_versions.index(to_version)]:
                    return True
    return pre == post
