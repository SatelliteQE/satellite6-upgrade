"""Upgrade TestSuite for validating Satellite lifecycle environments existence
post upgrade

:Requirement: Upgraded Satellite

:CaseAutomation: Automated

:CaseLevel: System

:CaseComponent: CLI

:TestType: nonfunctional

:CaseImportance: High

:SubType1: installability

:Upstream: No
"""
import pytest
from upgrade_tests.helpers.common import existence
from upgrade_tests.helpers.existence import compare_postupgrade, pytest_ids

# Required Data
component = 'lifecycle-environment'
lc_name = compare_postupgrade(component, 'name')


# Tests
@pytest.mark.parametrize("pre,post", lc_name, ids=pytest_ids(lc_name))
def test_positive_lifecycle_envs_by_name(pre, post):
    """Test all lifecycle envs are existing after upgrade by names

    :id: upgrade-4bb9c13a-b573-4f03-b2b3-65592e275eb1

    :expectedresults: All lifecycle envs should be retained post upgrade by
        names
    """
    assert existence(pre, post)
