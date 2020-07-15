"""Unit tests for upgrade test helpers
"""
import os

from upgrade_tests.helpers.variants import assert_varients


def test_67_to_68():
    os.environ['FROM_VERSION'] = '6.7'
    os.environ['TO_VERSION'] = '6.8'
    assert assert_varients('filter', 'lookupkey', 'lookupkey')


def test_67_to_68_no_diff():
    os.environ['FROM_VERSION'] = '6.7'
    os.environ['TO_VERSION'] = '6.8'
    assert assert_varients('filter', 'foo', 'foo')


def test_67_to_68_no_component():
    os.environ['FROM_VERSION'] = '6.7'
    os.environ['TO_VERSION'] = '6.8'
    assert assert_varients('non_exist_component', 'foo', 'foo')
