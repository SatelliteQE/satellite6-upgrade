"""Helper functions and variables to test entity existence and associations
post upgrade
"""

import json
import os
import pytest
from upgrade.helpers.tools import csv_reader

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
        'discovery_rule',
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
        'discovery_rule',
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


def _find_on_list_of_dicts(lst, data_key, all_=False):
    """Returns the value of a particular key in a dictionary from the list of
    dictionaries, when 'all' is set to false.

    When 'all' is set to true, returns the list of values of given key from all
    the dictionaries in list.

    :param list lst: A list of dictionaries
    :param str data_key: A key name of which data to be retrieved from given
        list of dictionaries
    :param bool all: Fetches all the values of key in list of dictionaries if
        True, else Fetches only single and first value of a key in list of
        dictionaries
    :returns the list of values or a value of a given data_key depends on
        'all' parameter

    """
    dct_values = [dct.get(data_key) for dct in lst]
    if all_:
        return dct_values
    for v in dct_values:
        if v is not None:
            return v

    raise KeyError(
        'Unable to find data for key \'{0}\' in satellite.'.format(
            data_key))


def _find_on_list_of_dicts_using_search_key(lst_of_dct, search_key, attr):
    """Returns the value of attr key in a dictionary from the list of
    dictionaries with the help of search_key.

    To retrieve the value search key and the attribute should be in the
    same dictionary

    :param list lst_of_dct: A list of dictionaries
    :param str search_key: A value of any unique key in dictionary in list of
        dictionary.
        The value will be used to fetch another keys value from same dictionary
    :param str attr: The key name in dictionary in which search_key exists in
        list of dictionaries
    :returns the value of given attr key from a dictionary where search_key
        exists as value of another key

    """
    for single_dict in lst_of_dct:
        for k, v in single_dict.items():
            if search_key == v:
                return single_dict.get(
                    attr, '{} attribute missing'.format(attr))
    return '{} entity missing'.format(search_key)


def set_datastore(datastore):
    """Creates a file with all the satellite components data in json format

    Here data is a list representation of all satellite component properties
    in format:
    [
    {'c1':[{c1_ent1:'val', 'c1_ent2':'val'}]},
    {'c2':[{c2_ent1:'val', 'c2_ent2':'val'}]}
    ]
    where c1 and c2 are sat components e.g host, capsule, role
    ent1 and ent2 are component properties e.g host ip, capsule name

    :param str datastore: A file name without extension where all sat component
    data will be exported

    Environment Variable:

    ORGANIZATION:
        The organization to which the components are associated
        Optional, by default 'Default_Organization'

    """
    org = os.environ.get('ORGANIZATION', 'Default_Organization')
    nonorged_comps_data = [
        csv_reader(
            component, 'list') for component in components['org_not_required']
    ]
    orged_comps_data = [
        csv_reader(
            component, 'list --organization {}'.format(org)
            ) for component in components['org_required']
    ]
    all_comps_data = nonorged_comps_data + orged_comps_data
    with open('{}'.format(datastore), 'w') as ds:
        json.dump(all_comps_data, ds)


def get_datastore(datastore):
    """Fetches a json type data of all the satellite components from a file

    This file would be exported by set_datastore function in this module

    Here data is a list representation of all satellite component properties
    in format:
    [
    {'c1':[{c1_ent1:'val', 'c1_ent2':'val'}]},
    {'c2':[{c2_ent1:'val', 'c2_ent2':'val'}]}
    ]
    where c1 and c2 are sat components e.g host, capsule, role
    ent1 and ent2 are component properties e.g host ip, capsule name

    :param str datastore: A file name from where all sat component data will
    be imported

    """
    with open('{}'.format(datastore)) as ds:
        return json.load(ds)


