"""Upgrade TestSuite for validating Satellite lifecycle environments existence
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
    compare_postupgrade('lifecycle-environment', 'name')
)
def test_positive_lifecycle_envs_by_name(pre, post):
    """Test all lifecycle envs are existing after upgrade by names

    :id: 4bb9c13a-b573-4f03-b2b3-65592e275eb1

    :expectedresults: All lifecycle envs should be retained post upgrade by
        names
    """
    assert pre == post
