"""Upgrade TestSuite for validating Satellite locations existence and
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
component = "location"
loc_id = compare_postupgrade(component, 'id')
loc_name = compare_postupgrade(component, 'name')
loc_desc = compare_postupgrade(component, 'description')
loc_title = compare_postupgrade(component, 'title')


# Tests
@pytest.mark.parametrize("pre,post", loc_id, ids=pytest_ids(loc_id))
def test_positive_locations_by_id(pre, post):
    """Test all locations are existing after upgrade by id's

    :id: upgrade-d16b33af-46b3-4413-b018-e7a4926c8bcc

    :expectedresults: All locations should be retained post upgrade by id's
    """
    assert existence(pre, post)


@pytest.mark.parametrize("pre,post", loc_name, ids=pytest_ids(loc_name))
def test_positive_locations_by_name(pre, post):
    """Test all locations are existing after upgrade by names

    :id: upgrade-613e51e8-3078-4857-9816-21916b936611

    :expectedresults: All locations should be retained post upgrade by names
    """
    assert existence(pre, post)


@pytest.mark.parametrize("pre,post", loc_desc, ids=pytest_ids(loc_desc))
def test_positive_locations_by_desc(pre, post):
    """Test all locations description are retained post upgrade

    :id: upgrade-f509abdf-f9d0-409e-a823-68a2a879ba68

    :expectedresults: All locations description are retained post upgrade
    """
    assert existence(pre, post)


@pytest.mark.parametrize("pre,post", loc_title, ids=pytest_ids(loc_title))
def test_positive_locations_by_title(pre, post):
    """Test all locations are existing after upgrade by title

    :id: upgrade-e5b3afac-1971-416d-94e8-a22f40be37b2

    :expectedresults: All locations should be retained post upgrade by title
    """
    assert existence(pre, post)
