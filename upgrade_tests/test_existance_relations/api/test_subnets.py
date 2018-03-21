"""Upgrade TestSuite for validating Satellite Subnets existence post upgrade

:Requirement: Upgraded Satellite

:CaseAutomation: Automated

:CaseLevel: System

:CaseComponent: API

:TestType: nonfunctional

:CaseImportance: High

:SubType1: installability

:Upstream: No
"""
import pytest
from upgrade_tests.helpers.common import existence
from upgrade_tests.helpers.existence import compare_postupgrade, pytest_ids

# Required Data
component = 'subnet'
sub_na = compare_postupgrade(component, 'network_address')


# Tests
@pytest.mark.parametrize("pre,post", sub_na, ids=pytest_ids(sub_na))
def test_positive_subnet_by_network_address(pre, post):
    """Test network addresses of subnets retained post upgrade

    :id: upgrade-316e6e8e-f129-4a54-b24c-a2677e142f36

    :expectedresults: Network Addresses of all subnets should be retained post
        upgrade
    """
    assert existence(pre, post)
