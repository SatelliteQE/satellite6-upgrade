"""Upgrade TestModule for validating remote execution features existence and their
associations after upgrade

:Requirement: Upgraded Satellite

:CaseAutomation: Automated

:CaseLevel: System

:CaseComponent: Remote Execution Feature

:TestType: nonfunctional

:CaseImportance: High

:Upstream: No
"""
import pytest

from upgrade_tests.helpers.common import existence
from upgrade_tests.helpers.existence import compare_postupgrade
from upgrade_tests.helpers.existence import pytest_ids


# Required Data
component = 'remote-execution-feature'
rex_feature_name = compare_postupgrade(component, 'name')
rex_feature_id = compare_postupgrade(component, 'id')
rex_feature_description = compare_postupgrade(component, 'description')
rex_feature_job_template_name = compare_postupgrade(component, 'job template name')


@pytest.mark.parametrize("pre,post", rex_feature_name, ids=pytest_ids(rex_feature_name))
def test_positive_rem_execution_feature_name(pre, post):
    """Test all remote execution feature's by name after post upgrade

    :id: upgrade-4f7b49e6-3e73-41a4-b99b-a683c2903a62

    :expectedresults: All remote-execution-feature name should be retained after post upgrade
    """
    assert existence(pre, post)


@pytest.mark.parametrize("pre,post", rex_feature_id, ids=pytest_ids(rex_feature_id))
def test_positive_rem_execution_feature_id(pre, post):
    """Test all remote execution feature's id existence after post upgrade"

    :id: upgrade-f36ce1c6-29af-44a0-9364-c9ec24d4592e

    :expectedresults: All remote execution feature's id should be retained after post upgrade
    """
    assert existence(pre, post)


@pytest.mark.parametrize("pre,post", rex_feature_description,
                         ids=pytest_ids(rex_feature_description))
def test_positive_rem_execution_feature_description(pre, post):
    """Test all remote execution feature's description existence after post upgrade"

    :id: upgrade-ce161736-ee98-46b9-b4b6-e1f2f35544cb

    :expectedresults: All remote execution feature's description should be retained
                      after post upgrade.
    """
    assert existence(pre, post)


@pytest.mark.parametrize("pre,post", rex_feature_job_template_name,
                         ids=pytest_ids(rex_feature_job_template_name))
def test_positive_rem_execution_feature_job_template_name(pre, post):
    """Test all policy remote execution feature's job template name after post upgrade"

    :id: upgrade-c0b0fdd5-e0b0-406e-b4a7-50dc04f9ba66

    :expectedresults: All remote execution feature's job template name should be retained
                      after post upgrade.
    """
    assert existence(pre, post)
