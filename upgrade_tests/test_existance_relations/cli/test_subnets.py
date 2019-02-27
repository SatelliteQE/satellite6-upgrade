"""Upgrade TestSuite for validating Satellite subnets existence and
associations post upgrade

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
component = 'subnet'
sub_name = compare_postupgrade(component, 'name')
sub_network = compare_postupgrade(
    component, ('network', 'network', 'network', 'network addr', 'network addr'))
sub_mask = compare_postupgrade(
    component, ('network', 'network', 'network', 'network mask', 'network mask'))


# Tests
@pytest.mark.parametrize("pre,post", sub_name, ids=pytest_ids(sub_name))
def test_positive_subnets_by_name(pre, post):
    """Test all subnets are existing post upgrade by their name

    :id: upgrade-07b32bf4-2205-4b9c-8af0-69c801058785

    :expectedresults: All subnets should be retained post upgrade
    """
    assert existence(pre, post)


@pytest.mark.parametrize("pre,post", sub_network, ids=pytest_ids(sub_network))
def test_positive_subnets_by_network(pre, post):
    """Test all subnets network ip's are existing post upgrade

    :id: upgrade-72d77821-15cd-4803-a7bd-623aeb7c692e

    :expectedresults: All subnets network ip's should be retained post upgrade
    """
    assert existence(pre, post)


@pytest.mark.parametrize("pre,post", sub_mask, ids=pytest_ids(sub_mask))
def test_positive_subnets_by_mask(pre, post):
    """Test all subnets masks are existing post upgrade

    :id: upgrade-18a6bbb1-00bf-4b3f-ada3-b7c3b9341460

    :expectedresults: All subnets masks should be retained post upgrade
    """
    assert existence(pre, post)
