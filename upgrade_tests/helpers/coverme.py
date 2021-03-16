"""Unit tests for upgrade test helpers
"""
from upgrade_tests.helpers.variants import assert_varients
FROM_VERSION = '6.8'
TO_VERSION = '6.9'


def test_67_to_68():
    assert assert_varients('filter', 'lookupkey', 'lookupkey')


def test_67_to_68_no_diff():
    assert assert_varients('filter', 'foo', 'foo')


def test_67_to_68_no_component():
    assert assert_varients('non_exist_component', 'foo', 'foo')
