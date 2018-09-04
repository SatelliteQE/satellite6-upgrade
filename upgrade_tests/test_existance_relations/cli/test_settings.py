"""Upgrade TestSuite for validating Satellite settings existence post upgrade

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
from upgrade_tests.helpers.common import dont_run_to_upgrade, existence
from upgrade_tests.helpers.existence import compare_postupgrade, pytest_ids

# Required Data
component = 'settings'
sett_name = compare_postupgrade(component, 'name')
sett_value = compare_postupgrade(component, 'value')
sett_desc = compare_postupgrade(component, 'description')


# Tests
@dont_run_to_upgrade('6.1')
@pytest.mark.parametrize("pre,post", sett_name, ids=pytest_ids(sett_name))
def test_positive_settings_by_name(pre, post):
    """Test all settings are existing post upgrade by their names

    :id: upgrade-802b547a-d9b1-4537-ba38-65d67985a94f

    :expectedresults: All settings should be retained post upgrade
    """
    assert existence(pre, post)


@dont_run_to_upgrade('6.1')
@pytest.mark.parametrize("pre,post", sett_value, ids=pytest_ids(sett_value))
def test_positive_settings_by_value(pre, post):
    """Test all settings value are preserved post upgrade

    :id: upgrade-5b60d8cb-aced-49e8-b4f5-42ea30892fce

    :expectedresults: All settings values should be retained post upgrade
    """
    assert existence(pre, post, component=component)


@dont_run_to_upgrade('6.1')
@pytest.mark.parametrize("pre,post", sett_desc, ids=pytest_ids(sett_desc))
def test_positive_settings_by_description(pre, post):
    """Test all settings descriptions are existing post upgrade

    :id: upgrade-3b5ccd81-cb0e-4bdd-a10f-972ad29f7ac6

    :expectedresults: All settings descriptions should be retained post upgrade
    """
    assert existence(pre, post, component=component)
