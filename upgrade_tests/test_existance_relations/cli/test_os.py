"""Upgrade TestSuite for validating OS in Satellite existence post upgrade

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
component = 'os'
os_title = compare_postupgrade(component, 'title')
os_fam = compare_postupgrade(component, 'family')


# Tests
@pytest.mark.parametrize("pre,post", os_title, ids=pytest_ids(os_title))
def test_positive_os_by_title(pre, post):
    """Test all OS are existing post upgrade by their title

    :id: upgrade-faf14fe0-cd2d-4c27-ad3a-eb631820eaa1

    :expectedresults: All OS should be retained post upgrade by their title
    """
    assert existence(pre, post)


@pytest.mark.parametrize("pre,post", os_fam, ids=pytest_ids(os_fam))
def test_positive_os_by_family(pre, post):
    """Test all OS are existing post upgrade by their families

    :id: upgrade-de83ceca-1dd5-4e20-a815-91d348b79e29

    :expectedresults: All OS should be retained post upgrade by their families
    """
    assert existence(pre, post)
