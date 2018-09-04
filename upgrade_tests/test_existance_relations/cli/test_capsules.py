"""Upgrade TestSuite for validating Satellite capsules existence and
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
from upgrade_tests.helpers.common import dont_run_to_upgrade, existence
from upgrade_tests.helpers.existence import compare_postupgrade, pytest_ids

# Required Data
component = 'capsule'
cap_features = compare_postupgrade(component, 'features')
cap_name = compare_postupgrade(component, 'name')
cap_url = compare_postupgrade(component, 'url')


# Tests
@dont_run_to_upgrade('6.1')
@pytest.mark.parametrize(
    "pre,post", cap_features, ids=pytest_ids(cap_features))
def test_positive_capsules_by_features(pre, post):
    """Test all features of each capsule are existing post upgrade

    :id: upgrade-6d3b8f24-2d51-465c-8d01-5a159aa89f2f

    :expectedresults: All features of all capsules should be retained post
        upgrade
    """
    assert existence(pre, post, component)


@pytest.mark.parametrize("pre,post", cap_name, ids=pytest_ids(cap_name))
def test_positive_capsules_by_name(pre, post):
    """Test all capsules are existing after upgrade by their names

    :id: upgrade-774b8ae3-2c82-4224-afca-df70d5a22e9b

    :expectedresults: All capsules should be retained post upgrade
    """
    assert existence(pre, post)


@pytest.mark.parametrize("pre,post", cap_url, ids=pytest_ids(cap_url))
def test_positive_capsules_by_url(pre, post):
    """Test all capsules are existing after upgrade by their urls

    :id: upgrade-1e5b2826-6394-4d36-aa7b-36dfc6411dd7

    :expectedresults: Capsule urls of all capsules should be retained post
        upgrade
    """
    assert existence(pre, post)
