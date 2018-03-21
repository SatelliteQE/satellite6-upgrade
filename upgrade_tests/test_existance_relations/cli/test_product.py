"""Upgrade TestSuite for validating Satellite products existence
post upgrade

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
component = 'product'
prod_name = compare_postupgrade(component, 'name')
prod_repo = compare_postupgrade(component, 'repositories')


# Tests
@pytest.mark.parametrize("pre,post", prod_name, ids=pytest_ids(prod_name))
def test_positive_products_by_name(pre, post):
    """Test all products are existing after upgrade by names

    :id: upgrade-3dea1ee4-ed57-4341-957a-d9b1813ff4db

    :expectedresults: All products should be retained post upgrade by names
    """
    assert existence(pre, post)


@pytest.mark.parametrize("pre,post", prod_repo, ids=pytest_ids(prod_repo))
def test_positive_products_by_repositories(pre, post):
    """Test all products association with their repositories are existing after
    upgrade

    :id: upgrade-cb3b838b-d69d-4de9-9ebb-bbc6143ecdbf

    :expectedresults: Repositories of all products should be retained post
        upgrade
    """
    assert existence(pre, post)
