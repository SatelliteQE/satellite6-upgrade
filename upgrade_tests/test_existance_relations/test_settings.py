"""Upgrade TestSuite for validating Satellite settings existence post upgrade

:Requirement: Upgraded Satellite

:CaseAutomation: Automated

:CaseLevel: Acceptance

:CaseComponent: CLI

:TestType: NonFunctional

:CaseImportance: High

:Upstream: No
"""
import pytest
from upgrade_tests.helpers.existence import compare_postupgrade


@pytest.mark.parametrize("pre,post", compare_postupgrade('settings', 'name'))
def test_positive_settings_by_name(pre, post):
    """Test all settings are existing post upgrade by their names

    :id: 802b547a-d9b1-4537-ba38-65d67985a94f

    :expectedresults: All settings should be retained post upgrade
    """
    assert pre == post


@pytest.mark.parametrize("pre,post", compare_postupgrade('settings', 'value'))
def test_positive_settings_by_value(pre, post):
    """Test all settings value are preserved post upgrade

    :id: 5b60d8cb-aced-49e8-b4f5-42ea30892fce

    :expectedresults: All settings values should be retained post upgrade
    """
    assert pre == post


@pytest.mark.parametrize(
    "pre,post",
    compare_postupgrade('settings', 'description')
)
def test_positive_settings_by_description(pre, post):
    """Test all settings descriptions are existing post upgrade

    :id: 3b5ccd81-cb0e-4bdd-a10f-972ad29f7ac6

    :expectedresults: All settings descriptions should be retained post upgrade
    """
    assert pre == post
