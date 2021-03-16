"""Upgrade TestSuite for validating Satellite domains existence post upgrade

:Requirement: Upgraded Satellite

:CaseAutomation: Automated

:CaseLevel: System

:CaseComponent: Networking

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
component = 'domain'
dom_subnets = compare_postupgrade(component, 'subnets')


# Tests
@pytest.mark.parametrize("pre,post", dom_subnets, ids=pytest_ids(dom_subnets))
def test_positive_domains_by_subnet(pre, post):
    """Test subnets of domains are existing post upgrade

    :id: upgrade-1cc40da2-b5fa-48ed-96c8-448781c8116f

    :expectedresults: Subnets of all domains should be retained post upgrade
    """
    if settings.upgrade.to_version == '6.4':
        if post:
            [subnet.pop('description') for subnet in post]
    assert existence(pre, post)
