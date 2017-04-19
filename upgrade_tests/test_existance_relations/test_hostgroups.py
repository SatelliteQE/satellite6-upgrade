"""Upgrade TestSuite for validating Satellite hostgroups existence and their
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


@pytest.mark.parametrize("pre,post", compare_postupgrade('hostgroup', 'name'))
def test_positive_hostgroups_by_name(pre, post):
    """Test all hostgroups are existing post upgrade by their names

    :id: 61739c36-30da-4f52-957c-abb1d0e728c7

    :expectedresults: All hostgroups should be retained post upgrade
    """
    assert pre == post


@pytest.mark.parametrize(
    "pre,post",
    compare_postupgrade('hostgroup', 'operating system')
)
def test_positive_hostgroups_by_os(pre, post):
    """Test OS associations of all hostgroups post upgrade

    :id: b2af5ad8-f7c8-49e6-9a9a-b31defb31e98

    :expectedresults: OS associations of all hostgroups should be retained post
        upgrade
    """
    assert pre == post


@pytest.mark.parametrize(
    "pre,post",
    compare_postupgrade('hostgroup', 'environment')
)
def test_positive_hostgroups_by_lc(pre, post):
    """Test LC associations of all hostgroups post upgrade

    :id: 4a071358-689e-46f1-9641-fd5958d4e725

    :expectedresults: LC associations of all hostgroups should be retained post
        upgrade
    """
    assert pre == post
