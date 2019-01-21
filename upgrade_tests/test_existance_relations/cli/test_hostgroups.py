"""Upgrade TestSuite for validating Satellite hostgroups existence and their
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
component = 'hostgroup'
hg_name = compare_postupgrade(component, 'name')
hg_os = compare_postupgrade(component, 'operating system')
hg_lc = compare_postupgrade(
    component,
    ('environment', 'environment', 'environment',
     'puppet environment', 'puppet environment')
)


# Tests
@pytest.mark.parametrize("pre,post", hg_name, ids=pytest_ids(hg_name))
def test_positive_hostgroups_by_name(pre, post):
    """Test all hostgroups are existing post upgrade by their names

    :id: upgrade-61739c36-30da-4f52-957c-abb1d0e728c7

    :expectedresults: All hostgroups should be retained post upgrade
    """
    assert existence(pre, post)


@pytest.mark.parametrize("pre,post", hg_os, ids=pytest_ids(hg_os))
def test_positive_hostgroups_by_os(pre, post):
    """Test OS associations of all hostgroups post upgrade

    :id: upgrade-b2af5ad8-f7c8-49e6-9a9a-b31defb31e98

    :expectedresults: OS associations of all hostgroups should be retained post
        upgrade
    """
    assert existence(pre, post)


@pytest.mark.parametrize("pre,post", hg_lc, ids=pytest_ids(hg_lc))
def test_positive_hostgroups_by_lc(pre, post):
    """Test LC associations of all hostgroups post upgrade

    :id: upgrade-4a071358-689e-46f1-9641-fd5958d4e725

    :expectedresults: LC associations of all hostgroups should be retained post
        upgrade
    """
    assert existence(pre, post)
