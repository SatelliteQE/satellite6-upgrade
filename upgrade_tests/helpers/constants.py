"""API and CLI upgrade Tests Constants"""
import os

from nailgun import entities

# FAKE REPOS
FAKE_REPO_ZOO3 = 'http://inecas.fedorapeople.org/fakerepos/zoo3/'
to_version = os.environ.get('TO_VERSION')


class cli_const:
    """The constants required to run CLI tests"""
    # Components for which the post upgrade existence will be validated,
    # org_not_required - The components where org is not required to get the
    # data about
    # org_required - The components where org is required to get the data about
    components = {
        'org_not_required':
        [
            'architecture',
            'capsule',
            'compute-resource',
            'discovery',
            'discovery-rule' if to_version in [
                '6.3', '6.4'] else 'discovery_rule',
            'domain',
            'environment',
            'filter',
            'host',
            'hostgroup',
            'medium',
            'organization',
            'os',
            'partition-table',
            'puppet-class',
            'puppet-module',
            'role',
            'sc-param',
            'settings',
            'smart-variable',
            'subnet',
            'user',
            'template',
            'user-group'
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
        ]
    }

    # Attributes where 'id' as key to fetch component property data
    attribute_keys = dict.fromkeys(
        [
            'activation-key',
            'architecture',
            'capsule',
            'content-host',
            'compute-resource',
            'discovery',
            'discovery-rule' if to_version in [
                '6.3', '6.4'] else 'discovery_rule',
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
            'puppet-class',
            'puppet-module',
            'repository',
            'role',
            'sc-param',
            'smart-variable',
            'subnet',
            'subscription',
            'sync-plan',
            'template',
            'user',
            'user-group'
        ],
        'id'
     )

    # Attributes where 'name' as key to fetch component property data
    attribute_keys.update(dict.fromkeys(
        [
            'partition-table',
            'product',
            'settings'
        ],
        'name'
     ))
    # Attributes with different or specific keys to fetch properties data
    # e.g for content-view there is content view id' and not 'id'
    attribute_keys['content-view'] = 'content view id'


class api_const:
    """The constants required to run API tests"""
    @classmethod
    def api_components(cls, id=None):
        """Components for which the post upgrade existence will be
        validated from API end

        :param str id: The id of an entity to get its data
        :returns dict: The dict of entities, where each key is component name
            and value is a list. In list the first item will be used to get
            list of a component entities and second will be used to get
            particular component entity data
        """
        api_comps = {
            'domain': [entities.Domain(), entities.Domain(id=id)],
            'subnet': [entities.Subnet(), entities.Subnet(id=id)],
            'contentview': [
                entities.ContentView(), entities.ContentView(id=id)]
        }
        return api_comps
