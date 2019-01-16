"""Upgrade TestSuite for validating Satellite host discovery existence and
its relations post upgrade

:Requirement: Upgraded Satellite

:CaseAutomation: Automated

:CaseLevel: System

:CaseComponent: CLI

:TestType: nonfunctional

:CaseImportance: High

:SubType1: installability

:Upstream: No
"""
import os
import pytest
from upgrade_tests.helpers.common import existence
from upgrade_tests.helpers.existence import compare_postupgrade, pytest_ids

# Required Data
component = 'discovery'
dis_name = compare_postupgrade(component, 'name')
dis_mac = compare_postupgrade(component, 'mac')
dis_cpus = compare_postupgrade(component, 'cpus')
dis_mem = compare_postupgrade(component, 'memory')
dis_disks = compare_postupgrade(component, 'disk count')
dis_size = compare_postupgrade(component, 'disks size')
dis_subnet = compare_postupgrade(component, 'subnet')
to_version = os.environ.get('TO_VERSION')
from_version = os.environ.get('FROM_VERSION')


# Tests
@pytest.mark.parametrize("pre,post", dis_name, ids=pytest_ids(dis_name))
def test_positive_discovery_by_name(pre, post):
    """Test all architectures are existing after upgrade by names

    :id: upgrade-2322766f-0731-4e80-bf54-d48a8756406d

    :expectedresults: All architectures should be retained post upgrade by
        names
    """
    assert existence(pre, post)


@pytest.mark.parametrize("pre,post", dis_mac, ids=pytest_ids(dis_mac))
def test_positive_discovery_by_mac(pre, post):
    """Test discovered hosts mac is retained after upgrade

    :id: upgrade-348a11f1-e7c2-4ff5-b36c-c79626ff2142

    :expectedresults: All discovered hosts mac should be retained post upgrade
    """
    assert existence(pre, post)


@pytest.mark.parametrize("pre,post", dis_cpus, ids=pytest_ids(dis_cpus))
def test_positive_discovery_by_cpus(pre, post):
    """Test discovered hosts cpus are retained after upgrade

    :id: upgrade-733663f6-4bee-4e0d-b4ed-35ac2e0e6370

    :expectedresults: All discovered hosts cpus should be retained post upgrade
    """
    assert existence(pre, post)


@pytest.mark.parametrize("pre,post", dis_mem, ids=pytest_ids(dis_mem))
def test_positive_discovery_by_memory(pre, post):
    """Test discovered hosts memory allocation is retained after upgrade

    :id: upgrade-91d2c395-d788-45c8-b722-051fbed18d38

    :expectedresults: All discovered hosts memory allocation should be retained
        post upgrade
    """
    assert existence(pre, post)


@pytest.mark.parametrize("pre,post", dis_disks, ids=pytest_ids(dis_disks))
def test_positive_discovery_by_disc_counts(pre, post):
    """Test discovered hosts disc counts are retained after upgrade

    :id: upgrade-ddb9c37c-4287-4419-b890-8a7891a333f0

    :expectedresults: All discovered hosts disk counts should be retained post
        upgrade
    """
    assert existence(pre, post)


@pytest.mark.parametrize("pre,post", dis_size, ids=pytest_ids(dis_size))
def test_positive_discovery_by_disc_size(pre, post):
    """Test discovered hosts disc size are retained after upgrade

    :id: upgrade-ad71e779-cded-4ba7-aaf2-ff0d138b3613

    :expectedresults: All discovered hosts disk size should be retained post
        upgrade
    """
    assert existence(pre, post)


@pytest.mark.parametrize("pre,post", dis_subnet, ids=pytest_ids(dis_subnet))
def test_positive_discovery_by_subnet(pre, post):
    """Test discovered hosts subnet is retained after upgrade

    :id: upgrade-c5218155-95a4-4a90-b853-76f843bb07c0

    :expectedresults: All discovered hosts subnet should be retained post
        upgrade
    """
    post = post.split(' (')[0] if float(to_version) >= 6.3 else post
    pre = post.split(' (')[0] if float(from_version) >= 6.3 else pre
    assert existence(pre, post)
