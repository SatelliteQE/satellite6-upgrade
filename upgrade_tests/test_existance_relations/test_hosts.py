"""Upgrade TestSuite for validating Satellite hosts existence and
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
from robozilla.decorators import pytest_skip_if_bug_open
from upgrade_tests.helpers.existence import compare_postupgrade, pytest_ids

# Required Data
component = 'host'
host_ip = compare_postupgrade(component, 'ip')
host_mac = compare_postupgrade(component, 'mac')
host_hg = compare_postupgrade(component, 'host group')
host_os = compare_postupgrade(component, 'operating system')
host_name = compare_postupgrade(component, 'name')


# Tests
@pytest.mark.parametrize("pre,post", host_ip, ids=pytest_ids(host_ip))
def test_positive_hosts_by_ip(pre, post):
    """Test ip associations of all hosts post upgrade

    :id: upgrade-3b4f8315-8490-42bc-8afa-4a6c267558d7

    :expectedresults: IP of each host should be associated to its respective
        host post upgrade
    """
    assert pre == post


@pytest_skip_if_bug_open('bugzilla', 1289510)
@pytest.mark.parametrize("pre,post", host_mac, ids=pytest_ids(host_mac))
def test_positive_hosts_by_mac(pre, post):
    """Test mac associations of all hosts post upgrade

    :id: upgrade-526af1dd-f2a1-4a66-a0d2-fe5c1ade165d

    :expectedresults: MAC of each host should be associated to its respective
        host post upgrade
    """
    assert pre == post


@pytest.mark.parametrize("pre,post", host_hg, ids=pytest_ids(host_hg))
def test_positive_hosts_by_hostgroup(pre, post):
    """Test hostgroup associations of all hosts post upgrade

    :id: upgrade-75d861ad-d8b5-4051-a584-b06ac63fd444

    :expectedresults: HostGroup of each host should be associated to its
        respective host post upgrade
    """
    assert pre == post


@pytest.mark.parametrize("pre,post", host_os, ids=pytest_ids(host_os))
def test_positive_hosts_by_operating_system(pre, post):
    """Test OS associations of all hosts post upgrade

    :id: upgrade-13c93f4b-0a46-4c74-aefa-136484bd8999

    :expectedresults: OS of each host should be associated to its respective
        host post upgrade
    """
    assert pre == post


@pytest.mark.parametrize("pre,post", host_name, ids=pytest_ids(host_name))
def test_positive_hosts_by_name(pre, post):
    """Test all hosts are retained post upgrade by their name

    :id: upgrade-2421fe0d-370d-4191-af36-1565f7c088bd

    :expectedresults: All hosts should be retained post upgrade by their names
    """
    assert pre == post
