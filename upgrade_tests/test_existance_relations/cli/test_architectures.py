"""Upgrade TestSuite for validating Satellite architectures existence
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
component = 'architecture'
arc_name = compare_postupgrade(component, 'name')


# Tests
@pytest.mark.parametrize("pre,post", arc_name, ids=pytest_ids(arc_name))
def test_positive_architectures_by_name(pre, post):
    """Test all architectures are existing after upgrade by names

    :id: upgrade-eb6d3728-6b0b-4cb7-888e-8d64a46e7beb

    :expectedresults: All architectures should be retained post upgrade by
        names
    """
    assert existence(pre, post)
