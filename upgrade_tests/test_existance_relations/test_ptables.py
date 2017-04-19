"""Upgrade TestSuite for validating Satellite partition tables existence
post upgrade

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


@pytest.mark.parametrize(
    "pre,post",
    compare_postupgrade('partition-table', 'name')
)
def test_positive_partition_tables_by_name(pre, post):
    """Test all partition tables are existing after upgrade by names

    :id: 7832ab52-75e5-4451-aee3-5b208ced0e67

    :expectedresults: All architectures should be retained post upgrade by
        names
    """
    assert pre == post
