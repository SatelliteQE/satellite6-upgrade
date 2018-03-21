"""Upgrade TestSuite for validating Satellite subscriptions existence post
upgrade

:Requirement: Upgraded Satellite

:CaseAutomation: Automated

:CaseLevel: System

:CaseComponent: CLI

:TestType: nonfunctional

:CaseImportance: High

:SubType1: installability

:Upstream: No
"""
import os
import pytest
from upgrade_tests.helpers.common import existence
from upgrade_tests.helpers.existence import compare_postupgrade, pytest_ids

# Required Data
component = 'subscription'
sub_name = compare_postupgrade(component, 'name')
sub_uuid = compare_postupgrade(component, ('id', 'uuid', 'uuid'))
sub_support = compare_postupgrade(component, 'support')
sub_qntity = compare_postupgrade(component, 'quantity')
sub_consume = compare_postupgrade(component, 'consumed')
sub_edate = compare_postupgrade(component, 'end date')


# Tests
@pytest.mark.parametrize("pre,post", sub_name, ids=pytest_ids(sub_name))
def test_positive_subscriptions_by_name(pre, post):
    """Test all subscriptions are existing after upgrade by names

    :id: upgrade-535d6529-27cb-4c6f-959e-6d0684e77aa6

    :expectedresults: All subscriptions should be retained post upgrade by
        names
    """
    assert existence(pre, post)


@pytest.mark.parametrize("pre,post", sub_uuid, ids=pytest_ids(sub_uuid))
def test_positive_subscriptions_by_uuid(pre, post):
    """Test all subscriptions uuids are existing after upgrade

    :id: upgrade-535d6529-27cb-4c6f-959e-6d0684e77aa6

    :expectedresults: All subscriptions uuids should be retained post upgrade
    """
    assert existence(pre, post)


@pytest.mark.parametrize("pre,post", sub_support, ids=pytest_ids(sub_support))
def test_positive_subscriptions_by_support(pre, post):
    """Test all subscriptions support status is retained after upgrade

    :id: upgrade-535d6529-27cb-4c6f-959e-6d0684e77aa6

    :expectedresults: All subscriptions support status should be retained post
        upgrade
    """
    assert existence(pre, post)


@pytest.mark.parametrize("pre,post", sub_qntity, ids=pytest_ids(sub_qntity))
def test_positive_subscriptions_by_quantity(pre, post):
    """Test all subscriptions quantities are retained after upgrade

    :id: upgrade-535d6529-27cb-4c6f-959e-6d0684e77aa6

    :expectedresults: All subscriptions quantities should be retained post
        upgrade
    """
    assert existence(pre, post, component)


@pytest.mark.parametrize("pre,post", sub_consume, ids=pytest_ids(sub_consume))
def test_positive_subscriptions_by_consumed(pre, post):
    """Test all subscriptions consumed status is retained after upgrade

    :id: upgrade-535d6529-27cb-4c6f-959e-6d0684e77aa6

    :expectedresults: All subscriptions consumed status should be retained post
        upgrade
    """
    assert existence(pre, post)


@pytest.mark.parametrize("pre,post", sub_edate, ids=pytest_ids(sub_edate))
def test_positive_subscriptions_by_end_date(pre, post):
    """Test all subscriptions end date status is retained after upgrade

    :id: upgrade-535d6529-27cb-4c6f-959e-6d0684e77aa6

    :expectedresults: All subscriptions end date status should be retained post
        upgrade
    """
    from_ver = os.environ.get('FROM_VERSION')
    if from_ver == '6.1':
        post = post.split('t')[0]
    if from_ver == '6.2':
        splited_pre = pre.split('t')
        pre = ' '.join(
            [splited_pre[0].replace('-', '/'), splited_pre[1].split('.')[0]]
        )
    assert existence(pre, post)
