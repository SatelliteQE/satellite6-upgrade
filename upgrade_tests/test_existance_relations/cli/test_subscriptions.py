"""Upgrade TestSuite for validating Satellite subscriptions existence post
upgrade

:Requirement: Upgraded Satellite

:CaseAutomation: Automated

:CaseLevel: System

:CaseComponent: SubscriptionManagement

:TestType: nonfunctional

:CaseImportance: High

:SubType1: installability

:Upstream: No
"""
import pytest

from upgrade.helpers import settings
from upgrade_tests.helpers.common import existence
from upgrade_tests.helpers.existence import compare_postupgrade
from upgrade_tests.helpers.existence import pytest_ids
# Required Data
component = 'subscription'
sub_name = compare_postupgrade(component, 'name')
sub_uuid = compare_postupgrade(component, ('uuid', 'uuid', 'uuid', 'uuid'))
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

    :id: upgrade-b5b47ce8-81c7-43ec-a9b1-a2861b2f2eab

    :expectedresults: All subscriptions uuids should be retained post upgrade
    """
    assert existence(pre, post)


@pytest.mark.parametrize("pre,post", sub_support, ids=pytest_ids(sub_support))
def test_positive_subscriptions_by_support(pre, post):
    """Test all subscriptions support status is retained after upgrade

    :id: upgrade-4e3352b8-3ddf-49bd-9002-95ed2fc3e84a

    :expectedresults: All subscriptions support status should be retained post
        upgrade
    """
    assert existence(pre, post)


@pytest.mark.parametrize("pre,post", sub_qntity, ids=pytest_ids(sub_qntity))
def test_positive_subscriptions_by_quantity(pre, post):
    """Test all subscriptions quantities are retained after upgrade

    :id: upgrade-fe42065a-01c3-4557-b7e9-330c68cd612d

    :expectedresults: All subscriptions quantities should be retained post
        upgrade
    """
    assert existence(pre, post, component)


@pytest.mark.parametrize("pre,post", sub_consume, ids=pytest_ids(sub_consume))
def test_positive_subscriptions_by_consumed(pre, post):
    """Test all subscriptions consumed status is retained after upgrade

    :id: upgrade-fe859a5a-9d83-45fc-8dcf-1274301df446

    :expectedresults: All subscriptions consumed status should be retained post
        upgrade
    """
    assert existence(pre, post)


@pytest.mark.parametrize("pre,post", sub_edate, ids=pytest_ids(sub_edate))
def test_positive_subscriptions_by_end_date(pre, post):
    """Test all subscriptions end date status is retained after upgrade

    :id: upgrade-980139c0-d31d-43d0-b0e6-eeb5bff8d0aa

    :expectedresults: All subscriptions end date status should be retained post
        upgrade
    """
    from_ver = settings.upgrade.from_version
    if from_ver == '6.1':
        post = post.split('t')[0]
    if from_ver == '6.2':
        splited_pre = pre.split('t')
        pre = ' '.join(
            [splited_pre[0].replace('-', '/'), splited_pre[1].split('.')[0]]
        )
    assert existence(pre, post)
