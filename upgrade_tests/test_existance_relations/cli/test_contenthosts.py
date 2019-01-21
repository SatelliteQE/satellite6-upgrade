"""Upgrade TestSuite for validating Satellite content hosts existence
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
from upgrade_tests.helpers.common import dont_run_to_upgrade, existence
from robozilla.decorators import pytest_skip_if_bug_open
from upgrade_tests.helpers.existence import compare_postupgrade, pytest_ids

# Required Data
component = 'content-host'
ch_name = compare_postupgrade(component, 'name')
ch_errata = compare_postupgrade(component, 'installable errata')


# Tests
@dont_run_to_upgrade(['6.3', '6.4'])
@pytest.mark.parametrize("pre,post", ch_name, ids=pytest_ids(ch_name))
def test_positive_contenthosts_by_name(pre, post):
    """Test all content hosts are existing after upgrade by names

    :id: upgrade-aa92463b-e693-4c30-b0cb-e2cafdab1c7f

    :expectedresults: All content hosts should be retained post upgrade by
        names
    """
    assert existence(pre, post)


@dont_run_to_upgrade(['6.3', '6.4'])
@pytest_skip_if_bug_open('bugzilla', 1461397)
@pytest.mark.parametrize("pre,post", ch_errata, ids=pytest_ids(ch_errata))
def test_positive_installable_erratas_by_name(pre, post):
    """Test all content hosts installable erratas are existing after upgrade

    :id: upgrade-bc40b921-c39b-4cd0-9816-87b53d1af352

    :expectedresults: All chosts installable erratas should be retained post
        upgrade
    """
    assert existence(pre, post)
