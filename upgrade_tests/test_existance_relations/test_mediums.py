"""Upgrade TestSuite for validating Satellite mediums existence
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
component = 'medium'
med_name = compare_postupgrade(component, 'name')


# Tests
@pytest.mark.parametrize("pre,post", med_name, ids=pytest_ids(med_name))
def test_positive_mediums_by_name(pre, post):
    """Test all OS mediums are existing after upgrade by names

    :id: fe7786be-61ea-4276-81c7-6228389c4b84

    :expectedresults: All OS mediums should be retained post upgrade by names
    """
    assert pre == post
