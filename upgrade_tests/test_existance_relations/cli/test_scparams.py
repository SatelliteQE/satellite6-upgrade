"""Upgrade TestSuite for validating Satellite smart class parameters
 existence and associations post upgrade

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
from upgrade_tests.helpers.common import run_to_upgrade, existence
from upgrade_tests.helpers.existence import compare_postupgrade, pytest_ids


# Required Data
component = 'sc-param'
scp_names = compare_postupgrade(component, 'parameter')
scp_dval = compare_postupgrade(component, 'default value')
scp_ovrde = compare_postupgrade(component, 'override')
scp_pclass = compare_postupgrade(component, 'puppet class')


# Tests
@pytest.mark.parametrize("pre,post", scp_names, ids=pytest_ids(scp_names))
def test_positive_smart_params_by_name(pre, post):
    """Test all smart parameters are existing after upgrade by names

    :id: upgrade-44113fb7-eab2-439b-986c-6110a1c15d54

    :expectedresults: All smart parameters should be retained post upgrade by
        names
    """
    assert existence(pre, post)


@pytest.mark.parametrize("pre,post", scp_dval, ids=pytest_ids(scp_dval))
def test_positive_smart_params_by_default_value(pre, post):
    """Test all smart parameters default values are retained after upgrade

    :id: upgrade-35a94fb5-5601-4b85-b23a-dd3ccb945bd6

    :expectedresults: All smart parameters default values should be retained
        post upgrade
    """
    assert existence(pre, post)


@pytest.mark.parametrize("pre,post", scp_ovrde, ids=pytest_ids(scp_ovrde))
def test_positive_smart_params_by_override(pre, post):
    """Test all smart parameters override check is retained after upgrade

    :id: upgrade-9f045338-8a79-43b1-a22c-45e79e8dbc56

    :expectedresults: All smart parameters override check should be retained
        post upgrade
    """
    assert existence(pre, post)


@run_to_upgrade('6.2')
@pytest.mark.parametrize("pre,post", scp_pclass, ids=pytest_ids(scp_pclass))
def test_positive_smart_params_by_puppet_class(pre, post):
    """Test all smart parameters associations with its puppet class is retained
    after upgrade

    :id: upgrade-86714406-afcf-45a8-8db9-07ea03251cfa

    :expectedresults: All smart parameters associations with puppet classes
        should be retained post upgrade
    """
    assert existence(pre, post)
