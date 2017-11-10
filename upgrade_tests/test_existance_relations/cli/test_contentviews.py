"""Upgrade TestSuite for validating Satellite CVs existence and
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
from upgrade_tests.helpers.common import run_to_upgrade
from upgrade_tests.helpers.existence import compare_postupgrade, pytest_ids

# Required Data
component = 'content-view'
cvs_repo = compare_postupgrade(component, 'repository ids')
cvs_label = compare_postupgrade(component, 'label')
cvs_composite = compare_postupgrade(component, 'composite')
cvs_name = compare_postupgrade(component, 'name')


# Tests
@pytest_skip_if_bug_open('bugzilla', 1461026)
@pytest.mark.parametrize("pre,post", cvs_repo, ids=pytest_ids(cvs_repo))
def test_positive_cvs_by_repository_ids(pre, post):
    """Test repository associations of all CVs post upgrade

    :id: upgrade-c8da27df-7d96-44b7-ab2a-d23a56ea2b2b

    :expectedresults: Repositories associations of each CV should be retained
        post upgrade
    """
    if ',' in pre:
        pre = sorted([num.strip() for num in pre.split(',')])
    if ',' in post:
        post = sorted([num.strip() for num in post.split(',')])
    assert pre == post


@pytest.mark.parametrize("pre,post", cvs_label, ids=pytest_ids(cvs_label))
def test_positive_cvs_by_label(pre, post):
    """Test all CVs are existing after upgrade by their labels

    :id: upgrade-9a541a98-c4b1-417c-9bfd-c65aadd72afb

    :expectedresults: All CVs should be retained post upgrade
    """
    assert pre == post


@run_to_upgrade('6.2')
@pytest.mark.parametrize(
    "pre,post", cvs_composite, ids=pytest_ids(cvs_composite))
def test_positive_cvs_by_composite_views(pre, post):
    """Test composite CV's are existing after upgrade

    :id: upgrade-554632f2-0e5b-44c8-9a80-5463302af22f

    :expectedresults: All composite CVs should be retained post upgrade
    """
    assert pre == post


@pytest.mark.parametrize("pre,post", cvs_name, ids=pytest_ids(cvs_name))
def test_positive_cvs_by_name(pre, post):
    """Test all CVs are existing after upgrade by their name

    :id: upgrade-7ad53fb0-f05c-4eea-bd6c-db6c35ea8841

    :expectedresults: All CVs should be retained post upgrade by their name
    """
    assert pre == post
