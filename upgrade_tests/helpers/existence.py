"""Helper functions and variables to test entity existence and associations
post upgrade
"""
import csv
import json
import os

from automation_tools.satellite6.hammer import (
    hammer,
    set_hammer_config
)
from fabric.api import execute
from nailgun.config import ServerConfig
from upgrade.helpers.tools import get_setup_data
from upgrade_tests.helpers.constants import api_const, cli_const
from upgrade_tests.helpers.variants import (
    depreciated_attrs_less_component_data
)


class IncorrectEndpointException(Exception):
    """Raise exception on wrong or No endpoint provided"""


def csv_reader(component, subcommand):
    """
    Reads all component entities data using hammer csv output and returns the
    dict representation of all the entities.

    Representation: {component_name:
    [{comp1_name:comp1, comp1_id:1}, {comp2_name:comp2, comp2_ip:192.168.0.1}]
    }
    e.g:
    {'host':[{name:host1.ab.com, id:10}, {name:host2.xz.com, ip:192.168.0.1}]}

    :param string component: Satellite component name. e.g host, capsule
    :param string subcommand: subcommand for above component. e.g list, info
    :returns dict: The dict repr of hammer csv output of given command
    """
    comp_dict = {}
    entity_list = []
    sat_host = get_setup_data()['sat_host']
    set_hammer_config()
    data = execute(
        hammer, '{0} {1}'.format(component, subcommand), 'csv', host=sat_host
    )[sat_host]
    csv_read = csv.DictReader(data.lower().split('\n'))
    for row in csv_read:
        entity_list.append(row)
    comp_dict[component] = entity_list
    return comp_dict


def set_api_server_config(user=None, passwd=None, verify=None):
    """Sets ServerConfig configuration required by nailgun to read entities

    :param str user: The web username of satellite user
        'admin' by default if not provided
    :param str passwd: The web password of satellite user
        'changeme' by default if not provided
    :param bool verify: The ssl verification to connect to satellite host
        False by default if not provided
    """
    sat_host = get_setup_data()['sat_host']
    auth = (
        'admin' if not user else user,
        'changeme' if not passwd else passwd
    )
    url = 'https://{}'.format(sat_host)
    verify = False if not verify else verify
    ServerConfig(auth=auth, url=url, verify=verify).save()


def api_reader(component):
    """Reads each entity data of all components using nailgun helpers and returns
    the dict representation of all the entities

    Representation: {component_name:
    [{comp1_name:comp1, comp1_id:1},
     {comp2_name:comp2, comp2_networks:[
            {'id':1, name:'abc','type':'ipv4'},
            {'id':18, name:'xyz','type':'ipv6'}]
        }]
    }

    e.g:
    {'host':
    [{name:host1.ab.com, id:10},
     {name:host2.xz.com, networks:[
            {'id':1, name:'abc','type':'ipv4'},
            {'id':18, name:'xyz','type':'ipv6'}]
        }]
     }

    :param string component: Satellite component name. e.g host, capsule
    :returns dict: The dict repr of entities data of all components
    """
    comp_data = {}
    comp_entity_data = []
    comp_entity_list = api_const.api_components()[component][0].search_json()
    for unique_id in comp_entity_list['results']:
        single_entity_info = api_const.api_components(
            unique_id['id']
        )[component][1].read_json()
        comp_entity_data.append(single_entity_info)
    comp_data[component] = comp_entity_data
    return comp_data


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


def _find_on_list_of_dicts_using_search_criteria(
        lst_of_dct, search_criteria, attr):
    """Returns the value of attr key in a dictionary from the list of
    dictionaries with the help of search_critria.

    To retrieve the value search key and the attribute should be in the
    same dictionary

    :param list lst_of_dct: A list of dictionaries
    :param dict search_criteria: A dictionary contains the search criteria
        where key is the attribute and value is that attribute value. This dict
        will be used to fetch another key values from list of dictionaries.
    :param str attr: The key name in dictionary in which search_key exists in
        list of dictionaries
    :returns the value of given attr key from a dictionary where search_key
        exists as value of another key

    """
    search_key = search_criteria.keys()[0]
    search_value = search_criteria.values()[0]
    for single_dict in lst_of_dct:
        for key, value in single_dict.items():
            if search_value == str(value) and key == search_key:
                return single_dict.get(
                    attr,
                    '{0} attribute missing for {1} : {2}'.format(
                        attr, search_key, search_value)
                )
    return '{0} : {1} entity missing'.format(search_key, search_value)


