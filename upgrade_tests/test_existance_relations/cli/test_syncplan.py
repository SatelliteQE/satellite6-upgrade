"""Upgrade TestSuite for validating Satellite sync plans existence and its
association post upgrade

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
component = 'sync-plan'
sp_name = compare_postupgrade(component, 'name')
sp_sd = compare_postupgrade(component, 'start date')
sp_interval = compare_postupgrade(component, 'interval')
sp_enable = compare_postupgrade(component, 'enabled')


# Tests
@pytest.mark.parametrize("pre,post", sp_name, ids=pytest_ids(sp_name))
def test_positive_syncplans_by_name(pre, post):
    """Test all sync plans are existing after upgrade by names

    :id: upgrade-8030bff2-455e-4b1a-8b62-0596465ef2da

    :expectedresults: All sync plans should be retained post upgrade by names
    """
    assert existence(pre, post)


@pytest.mark.parametrize("pre,post", sp_sd, ids=pytest_ids(sp_sd))
def test_positive_syncplans_by_start_date(pre, post):
    """Test all sync plans start date is retained after upgrade

    :id: upgrade-8106ddf2-701c-4c58-8246-b0122195fa5d

    :expectedresults: All sync plans start date should be retained post upgrade
    """
    assert existence(pre, post)


@pytest.mark.parametrize("pre,post", sp_interval, ids=pytest_ids(sp_interval))
def test_positive_syncplans_by_interval(pre, post):
    """Test all sync plans interval time is retained after upgrade

    :id: upgrade-058eeba9-9a4d-44c5-a759-48c3199b70f0

    :expectedresults: All sync plans interval time should be retained post
        upgrade
    """
    assert existence(pre, post)


@pytest.mark.parametrize("pre,post", sp_enable, ids=pytest_ids(sp_enable))
def test_positive_syncplans_by_enablement(pre, post):
    """Test all sync plans enablement and disablement is retained after upgrade

    :id: upgrade-a90e8c93-74b5-49f8-9c08-4fba7903635c

    :expectedresults: All sync plans enablement and disablement should be
        retained post upgrade
    """
    assert existence(pre, post)
