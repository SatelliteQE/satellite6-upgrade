"""Upgrade TestSuite for validating Satellite capsules existence and
associations post upgrade

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


@pytest.mark.parametrize(
    "pre,post",
    compare_postupgrade('capsule', 'features')
)
def test_positive_capsules_by_features(pre, post):
    """Test all features of each capsule are existing post upgrade

    :id: 6d3b8f24-2d51-465c-8d01-5a159aa89f2f

    :expectedresults: All features of all capsules should be retained post
        upgrade
    """
    assert pre == post


@pytest.mark.parametrize(
    "pre,post",
    compare_postupgrade('capsule', 'name')
)
def test_positive_capsules_by_name(pre, post):
    """Test all capsules are existing after upgrade by their names

    :id: 774b8ae3-2c82-4224-afca-df70d5a22e9b

    :expectedresults: All capsules should be retained post upgrade
    """
    assert pre == post


@pytest.mark.parametrize(
    "pre,post",
    compare_postupgrade('capsule', 'url')
)
def test_positive_capsules_by_url(pre, post):
    """Test all capsules are existing after upgrade by their urls

    :id: 1e5b2826-6394-4d36-aa7b-36dfc6411dd7

    :expectedresults: Capsule urls of all capsules should be retained post
        upgrade
    """
    assert pre == post
