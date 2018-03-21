"""Upgrade TestSuite for validating Satellite Content Views existence
post upgrade

:Requirement: Upgraded Satellite

:CaseAutomation: Automated

:CaseLevel: System

:CaseComponent: API

:TestType: nonfunctional

:CaseImportance: High

:SubType1: installability

:Upstream: No
"""
import pytest
from upgrade_tests.helpers.common import existence
from upgrade_tests.helpers.existence import compare_postupgrade, pytest_ids

# Required Data
component = 'contentview'
cv_chosts = compare_postupgrade(component, 'content_host_count')


# Tests
@pytest.mark.parametrize("pre,post", cv_chosts, ids=pytest_ids(cv_chosts))
def test_positive_cv_by_chosts_count(pre, post):
    """Test Contents hosts association is retained with CVs post upgrade

    :id: upgrade-3bd14640-89c6-4463-af57-06b822c8eff6

    :expectedresults: Content Hosts of all CVs should be retained post
        upgrade
    """
    assert existence(pre, post)
