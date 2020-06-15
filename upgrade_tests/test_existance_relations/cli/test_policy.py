"""Upgrade TestModule for validating Compliance policies existence and
their associations after upgrade

:Requirement: Upgraded Satellite

:CaseAutomation: Automated

:CaseLevel: System

:CaseComponent: Compliance Policy

:TestType: nonfunctional

:CaseImportance: High

:Upstream: No
"""
import pytest

from upgrade_tests.helpers.common import existence
from upgrade_tests.helpers.existence import compare_postupgrade
from upgrade_tests.helpers.existence import pytest_ids


# Required Data
component = 'policy'
policy_id = compare_postupgrade(component, 'id')
policy_name = compare_postupgrade(component, 'name')


# Tests
@pytest.mark.parametrize("pre,post", policy_name, ids=pytest_ids(policy_name))
def test_positive_policy_by_name(pre, post):
    """Test all policies existence by name after post upgrade

    :id: upgrade-3b733e91-f593-49f4-87bf-2eb6b1a0ccf5

    :expectedresults: All policies name should be retained  after post upgrade
    """
    assert existence(pre, post)


@pytest.mark.parametrize("pre,post", policy_id, ids=pytest_ids(policy_id))
def test_positive_policy_id(pre, post):
    """Test all policies id's existence after post upgrade"

    :id: upgrade-9974fbf6-df36-417d-a024-bfa27ee99407

    :expectedresults: All policies id should be retained after post upgrade
    """
    assert existence(pre, post)
