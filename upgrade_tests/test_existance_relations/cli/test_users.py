"""Upgrade TestSuite for validating Satellite users existence and
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
from upgrade_tests.helpers.existence import compare_postupgrade, pytest_ids

# Required Data
component = 'user'
user_name = compare_postupgrade(component, 'name')
user_login = compare_postupgrade(component, 'login')
user_email = compare_postupgrade(component, 'email')


# Tests
@pytest.mark.parametrize("pre,post", user_name, ids=pytest_ids(user_name))
def test_positive_users_by_name(pre, post):
    """Test all users are existing post upgrade by their name

    :id: upgrade-1accdb79-7dd6-4cf7-904a-b179e108ba2d

    :expectedresults: All users should be retained post upgrade
    """
    assert pre == post


@pytest.mark.parametrize("pre,post", user_login, ids=pytest_ids(user_login))
def test_positive_users_by_login(pre, post):
    """Test all users login name are existing post upgrade

    :id: upgrade-1b8cba29-38e7-4d65-a8b2-4f5abab511dd

    :expectedresults: All users login name should be retained post upgrade
    """
    assert pre == post


@pytest.mark.parametrize("pre,post", user_email, ids=pytest_ids(user_email))
def test_positive_users_by_email(pre, post):
    """Test all users email are existing post upgrade

    :id: upgrade-45d267e9-a714-4fc1-952d-fa2ddd1e8231

    :expectedresults: All users email should be retained post upgrade
    """
    assert pre == post
