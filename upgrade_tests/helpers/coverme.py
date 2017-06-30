"""Unit tests for upgrade test helpers
"""

import os
from upgrade_tests.helpers.variants import assert_varients


def test_61_to_62():
    os.environ['FROM_VERSION'] = '6.1'
    os.environ['TO_VERSION'] = '6.2'
    assert assert_varients('filter', 'lookupkey', 'variablelookupkey')


def test_61_to_62_no_diff():
    os.environ['FROM_VERSION'] = '6.1'
    os.environ['TO_VERSION'] = '6.2'
    assert assert_varients('filter', 'foo', 'foo')


def test_61_to_62_no_component():
    os.environ['FROM_VERSION'] = '6.1'
    os.environ['TO_VERSION'] = '6.2'
    assert assert_varients('non_exist_component', 'foo', 'foo')
