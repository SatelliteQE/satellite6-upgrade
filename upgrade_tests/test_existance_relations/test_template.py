"""Upgrade TestSuite for validating Satellite provisioning templates existence
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
    compare_postupgrade('template', 'name')
)
def test_positive_templates_by_name(pre, post):
    """Test all templates are existing after upgrade by names

    :id: fce33637-8e7b-4ccf-a9fb-47f0e0607f83

    :expectedresults: All templates should be retained post upgrade by names
    """
    assert pre == post
