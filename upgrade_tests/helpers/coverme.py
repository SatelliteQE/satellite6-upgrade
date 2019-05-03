"""Unit tests for upgrade test helpers
"""

import os
from upgrade_tests.helpers.variants import assert_varients


def test_64_to_65():
    os.environ['FROM_VERSION'] = '6.4'
    os.environ['TO_VERSION'] = '6.5'
    assert assert_varients('filter', 'lookupkey', 'lookupkey')


def test_64_to_65_no_diff():
    os.environ['FROM_VERSION'] = '6.4'
    os.environ['TO_VERSION'] = '6.5'
    assert assert_varients('filter', 'foo', 'foo')


def test_64_to_65_no_component():
    os.environ['FROM_VERSION'] = '6.4'
    os.environ['TO_VERSION'] = '6.5'
    assert assert_varients('non_exist_component', 'foo', 'foo')
