"""API and CLI upgrade Tests Constants"""
from nailgun import entities

from upgrade.helpers import nailgun_conf
from upgrade.helpers import settings

to_version = settings.upgrade.to_version

CLI_COMPONENTS = {
    'org_not_required':
        [
            'architecture',
            'capsule',
            'compute-resource',
            'discovery',
            'discovery-rule',
            'domain',
            'puppet-environment',
            'filter',
            'host',
            'hostgroup',
            'medium',
            'organization',
            'os',
            'partition-table',
            'policy',
            'puppet-class',
            'remote-execution-feature',
            'role',
            'sc-param',
            'settings',
            'smart-variable',
            'subnet',
            'user',
            'template',
            'user-group',
            'virt-who-config'
        ],
        'org_required':
        [
            'activation-key',
            'content-view',
            'content-host',
            'gpg',
            'lifecycle-environment',
            'product',
            'repository',
            'subscription',
            'sync-plan'
        ]}


CLI_ATTRIBUTES_KEY = dict.fromkeys(
    [
        'activation-key',
        'architecture',
        'capsule',
        'content-host',
        'compute-resource',
        'discovery',
        'discovery-rule',
        'domain',
        'environment',
        'filter',
        'gpg',
        'host',
        'hostgroup',
        'lifecycle-environment',
        'medium',
        'organization',
        'os',
        'policy',
        'puppet-class',
        'puppet-environment',
        'remote-execution-feature',
        'repository',
        'role',
        'sc-param',
        'smart-variable',
        'subnet',
        'subscription',
        'sync-plan',
        'template',
        'user',
        'user-group',
        'virt-who-config'], 'id'
)

CLI_ATTRIBUTES_KEY.update(dict.fromkeys(
    [
        'partition-table',
        'product',
        'settings',
    ],
    'name')
)

CLI_ATTRIBUTES_KEY["content-view"] = 'content view id'

# This lambda function is used to create the constant file for API component
# The id for an entity to get its data

API_COMPONENTS = (lambda id=None: {
    'domain': [entities.Domain(nailgun_conf), entities.Domain(nailgun_conf, id=id)],
    'subnet': [entities.Subnet(nailgun_conf), entities.Subnet(nailgun_conf, id=id)],
    'contentview': [entities.ContentView(nailgun_conf), entities.ContentView(nailgun_conf, id=id)]
})
