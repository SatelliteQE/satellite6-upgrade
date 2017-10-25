"""Upgrade TestSuite for validating Satellite Orgs existence and
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
component = 'organization'
org_id = compare_postupgrade(component, 'id')
org_name = compare_postupgrade(component, 'name')
org_label = compare_postupgrade(component, 'label')
org_desc = compare_postupgrade(component, 'description')


# Tests
@pytest.mark.parametrize("pre,post", org_id, ids=pytest_ids(org_id))
def test_positive_organizations_by_id(pre, post):
    """Test all organizations are existing after upgrade by id's

    :id: upgrade-d7eceba4-8076-4d46-aeaf-0679ea38586c

    :expectedresults: All organizations should be retained post upgrade by id's
    """
    assert pre == post


@pytest.mark.parametrize("pre,post", org_name, ids=pytest_ids(org_name))
def test_positive_organizations_by_name(pre, post):
    """Test all organizations are existing after upgrade by names

    :id: upgrade-361414af-fb7f-4b7b-bf5a-9b3d9cc82d03

    :expectedresults: All organizations should be retained post upgrade by
        names
    """
    assert pre == post


@pytest.mark.parametrize("pre,post", org_label, ids=pytest_ids(org_label))
def test_positive_organizations_by_label(pre, post):
    """Test all organizations are existing after upgrade by labels

    :id: upgrade-6290b7eb-bf94-453c-9528-8b8de646eb7a

    :expectedresults: All organizations should be retained post upgrade by
        labels
    """
    assert pre == post


@pytest_skip_if_bug_open('bugzilla', 1461455)
@pytest.mark.parametrize("pre,post", org_desc, ids=pytest_ids(org_desc))
def test_positive_organizations_by_description(pre, post):
    """Test all organizations descriptions is retained post upgrade

    :id: upgrade-fc8bb660-eb8f-4df0-a5be-82e51a21d32c

    :expectedresults: All organizations descriptions should be retained post
        upgrade
    """
    assert pre == post
