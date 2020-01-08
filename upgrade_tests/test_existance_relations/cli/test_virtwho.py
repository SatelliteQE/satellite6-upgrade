"""Upgrade TestSuite for validating Satellite virt-who-config existence post upgrade

:Requirement: Upgraded Satellite

:CaseAutomation: Automated

:CaseLevel: System

:CaseComponent: virt-who-config

:TestType: nonfunctional

:CaseImportance: High

:SubType1: installability

:Upstream: No
"""
import pytest
from upgrade_tests.helpers.common import existence
from upgrade_tests.helpers.existence import compare_postupgrade, pytest_ids

# Required Data
component = 'virt-who-config'
virtwho_name = compare_postupgrade(component, 'name')
virtwho_interval = compare_postupgrade(component, 'interval')
virtwho_status = compare_postupgrade(component, 'status')
virtwho_last_report = compare_postupgrade(component, 'last report at')


# Tests
@pytest.mark.parametrize("pre,post", virtwho_name, ids=pytest_ids(virtwho_name))
def test_positive_virt_who_by_name(pre, post):
    """Test all virt-who configs are existing post upgrade by their name

    :id: upgrade-68e6a1dd-9b65-41ee-983b-0f2101300cd8

    :expectedresults: All virt-who configs should be retained post upgrade
    """
    assert existence(pre, post)


@pytest.mark.parametrize("pre,post", virtwho_interval, ids=pytest_ids(virtwho_interval))
def test_positive_virt_who_by_interval(pre, post):
    """Test all virt-who configs interval are existing post upgrade

    :id: upgrade-84702862-aef1-4b19-9007-dbb4e65a78c2

    :expectedresults: All virt-who configs interval should be retained post upgrade
    """
    assert existence(pre, post)


@pytest.mark.parametrize("pre,post", virtwho_status, ids=pytest_ids(virtwho_status))
def test_positive_virt_who_by_status(pre, post):
    """Test all virt-who configs status are existing post upgrade

    :id: upgrade-54db1ea8-1cfe-4aa6-9e7e-3f7409ca2a36

    :expectedresults: All virt-who configs status should be retained post upgrade
    """
    assert existence(pre, post)
