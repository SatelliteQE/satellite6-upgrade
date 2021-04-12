"""API and CLI upgrade Tests Constants"""
from nailgun import entities

from upgrade.helpers import settings

# FAKE REPOS
FAKE_REPO_ZOO3 = 'http://inecas.fedorapeople.org/fakerepos/zoo3/'
FROM_VERSION = os.environ.get('FROM_VERSION')
TO_VERSION = os.environ.get('TO_VERSION')
SUPPORTED_SAT_VERSIONS = ['6.7', '6.8', '6.9', '6.10']
ALLOWED_ENDS = ['cli', 'api']

to_version = settings.upgrade.to_version

CLI_COMPONENTS = {
    'org_not_required':
        [
            'architecture',
            'capsule',
            'compute-resource',
            'discovery',
            'discovery-rule' if to_version is not None and float(to_version) >= 6.3
            else 'discovery_rule',
            'domain',
            'puppet-environment' if to_version is not None and float(to_version) >= 6.7
            else 'environment',
            'filter',
            'host',
            'hostgroup',
            'medium',
            'organization',
            'os',
            'partition-table',
            'policy',
            'puppet-class',
            'puppet-module',
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
        'discovery-rule' if to_version is not None and float(to_version) >= 6.3
        else 'discovery_rule',
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
        'puppet-module',
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
        'settings'
    ],
    'name')
)

CLI_ATTRIBUTES_KEY["content-view"] = 'content view id'

# This lambda function is used to create the constant file for API component
# The id for an entity to get its data

API_COMPONENTS = (lambda id=None: {
    'domain': [entities.Domain(), entities.Domain(id=id)],
    'subnet': [entities.Subnet(), entities.Subnet(id=id)],
    'contentview': [entities.ContentView(), entities.ContentView(id=id)]
})
