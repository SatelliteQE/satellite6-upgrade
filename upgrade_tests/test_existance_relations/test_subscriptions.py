"""Upgrade TestSuite for validating Satellite subscriptions existence post
upgrade

:Requirement: Upgraded Satellite

:CaseAutomation: Automated

:CaseLevel: Acceptance

:CaseComponent: CLI

:TestType: NonFunctional

:CaseImportance: High

:Upstream: No
"""
import pytest
from upgrade_tests.helpers.existence import compare_postupgrade, pytest_ids

# Required Data
component = 'subscription'
sub_name = compare_postupgrade(component, 'name')
sub_uuid = compare_postupgrade(component, 'uuid')
sub_support = compare_postupgrade(component, 'support')
sub_qntity = compare_postupgrade(component, 'quantity')
sub_consume = compare_postupgrade(component, 'consumed')
sub_edate = compare_postupgrade(component, 'end date')


# Tests
@pytest.mark.parametrize("pre,post", sub_name, ids=pytest_ids(sub_name))
def test_positive_subscriptions_by_name(pre, post):
    """Test all subscriptions are existing after upgrade by names

    :id: 535d6529-27cb-4c6f-959e-6d0684e77aa6

    :expectedresults: All subscriptions should be retained post upgrade by
        names
    """
    assert pre == post


@pytest.mark.parametrize("pre,post", sub_uuid, ids=pytest_ids(sub_uuid))
def test_positive_subscriptions_by_uuid(pre, post):
    """Test all subscriptions uuids are existing after upgrade

    :id: 535d6529-27cb-4c6f-959e-6d0684e77aa6

    :expectedresults: All subscriptions uuids should be retained post upgrade
    """
    assert pre == post


@pytest.mark.parametrize("pre,post", sub_support, ids=pytest_ids(sub_support))
def test_positive_subscriptions_by_support(pre, post):
    """Test all subscriptions support status is retained after upgrade

    :id: 535d6529-27cb-4c6f-959e-6d0684e77aa6

    :expectedresults: All subscriptions support status should be retained post
        upgrade
    """
    assert pre == post


@pytest.mark.parametrize("pre,post", sub_qntity, ids=pytest_ids(sub_qntity))
def test_positive_subscriptions_by_quantity(pre, post):
    """Test all subscriptions quantities are retained after upgrade

    :id: 535d6529-27cb-4c6f-959e-6d0684e77aa6

    :expectedresults: All subscriptions quantities should be retained post
        upgrade
    """
    assert pre == post


@pytest.mark.parametrize("pre,post", sub_consume, ids=pytest_ids(sub_consume))
def test_positive_subscriptions_by_consumed(pre, post):
    """Test all subscriptions consumed status is retained after upgrade

    :id: 535d6529-27cb-4c6f-959e-6d0684e77aa6

    :expectedresults: All subscriptions consumed status should be retained post
        upgrade
    """
    assert pre == post


@pytest.mark.parametrize("pre,post", sub_edate, ids=pytest_ids(sub_edate))
def test_positive_subscriptions_by_end_date(pre, post):
    """Test all subscriptions end date status is retained after upgrade

    :id: 535d6529-27cb-4c6f-959e-6d0684e77aa6

    :expectedresults: All subscriptions end date status should be retained post
        upgrade
    """
    assert pre == post
