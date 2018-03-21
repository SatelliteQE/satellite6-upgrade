"""Upgrade TestSuite for validating Satellite discovery rules existence abd
its associations post upgrade

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
component = 'discovery_rule'
drule_name = compare_postupgrade(component, 'name')
drule_prio = compare_postupgrade(component, 'priority')
drule_search = compare_postupgrade(component, 'search')
drule_hg = compare_postupgrade(component, 'host group')
drule_hl = compare_postupgrade(component, 'hosts limit')
drule_enable = compare_postupgrade(component, 'enabled')


# Tests
@pytest.mark.parametrize("pre,post", drule_name, ids=pytest_ids(drule_name))
def test_positive_discovery_rules_by_name(pre, post):
    """Test all discovery rules are existing after upgrade by name

    :id: upgrade-0d7e8920-5717-4196-af8a-977cfba33184

    :expectedresults: All discovery rules should be retained post upgrade by
        names
    """
    assert existence(pre, post)


@pytest.mark.parametrize("pre,post", drule_prio, ids=pytest_ids(drule_prio))
def test_positive_discovery_rules_by_priority(pre, post):
    """Test all discovery rules priorities are existing after upgrade

    :id: upgrade-f2a1c6e6-d025-463c-a837-4f4657106f1e

    :expectedresults: All discovery rules priorities should be retained post
        upgrade
    """
    assert existence(pre, post)


@pytest.mark.parametrize(
    "pre,post", drule_search, ids=pytest_ids(drule_search))
def test_positive_discovery_rules_by_search(pre, post):
    """Test all discovery rules search are existing after upgrade

    :id: upgrade-ef1944c4-62f6-447e-90d9-f8ed95eb35de

    :expectedresults: All discovery rules search should be retained post
        upgrade
    """
    assert existence(pre, post)


@pytest.mark.parametrize("pre,post", drule_hg, ids=pytest_ids(drule_hg))
def test_positive_discovery_rules_by_hostgroup(pre, post):
    """Test all discovery rules hostgroup associations are existing after
    upgrade

    :id: upgrade-da605ae6-cdf8-49f9-87f6-c1cdfc411f90

    :expectedresults: All discovery rules hostgroups should be retained post
        upgrade
    """
    assert existence(pre, post)


@pytest.mark.parametrize("pre,post", drule_hl, ids=pytest_ids(drule_hl))
def test_positive_discovery_rules_by_hostslimit(pre, post):
    """Test all discovery rules hosts limit are retained after upgrade

    :id: upgrade-a9c59324-85eb-4295-8f2d-6f2e783a63dd

    :expectedresults: All discovery rules hosts limit should be retained post
        upgrade
    """
    assert existence(pre, post)


@pytest.mark.parametrize(
    "pre,post", drule_enable, ids=pytest_ids(drule_enable))
def test_positive_discovery_rules_by_enablement(pre, post):
    """Test all discovery rules enablement and disablement is existing after
        upgrade

    :id: upgrade-7b71be69-1c60-43e8-bbfb-938565ef8eee

    :expectedresults: All discovery rules enablement and disablement should be
        retained post upgrade
    """
    assert existence(pre, post)
