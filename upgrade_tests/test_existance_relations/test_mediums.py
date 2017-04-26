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
from upgrade_tests.helpers.existence import compare_postupgrade


@pytest.mark.parametrize(
    "pre,post",
    compare_postupgrade('medium', 'name')
)
def test_positive_mediums_by_name(pre, post):
    """Test all OS mediums are existing after upgrade by names

    :id: fe7786be-61ea-4276-81c7-6228389c4b84

    :expectedresults: All OS mediums should be retained post upgrade by names
    """
    assert pre == post
