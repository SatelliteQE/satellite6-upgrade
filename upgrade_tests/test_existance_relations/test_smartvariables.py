"""Upgrade TestSuite for validating Satellite smart variables existence
and associations post upgrade

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
from upgrade_tests.helpers.common import run_to_upgrade
from upgrade_tests.helpers.existence import compare_postupgrade, pytest_ids

# Required Data
component = 'smart-variable'
sv_name = compare_postupgrade(component, ('name', 'name', 'variable'))
sv_dv = compare_postupgrade(component, 'default value')
sv_type = compare_postupgrade(component, 'type')
sv_pclass = compare_postupgrade(component, 'puppet class')


# Tests
@run_to_upgrade('6.2')
@pytest.mark.parametrize("pre,post", sv_name, ids=pytest_ids(sv_name))
def test_positive_smart_variables_by_name(pre, post):
    """Test all smart variables are existing after upgrade by names

    :id: upgrade-d2543c28-135d-4e8f-8fe6-f510f74f51b9

    :expectedresults: All smart variables should be retained post upgrade by
        names
    """
    assert pre == post


@run_to_upgrade('6.2')
@pytest.mark.parametrize("pre,post", sv_dv, ids=pytest_ids(sv_dv))
def test_positive_smart_variables_by_default_value(pre, post):
    """Test all smart variables default values are retained after upgrade

    :id: upgrade-c8337fbc-9c26-408a-a6ac-6f4886aabcdf

    :expectedresults: All smart variables default values should be retained
        post upgrade
    """
    assert pre == post


@run_to_upgrade('6.2')
@pytest.mark.parametrize("pre,post", sv_type, ids=pytest_ids(sv_type))
def test_positive_smart_variables_by_type(pre, post):
    """Test all smart variables override check is retained after upgrade

    :id: upgrade-401e491c-bb54-4d2e-88a7-b6b6a9c033e3

    :expectedresults: All smart variables override check should be retained
        post upgrade
    """
    assert pre == post


@run_to_upgrade('6.2')
@pytest.mark.parametrize("pre,post", sv_pclass, ids=pytest_ids(sv_pclass))
def test_positive_smart_variables_by_puppet_class(pre, post):
    """Test all smart variables associations with its puppet class is retained
    after upgrade

    :id: upgrade-97721211-4cfe-4170-8e9b-5dd622e0ae81

    :expectedresults: All smart variables associations with puppet classes
        should be retained post upgrade
    """
    assert pre == post
