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
    'compute-resource': [
        ['rhev', 'rhev', 'rhv']],
    'filter': [
        # Resource Type Variants
        ['lookupkey', 'variablelookupkey', 'variablelookupkey'],
        ['(miscellaneous)', 'foremanopenscap::arfreport',
         'foremanopenscap::arfreport'],
        ['organization', 'katello::subscription', 'katello::subscription'],
        ['configtemplate', 'provisioningtemplate', 'provisioningtemplate'],
        # Permissions Variants
        ['view_templates, create_templates, edit_templates, '
         'destroy_templates, deploy_templates',
         'view_provisioning_templates, create_provisioning_templates, '
         'edit_provisioning_templates, destroy_provisioning_templates, '
         'deploy_provisioning_templates',
         'view_provisioning_templates, create_provisioning_templates, '
         'edit_provisioning_templates, destroy_provisioning_templates, '
         'deploy_provisioning_templates'],
        ['viewer', 'viewer', 'customized viewer'],
        ['site manager', 'site manager', 'customized site manager'],
        ['manager', 'manager', 'customized manager'],
        ['discovery reader', 'discovery reader', 'customized discovery reader'], # noqa
        ['discovery manager', 'discovery manager', 'customized discovery manager'], # noqa
        ['compliance viewer', 'compliance viewer', 'customized compliance viewer'], # noqa
        ['compliance manager', 'compliance manager', 'customized compliance manager'], # noqa
        ['anonymous', 'anonymous', 'default role'],
        ['commonparameter', 'commonparameter', 'parameter']],
    'organization': [
        ['default_organization', 'default_organization', 'default organization']], # noqa
    'role': [
        # Role Variants
        ['viewer', 'viewer', 'customized viewer'],
        ['site manager', 'site manager', 'customized site manager'],
        ['manager', 'manager', 'customized manager'],
        ['discovery reader', 'discovery reader', 'customized discovery reader'], # noqa
        ['discovery manager', 'discovery manager', 'customized discovery manager'], # noqa
        ['compliance viewer', 'compliance viewer', 'customized compliance viewer'], # noqa
        ['compliance manager', 'compliance manager', 'customized compliance manager'], # noqa
        ['anonymous', 'anonymous', 'default role']],
    'settings': [
        # Value Variants
        ['immediate', 'immediate', 'on_demand'],
        ['', '', '/etc/pki/katello/certs/katello-apache.crt'],
        ['', '', '/etc/pki/katello/private/katello-apache.key'],
        ['false', 'false', 'true'],
        ['["lo", "usb*", "vnet*", "macvtap*"]',
         '["lo", "usb*", "vnet*", "macvtap*"]',
         '["lo", "usb*", "vnet*", "macvtap*", "_vdsmdummy_", "veth*", '
         '"docker*", "tap*", "qbr*", "qvb*", "qvo*", "qr-*", "qg-*", '
         '"vlinuxbr*", "vovsbr*"]'],
        # Description Variants
        ['fact name to use for primary interface detection and hostname',
         'fact name to use for primary interface detection and hostname',
         'fact name to use for primary interface detection'],
        ['automatically reboot discovered host during provisioning',
         'automatically reboot discovered host during provisioning',
         'automatically reboot or kexec discovered host during provisioning'],
        ['default provisioning template for new atomic operating systems',
         'default provisioning template for new atomic operating systems',
         'default provisioning template for new atomic operating systems '
         'created from synced content'],
        ['default finish template for new operating systems',
         'default finish template for new operating systems',
         'default finish template for new operating systems created '
         'from synced content'],
        ['default ipxe template for new operating systems',
         'default ipxe template for new operating systems',
         'default ipxe template for new operating systems created from '
         'synced content'],
        ['default kexec template for new operating systems',
         'default kexec template for new operating systems',
         'default kexec template for new operating systems created '
         'from synced content'],
        ['default provisioning template for new operating systems',
         'default provisioning template for new operating systems',
         'default provisioning template for operating systems created'
         ' from synced content'],
        ['default partitioning table for new operating systems',
         'default partitioning table for new operating systems',
         'default partitioning table for new operating systems created'
         ' from synced content'],
        ['default pxelinux template for new operating systems',
         'default pxelinux template for new operating systems',
         'default pxelinux template for new operating systems created'
         ' from synced content'],
        ['default user data for new operating systems',
         'default user data for new operating systems',
         'default user data for new operating systems created from '
         'synced content'],
        ['when unregistering host via subscription-manager, also delete '
         'server-side host record',
         'when unregistering host via subscription-manager, also delete'
         ' server-side host record',
         'when unregistering a host via subscription-manager, also delete'
         ' the host record. managed resources linked to host such as virtual'
         ' machines and dns records may also be deleted.'],
        ['private key that foreman will use to encrypt websockets',
         'private key that foreman will use to encrypt websockets',
         'private key file that foreman will use to encrypt websockets']],
    'subscription': [
        # Validity Variants
        ['-1', '-1', 'unlimited']],
}


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
