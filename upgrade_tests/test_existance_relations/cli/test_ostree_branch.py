"""Upgrade TestSuite for validating Satellite ostree-branch existence and
associations post upgrade

:Requirement: Upgraded Satellite

:CaseAutomation: Automated

:CaseLevel: System

:CaseComponent: CLI

:TestType: nonfunctional

:CaseImportance: High

:Upstream: No
"""
import pytest
from upgrade_tests.helpers.common import existence
from upgrade_tests.helpers.existence import compare_postupgrade, pytest_ids

# Required Data
component = "ostree-branch"
ostree_id = compare_postupgrade(component, 'id')
ostree_name = compare_postupgrade(component, 'name')
ostree_version = compare_postupgrade(component, 'version')


# Tests
@pytest.mark.parametrize("pre,post", ostree_id, ids=pytest_ids(ostree_id))
def test_positive_ostree_branch_by_id(pre, post):
    """Test all ostree-branch are existing after upgrade by id's

    :id: upgrade-057ba0be-581c-4892-ad99-c52f0c3fd7c9

    :expectedresults: All ostree-branch should be retained post upgrade by id's
    """
    assert existence(pre, post)


@pytest.mark.parametrize("pre,post", ostree_name, ids=pytest_ids(ostree_name))
def test_positive_ostree_branch_by_name(pre, post):
    """Test all ostree-branch are existing after upgrade by name

    :id: upgrade-9e8e74ba-43f7-41e5-ae5e-2b745f2a76fe

    :expectedresults: All ostree-branch should be retained post upgrade by name
    """
    assert existence(pre, post)


@pytest.mark.parametrize("pre,post", ostree_version, ids=pytest_ids(ostree_version))
def test_positive_ostree_branch_by_version(pre, post):
    """Test all ostree-branch versions are existing after upgrade

    :id: upgrade-9dc8583e-b7fb-43b3-81d4-5ae0f2917ff8

    :expectedresults: All ostree-branch versions should be retained post upgrade
    """
    assert existence(pre, post)
