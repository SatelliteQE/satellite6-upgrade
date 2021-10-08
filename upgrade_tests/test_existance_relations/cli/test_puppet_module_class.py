"""Upgrade TestSuite for validating Satellite puppet classes and modules
existence post upgrade

:Requirement: Upgraded Satellite

:CaseAutomation: Automated

:CaseLevel: System

:CaseComponent: Puppet

:TestType: nonfunctional

:CaseImportance: High

:SubType1: installability

:Upstream: No
"""
import pytest

from upgrade_tests.helpers.common import existence
from upgrade_tests.helpers.existence import compare_postupgrade
from upgrade_tests.helpers.existence import pytest_ids

# Required Data
component_class = 'puppet-class'
pc_name = compare_postupgrade(component_class, 'name')


# Tests
@pytest.mark.parametrize("pre,post", pc_name, ids=pytest_ids(pc_name))
def test_positive_puppet_classes_by_name(pre, post):
    """Test all puppet classes are existing after upgrade by names

    :id: upgrade-44e7617c-4092-42bd-9b28-907c034966f7

    :expectedresults: All puppet classes should be retained post upgrade by
        names
    """
    assert existence(pre, post)
