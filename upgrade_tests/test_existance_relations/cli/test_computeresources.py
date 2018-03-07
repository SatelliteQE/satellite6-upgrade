"""Upgrade TestSuite for validating Satellite compute resources existence and
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
component = 'compute-resource'
comp_name = compare_postupgrade(component, 'name')
comp_provider = compare_postupgrade(component, 'provider')


@pytest.mark.parametrize("pre,post", comp_name, ids=pytest_ids(comp_name))
def test_positive_compute_resources_by_name(pre, post):
    """Test all compute resources are existing post upgrade by their name

    :id: upgrade-24f05707-4547-458c-bb7e-96be35d3f043

    :expectedresults: All compute resources should be retained post upgrade
    """
    assert existence(pre, post)


@pytest.mark.parametrize(
    "pre,post", comp_provider, ids=pytest_ids(comp_provider))
def test_positive_compute_resources_by_provider(pre, post):
    """Test all compute resources provider are existing post upgrade

    :id: upgrade-f3429be3-505e-44ff-a4fb-4adc940e8b67

    :expectedresults: All compute resources provider should be retained post
        upgrade
    """
    assert existence(pre, post)
