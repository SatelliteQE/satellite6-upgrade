"""Upgrade TestSuite for validating Satellite partition tables existence
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
from upgrade_tests.helpers.existence import compare_postupgrade, pytest_ids

# Required Data
component = 'partition-table'
ptable_name = compare_postupgrade(component, 'name')


# Tests
@pytest.mark.parametrize("pre,post", ptable_name, ids=pytest_ids(ptable_name))
def test_positive_partition_tables_by_name(pre, post):
    """Test all partition tables are existing after upgrade by names

    :id: upgrade-7832ab52-75e5-4451-aee3-5b208ced0e67

    :expectedresults: All architectures should be retained post upgrade by
        names
    """
    assert pre == post
