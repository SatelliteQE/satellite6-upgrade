"""Upgrade TestSuite for validating Satellite repositories existence and its
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
from upgrade_tests.helpers.common import existence
from upgrade_tests.helpers.existence import compare_postupgrade, pytest_ids

# Required Data
component = 'repository'
repo_name = compare_postupgrade(component, 'name')
repo_prod = compare_postupgrade(component, 'product')
repo_ctype = compare_postupgrade(component, 'content type')


# Tests
@pytest.mark.parametrize("pre,post", repo_name, ids=pytest_ids(repo_name))
def test_positive_repositories_by_name(pre, post):
    """Test all repositories are existing after upgrade by names

    :id: upgrade-13811137-89f7-4dc7-b4b5-4aed91546bd5

    :expectedresults: All repositories should be retained post upgrade by names
    """
    assert existence(pre, post)


@pytest.mark.parametrize("pre,post", repo_prod, ids=pytest_ids(repo_prod))
def test_positive_repositories_by_product(pre, post):
    """Test all repositories association with products are existing after
    upgrade

    :id: upgrade-24130f2e-4eef-4038-8ae6-14613c79e34a

    :expectedresults: All repositories association to its product should be
        retained post upgrade
    """
    assert existence(pre, post)


@pytest.mark.parametrize("pre,post", repo_ctype, ids=pytest_ids(repo_ctype))
def test_positive_repositories_by_url(pre, post):
    """Test all repositories urls are existing after upgrade

    :id: upgrade-0776a63f-863e-481d-a7a4-87e449029914

    :expectedresults: All repositories urls should be retained post upgrade
    """
    assert existence(pre, post)
