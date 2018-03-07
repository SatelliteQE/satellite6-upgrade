"""Common helper functions to run upgrade existence and scenario tests
"""
import os
import pytest

from functools import partial
from robozilla.decorators import pytest_skip_if_bug_open
from upgrade_tests.helpers.variants import assert_varients

cur_ver = os.environ.get('FROM_VERSION')
to_ver = os.environ.get('TO_VERSION')


class VersionException(Exception):
    """Version Exception if wrong satellite version provided"""
    pass


pytest_skip_if_bug_open = partial(
        pytest_skip_if_bug_open)


def existence(pre, post, component=None):
    """Returns test result according to pre and post value

    Result Types:
    ```
    1. Fails the test with reason if 'missing' keyword found in pre or post
    value
    2. If 'component' is provided then it alternates the result of assert if
    the value of entity attribute is 'expected' to change during upgrade.
    visit def `assert_variants` for more details
    3. Finally If nothing from above, then plain comparision and return results
    ```

    Note:
    ```
    If your are sure that the component attribute name varies between sat
    versions, then Its mandatory to pass component parameter to this function
    while calling.

     e.g:
     def test_anyentity(pre, post)
        assert existence(pre, post, component='entity_name')
    This internally calls assert_variants function.
    ```

    :param pre: Pre-upgrade value from test
    :param post: Post-upgrade Value from test
    :param component: The satellite component name for which the attribute name
     differs
    :return: Returns pytest.fail or Boolean value according to pre-upgrade and
     post-upgrade value
    """
    if isinstance(pre, str) or isinstance(pre, int):
        pre = str(pre)
        post = str(post)
    if ('missing' in pre) or ('missing' in post):
            pytest.fail(msg='{0}{1}'.format(pre, post))
    elif component:
        return assert_varients(component, pre, post)
    else:
        return pre == post


def run_to_upgrade(version):
    """Decorator on test definition to run that test on given 'version' only.

    Usage:

    * If version is '6.1', then the test will run while upgrading from 6.1 only
    * If version is '6.2', then the test will run while upgrading from 6.2 only
    * If this decorator is not called on test def, then the test will run on
        all versions

    Example:

        Following test will run only when upgrading from 6.2,
        in short when FROM_VERSION = 6.2

        @run_to_upgrade('6.2')
        def test_something():
            # Do test related things

    Environment Variable:

    FROM_VERSION
        Current satellite version which will be upgraded to next version

    :param str version: The satellite version only on which the test will run
    :return: If the version and FROM_VERSION doesnt matches then
        pytests skip test
    """
    allowed_versions = ('6.0', '6.1', '6.2')
    if version not in allowed_versions:
        raise VersionException(
            'Wrong sat version provided to run this test. Provide one of '
            '{}'.format(allowed_versions))
    if cur_ver not in allowed_versions:
        raise VersionException(
            'Wrong sat version provided in FROM VERSION env var. Provide one '
            'of {}'.format(allowed_versions))
    return pytest.mark.skipif(
        version != cur_ver, reason='Not for version {}'.format(cur_ver))
