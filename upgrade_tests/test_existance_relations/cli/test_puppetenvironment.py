"""Upgrade TestSuite for validating puppet environment existence
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
component = 'environment'
env_name = compare_postupgrade(component, 'name')


# Tests
@pytest.mark.parametrize("pre,post", env_name, ids=pytest_ids(env_name))
def test_positive_puppet_envs_by_name(pre, post):
    """Test all puppet envs are existing after upgrade by names

    :id: upgrade-d144094d-48fd-450b-8570-bd53758e090f

    :expectedresults: All puppet envs should be retained post upgrade by names
    """
    assert existence(pre, post)
