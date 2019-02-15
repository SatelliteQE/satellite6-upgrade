"""Upgrade TestSuite for validating Satellite provisioning templates existence
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
from upgrade_tests.helpers.common import existence
from upgrade_tests.helpers.existence import compare_postupgrade, compare_templates, pytest_ids

# Required Data
component = 'template'
temp_name = compare_postupgrade(component, 'name')
ptables_templates = compare_templates('partition-table')
job_templates = compare_templates('job-template')
provi_templates = compare_templates('template')


# Tests
@pytest.mark.parametrize("pre,post", temp_name, ids=pytest_ids(temp_name))
def test_positive_templates_by_name(pre, post):
    """Test all templates are existing after upgrade by names

    :id: upgrade-fce33637-8e7b-4ccf-a9fb-47f0e0607f83

    :expectedresults: All templates should be retained post upgrade by names
    """
    assert existence(pre, post, component)


@pytest.mark.parametrize("pre, post", ptables_templates, ids=pytest_ids(ptables_templates))
def test_positive_partitiontable_templates(pre, post):
    """Test all ptable templates contents are migrated as expected

    :id: upgrade-33f1b9ce-5c18-41eb-a41f-dad2ff0429f6

    :expectedresults: All ptable templates contents are migrated successfully
    """
    assert existence(pre, post, template='partition-table')


@pytest.mark.parametrize("pre, post", provi_templates, ids=pytest_ids(provi_templates))
def test_positive_provisioning_templates(pre, post):
    """Test all provisioning templates contents are migrated as expected

    :id: upgrade-2c487815-8b8a-4f72-9e7a-d068277d60a0

    :expectedresults: All provisioning templates contents are migrated successfully
    """
    assert existence(pre, post, template='template')


@pytest.mark.parametrize("pre, post", job_templates, ids=pytest_ids(job_templates))
def test_positive_job_templates(pre, post):
    """Test all job templates contents are migrated as expected

    :id: upgrade-af98116e-5c01-46fa-8ca8-05fc85e77ff3

    :expectedresults: All job templates contents are migrated successfully
    """
    assert existence(pre, post, template='job-template')
