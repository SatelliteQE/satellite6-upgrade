"""Upgrade TestSuite for validating Satellite auser groups existence
post upgrade

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
component = 'user-group'
ug_name = compare_postupgrade(component, 'name')


# Tests
@pytest.mark.parametrize("pre,post", ug_name, ids=pytest_ids(ug_name))
def test_positive_usergroups_by_name(pre, post):
    """Test all usergroups are existing after upgrade by names

    :id: 62e8bbca-25f5-403c-b868-7f0bc11ff341

    :expectedresults: All user groups should be retained post upgrade by names
    """
    assert pre == post