def set_datastore(datastore, endpoint):
    """Creates an endpoint file with all the satellite components data in json
    format

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
    :param str endpoint: An endpoints of satellite to get the data and create
    datastore. It has to be either cli or api.

    Environment Variable:

    ORGANIZATION:
        The organization to which the components are associated, if endpoint
        is CLI
        Optional, by default 'Default_Organization'

    """
    allowed_ends = ['cli', 'api']
    if endpoint not in allowed_ends:
        raise IncorrectEndpointException(
            'Endpoints has to be one of {}'.format(allowed_ends))
    if endpoint == 'cli':
        nonorged_comps_data = [
            csv_reader(
                component, 'list') for component in cli_const.components[
                'org_not_required']]
        orged_comps_data = [
            csv_reader(
                component, 'list --organization-id 1'
                ) for component in cli_const.components['org_required']
        ]
        all_comps_data = nonorged_comps_data + orged_comps_data
    if endpoint == 'api':
        set_api_server_config()
        api_comps = api_const.api_components().keys()
        all_comps_data = [
            api_reader(component) for component in api_comps
        ]
    with open('{0}_{1}'.format(datastore, endpoint), 'w') as ds:
        json.dump(all_comps_data, ds)


def get_datastore(datastore, endpoint):
    """Fetches a json type data of all the satellite components from an
    endpoint file

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
    :param str endpoint: An endpoint of satellite to select the correct
        datastore file. It has to be either cli or api.
    """
    allowed_ends = ['cli', 'api']
    if endpoint not in allowed_ends:
        raise IncorrectEndpointException(
            'Endpoints has to be one of {}'.format(allowed_ends))
    with open('{0}_{1}'.format(datastore, endpoint)) as ds:
        return json.load(ds)


def find_datastore(datastore, component, attribute, search_criteria=None):
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
    attribute = attribute.lower() if attribute is not None else attribute
    # Fetching Process
    comp_data = _find_on_list_of_dicts(datastore, component)
    if isinstance(comp_data, list):
        if (search_criteria is None) and attribute:
            attr_entities = _find_on_list_of_dicts(
                comp_data, attribute, all_=True)
            return depreciated_attrs_less_component_data(
                component, attr_entities)
        if all([search_criteria, attribute]):
            return _find_on_list_of_dicts_using_search_criteria(
                comp_data, search_criteria, attribute)


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
    sat_vers = ['6.1', '6.2', '6.3', '6.4']
    from_ver = os.environ.get('FROM_VERSION')
    to_ver = os.environ.get('TO_VERSION')
    endpoint = os.environ.get('ENDPOINT')
    if isinstance(attribute, tuple):
        pre_attr = attribute[sat_vers.index(from_ver)]
        post_attr = attribute[sat_vers.index(to_ver)]
    elif isinstance(attribute, str):
        pre_attr = post_attr = attribute
    else:
        raise TypeError('Wrong attribute type provided in test. '
                        'Please provide one of string/tuple.')
    # Getting preupgrade and postupgrade data
    predata = get_datastore('preupgrade', endpoint)
    postdata = get_datastore('postupgrade', endpoint)
    entity_values = []
    atr = 'id' if endpoint == 'api' else cli_const.attribute_keys[component]
    for test_case in find_datastore(predata, component, atr):
        preupgrade_entity = find_datastore(
            predata,
            component,
            search_criteria={atr: str(test_case)},
            attribute=pre_attr)
        postupgrade_entity = find_datastore(
            postdata,
            component,
            search_criteria={atr: str(test_case)},
            attribute=post_attr
        )
        if 'missing' in str(preupgrade_entity) or 'missing' in str(postupgrade_entity): # noqa
            culprit = preupgrade_entity if 'missing' in preupgrade_entity \
                else postupgrade_entity
            culprit_ver = ' in preupgrade version' if 'missing' \
                in preupgrade_entity else ' in postupgrade version'
            entity_values.append((culprit, culprit_ver))
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