def find_datastore(datastore, component, attribute, search_key=None):
    """Returns a particular sat component property attribute or all attribute
    values of component property

    Particular property attribute if search key is provided
    e.g component='host', search_key='1'(which can be id), attribute='ip'
    then, the ip of host with id 1 will be returned

    All property attribute values if search key is not provided
    e.g component='host', attribute='ip'
    then, List of all the ips of all the hosts will be returned

    :param list datastore: The data fetched from get_datastore function in
        this module
    :param str component: The component name of which the property values
        to find
    :param str attribute: The property of sat component of which value to be
        determined
    :param str search_key: The property value as key of sats given components
        property
    :returns str/list: A particular sat component property attribute or list
        of attribute values of component property
    """
    # Lower the keys and attributes
    component = component.lower() if component is not None else component
    search_key = search_key.lower() if search_key is not None else search_key
    attribute = attribute.lower() if attribute is not None else attribute
    # Fetching Process
    comp_data = _find_on_list_of_dicts(datastore, component)
    if isinstance(comp_data, list):
        if (search_key is None) and attribute:
            return _find_on_list_of_dicts(comp_data, attribute, all_=True)
        if all([search_key, attribute]):
            return _find_on_list_of_dicts_using_search_key(
                comp_data, search_key, attribute)


def compare_postupgrade(component, attribute):
    """Returns the given component attribute value from preupgrade and
    postupgrade datastore

    If the attribute is tuple then items in tuple should follow the satellite
    versions order. Like 1st item for 6.1, 2nd for 6.2 and so on.
    e.g ('id','uuid') here 'id' is in 6.1 and 'uuid' in 6.2.

    :param str component: The sat component name of which attribute value to
        fetch from datastore
    :param str/tuple attribute: String if component attribute name is same in
        pre and post upgrade versions. Tuple if component attribute name is
        different in pre and post upgrade versions.
        e.g 'ip' of host (if string)
        e.g ('id','uuid') of subscription (if tuple)
    :returns tuple: The tuple containing two items, first attribute value
        before upgrade and second attribute value of post upgrade
    """
    sat_vers = ['6.1', '6.2']
    from_ver = os.environ.get('FROM_VERSION')
    to_ver = os.environ.get('TO_VERSION')
    if isinstance(attribute, tuple):
        pre_attr = attribute[sat_vers.index(from_ver)]
        post_attr = attribute[sat_vers.index(to_ver)]
    elif isinstance(attribute, str):
        pre_attr = post_attr = attribute
    else:
        raise TypeError('Wrong attribute type provided in test. Please provide'
                        'one of string/tuple.')
    # Getting preupgrade and postupgrade data
    predata = get_datastore('preupgrade')
    postdata = get_datastore('postupgrade')
    entity_values = []
    for test_case in find_datastore(
            predata, component, attribute=attribute_keys[component]):
        preupgrade_entity = find_datastore(
            predata, component, search_key=test_case, attribute=pre_attr)
        postupgrade_entity = find_datastore(
            postdata, component, search_key=test_case, attribute=post_attr)
        if 'missing' in preupgrade_entity or 'missing' in postupgrade_entity:
            culprit = preupgrade_entity if 'missing' in preupgrade_entity \
                else postupgrade_entity
            culprit_ver = ' in preupgrade version' if 'missing' \
                in preupgrade_entity else ' in postupgrade version'
            entity_values.append(
                pytest.mark.xfail(
                    (preupgrade_entity, postupgrade_entity),
                    reason=culprit+culprit_ver))
        else:
            entity_values.append((preupgrade_entity, postupgrade_entity))
    return entity_values


def pytest_ids(data):
    """Generates pytest ids for post upgrade existance tests

    :param list/str data: The list of tests to pytest parametrized function
    """
    if isinstance(data, list):
        ids = ["pre and post" for i in range(len(data))]
    elif isinstance(data, str):
        ids = ["pre and post"]
    else:
        raise TypeError(
            'Wrong data type is provided to generate pytest ids. '
            'Provide one of list/str.')
    return ids
