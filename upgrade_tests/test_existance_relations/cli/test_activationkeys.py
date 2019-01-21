"""Upgrade TestModule for validating Satellite AKs existence and
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
component = 'activation-key'
aks_cv = compare_postupgrade(component, 'content view')
aks_lc = compare_postupgrade(component, 'lifecycle environment')
aks_name = compare_postupgrade(component, 'name')
aks_hl = compare_postupgrade(
    component, ('consumed', 'host limit', 'host limit', 'host limit', 'host limit'))


# Tests
@pytest.mark.parametrize("pre,post", aks_cv, ids=pytest_ids(aks_cv))
def test_positive_aks_by_content_view(pre, post):
    """Test CV association of all AKs post upgrade

    :id: upgrade-37804d7c-3667-45f3-8039-891908372ce7

    :expectedresults: CV of all AKs should be retained post upgrade
    """
    assert existence(pre, post)


@pytest.mark.parametrize("pre,post", aks_lc, ids=pytest_ids(aks_lc))
def test_positive_aks_by_lc(pre, post):
    """Test LC association of all AKs post upgrade

    :id: upgrade-16dc1ae8-f30d-45c3-8289-f0f0736ca603

    :expectedresults: LC of all AKs should be retained post upgrade
    """
    assert existence(pre, post)


@pytest.mark.parametrize("pre,post", aks_name, ids=pytest_ids(aks_name))
def test_positive_aks_by_name(pre, post):
    """Test AKs are existing by their name post upgrade

    :id: upgrade-31d079e2-a457-4b5a-b371-b0f70432bf1d

    :expectedresults: AKs should be existing by their names post upgrade
    """
    assert existence(pre, post)


@pytest.mark.parametrize("pre,post", aks_hl, ids=pytest_ids(aks_hl))
def test_positive_aks_by_host_limit(pre, post):
    """Test host limit associations of all AKs post upgrade

    :id: upgrade-cee32f2a-d4f4-4cf8-91da-aaed426f1942

    :expectedresults: Subscription consumptions by hosts of all AKs should be
        retained post upgrade
    """
    assert existence(pre, post)
