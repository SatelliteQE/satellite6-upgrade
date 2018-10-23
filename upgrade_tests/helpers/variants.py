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
        ['puppet, puppet ca, pulp node, templates, discovery, tftp, dns, dhcp, bmc, openscap, dynflow, ssh, ansible'], # noqa
        ['tftp, dns, dhcp, puppet, puppet ca, bmc, pulp, discovery, openscap, dynflow, ssh']*3 + # noqa
        ['tftp, dns, dhcp, puppet, puppet ca, pulp, discovery, bmc, openscap, dynflow, ssh, ansible'] # noqa
    ],
    'compute-resource': [
        ['rhev']*2+['rhv']*2],
    'filter': [
        # Resource Type Variants
        ['lookupkey']+['variablelookupkey']*3,
        ['(miscellaneous)']+['foremanopenscap::arfreport']*3,
        ['organization']+['katello::subscription']*3,
        ['configtemplate']+['provisioningtemplate']*3,
        ['authsourceldap']*3+['authsource'],
        ['templateinvocation']*3+['(miscellaneous)'],
        ['docker/imagesearch']*3+['(miscellaneous)'],
        # Permissions Variants
        ['view_templates, create_templates, edit_templates, '
         'destroy_templates, deploy_templates'] +
        ['view_provisioning_templates, create_provisioning_templates, '
         'edit_provisioning_templates, destroy_provisioning_templates, '
         'deploy_provisioning_templates']*3,
        ['viewer']*2+['customized viewer']*2,
        ['site manager']*2+['customized site manager']*2,
        ['manager']*2+['customized manager']*2,
        ['discovery reader']*2+['customized discovery reader']*2,
        ['discovery manager']*2+['customized discovery manager']*2,
        ['compliance viewer']*2+['customized compliance viewer']*2,
        ['compliance manager']*2+['customized compliance manager']*2,
        ['anonymous']*2+['default role']*2,
        ['commonparameter']*2+['parameter']*2,
        ['execute_template_invocation']*3+[''],
        ['create_job_invocations, view_job_invocations']*3 +
        ['create_job_invocations, view_job_invocations, cancel_job_invocations'], # noqa
        ['execute_template_invocation, filter_autocompletion_for_template_invocation']*3 + # noqa
        ['filter_autocompletion_for_template_invocation, create_template_invocations'], # noqa
        ['view_hostgroups, create_hostgroups, edit_hostgroups, destroy_hostgroups']*3 + # noqa
        ['view_hostgroups, create_hostgroups, edit_hostgroups, destroy_hostgroups, play_roles_on_hostgroup'], # noqa
        ['view_registries, create_registries, destroy_registries']*3 +
        ['view_registries, create_registries, destroy_registries, search_repository_image_search'], # noqa
        ['search_repository_image_search']*3 + [''],
        ['view_gpg_keys, create_gpg_keys, edit_gpg_keys, destroy_gpg_keys']*3 +
        ['view_gpg_keys, create_gpg_keys, edit_gpg_keys, destroy_gpg_keys, view_content_credentials, create_content_credentials, edit_content_credentials, destroy_content_credentials'], # noqa
        ['view_subscriptions, attach_subscriptions, unattach_subscriptions, import_manifest, delete_manifest']*3 + # noqa
        ['view_subscriptions, attach_subscriptions, unattach_subscriptions, import_manifest, delete_manifest, manage_subscription_allocations'], # noqa
        ['execute_template_invocation, filter_autocompletion_for_template_invocation']*3 + # noqa
        ['filter_autocompletion_for_template_invocation, create_template_invocations, view_template_invocations'], # noqa
        ['view_gpg_keys']*3 + ['view_gpg_keys, view_content_credentials'],
        ['view_hosts, create_hosts, build_hosts, view_discovered_hosts, provision_discovered_hosts, edit_discovered_hosts, destroy_discovered_hosts, submit_discovered_hosts, auto_provision_discovered_hosts']*3 + # noqa
        ['view_hosts, create_hosts, edit_hosts, build_hosts, view_discovered_hosts, provision_discovered_hosts, edit_discovered_hosts, destroy_discovered_hosts, submit_discovered_hosts, auto_provision_discovered_hosts'], # noqa
        ['view_hosts, create_hosts, edit_hosts, destroy_hosts, build_hosts, power_hosts, console_hosts, puppetrun_hosts, ipmi_boot_hosts, view_discovered_hosts, provision_discovered_hosts, edit_discovered_hosts, destroy_discovered_hosts, submit_discovered_hosts, auto_provision_discovered_hosts']*3 + # noqa
        ['view_hosts, create_hosts, edit_hosts, destroy_hosts, build_hosts, power_hosts, console_hosts, puppetrun_hosts, ipmi_boot_hosts, view_discovered_hosts, provision_discovered_hosts, edit_discovered_hosts, destroy_discovered_hosts, submit_discovered_hosts, auto_provision_discovered_hosts, play_roles_on_host'] # noqa
    ],
    'organization': [
        ['default_organization']*3+['default organization']],  # noqa
    'role': [
        # Role Variants
        ['viewer']*2+['customized viewer']*2,
        ['site manager']*2+['customized site manager']*2,
        ['manager']*2+['customized manager']*2,
        ['discovery reader']*2+['customized discovery reader']*2,  # noqa
        ['discovery manager']*2+['customized discovery manager']*2,  # noqa
        ['compliance viewer']*2+['customized compliance viewer']*2,  # noqa
        ['compliance manager']*2+['customized compliance manager']*2,  # noqa
        ['anonymous']*2+['default role']*2],
    'settings': [
        # Value Variants
        ['immediate']*2+['on_demand']*2,
        ['']*2+['/etc/pki/katello/certs/katello-apache.crt']*2,
        ['']*2+['/etc/pki/katello/private/katello-apache.key']*2,
        ['false']*2+['true']*2,
        ['["lo", "usb*", "vnet*", "macvtap*"]']*2 +
        ['["lo", "usb*", "vnet*", "macvtap*", "_vdsmdummy_", "veth*", '
         '"docker*", "tap*", "qbr*", "qvb*", "qvo*", "qr-*", "qg-*", '
         '"vlinuxbr*", "vovsbr*"]']*2,
        # Description Variants
        ['fact name to use for primary interface detection and hostname']*2 +
         ['fact name to use for primary interface detection']*2,
        ['automatically reboot discovered host during provisioning']*2 +
         ['automatically reboot or kexec discovered host during provisioning']*2,  # noqa
        ['default provisioning template for new atomic operating systems']*2 +
         ['default provisioning template for new atomic operating systems '
         'created from synced content']*2,
        ['default finish template for new operating systems']*2 +
         ['default finish template for new operating systems created '
         'from synced content']*2,
        ['default ipxe template for new operating systems']*2 +
         ['default ipxe template for new operating systems created from '
         'synced content']*2,
        ['default kexec template for new operating systems']*2 +
         ['default kexec template for new operating systems created '
         'from synced content']*2,
        ['default provisioning template for new operating systems']*2 +
         ['default provisioning template for operating systems created'
         ' from synced content']*2,
        ['default partitioning table for new operating systems']*2 +
         ['default partitioning table for new operating systems created'
         ' from synced content']*2,
        ['default pxelinux template for new operating systems']*2 +
         ['default pxelinux template for new operating systems created'
         ' from synced content']*2,
        ['default user data for new operating systems']*2 +
         ['default user data for new operating systems created from '
         'synced content']*2,
        ['when unregistering host via subscription-manager, also delete '
         'server-side host record']*2 +
         ['when unregistering a host via subscription-manager, also delete'
         ' the host record. managed resources linked to host such as virtual'
         ' machines and dns records may also be deleted.']*2,
        ['private key that foreman will use to encrypt websockets']*2 +
         ['private key file that foreman will use to encrypt websockets']*2,
        ['duration in minutes after the puppet interval for servers to be classed as out of sync.']*3 +  # noqa
         ['duration in minutes after servers are classed as out of sync.'],
        ['satellite kickstart default user data'] * 3 + ['kickstart default user data'],  # noqa
        ['satellite kickstart default'] * 3 + ['kickstart default'],
        ['satellite kickstart default finish'] * 3 + ['kickstart default finish'],  # noqa
        ['satellite atomic kickstart default'] * 3 + ['atomic kickstart default'],  # noqa
        ['default_location'] * 3 + ['default location'],
        ['what command should be used to switch to the effective user. one of ["sudo", "su"]']*3 +  # noqa
         ['what command should be used to switch to the effective user. one of ["sudo", "dzdo", "su"]']],  # noqa
    'subscription': [
        # Validity Variants
        ['-1']*2+['unlimited']*2],
    'template': [
        # name variants
        ['idm_register']*3+['deprecated idm_register'],
        ['satellite atomic kickstart default']*3+['deprecated satellite atomic kickstart default'], # noqa
        ['satellite kickstart default']*3+['deprecated satellite kickstart default'],  # noqa
        ['satellite kickstart default finish']*3+['deprecated satellite kickstart default finish'], # noqa
        ['satellite kickstart default user data']*3+['deprecated satellite kickstart default user data'] # noqa
    ]
}

# Depreciated component entities satellite version wise
_depreciated = {
    '6.4': {
        'settings': [
            'use_pulp_oauth', 'use_gravatar', 'trusted_puppetmaster_hosts', 'force_post_sync_actions']  # noqa
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
    supported_versions = ['6.1', '6.2', '6.3', '6.4']
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
