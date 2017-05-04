"""Upgrade TestSuite for validating Satellite domains existence post upgrade

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
component = 'domain'
dom_name = compare_postupgrade(component, 'name')


# Tests
@pytest.mark.parametrize("pre,post", dom_name, ids=pytest_ids(dom_name))
def test_positive_domains_by_name(pre, post):
    """Test all domains are existing post upgrade by their names

    :id: 0f00b7c4-da85-437d-beae-19a0c50ae9d0

    :expectedresults: All domains should be retained post upgrade
    """
    assert pre == post
