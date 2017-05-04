"""Upgrade TestSuite for validating Satellite roles existence post upgrade

:Requirement: Upgraded Satellite

:CaseAutomation: Automated

:CaseLevel: Acceptance

:CaseComponent: CLI

:TestType: NonFunctional

:CaseImportance: High

:Upstream: No
"""
import pytest
from upgrade_tests.helpers.existence import compare_postupgrade, pytest_ids

# Required Data
component = 'role'
role_name = compare_postupgrade(component, 'name')


# Tests
@pytest.mark.parametrize("pre,post", role_name, ids=pytest_ids(role_name))
def test_positive_roles_by_name(pre, post):
    """Test all roles are existing post upgrade by their name

    :id: 0ee07ffb-ae2b-4b98-ad0a-5a0db568fc1e

    :expectedresults: All roles should be retained post upgrade
    """
    assert pre == post
