"""Common helper functions to run upgrade existence and scenario tests
"""
import os
import pytest

from functools import partial
from robozilla.decorators import pytest_skip_if_bug_open
from upgrade_tests.helpers.variants import assert_varients
from upgrade_tests.helpers.existence import assert_templates

cur_ver = os.environ.get('FROM_VERSION')
to_ver = os.environ.get('TO_VERSION')


class VersionException(Exception):
    """Version Exception if wrong satellite version provided"""
    pass


pytest_skip_if_bug_open = partial(
        pytest_skip_if_bug_open)


def existence(pre, post, component=None, template=None):
    """Returns test result according to pre and post value

    Result Types:
    ```
    1. Fails the test with reason if 'missing' keyword found in pre or post
    value
    2. If 'component' is provided then it alternates the result of assert if
    the value of entity attribute is 'expected' to change during upgrade.
    visit def `assert_variants` for more details
    3. If 'template' is provided then it calls helpers for foreman templates comparision,
    also the preupgrade and postupgrade templates needs to be available.
    This option is only for template.py template existence tests.
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
    :param template: The foreman template type for template comparision
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
    elif template and not post == 'true':
        return assert_templates(template, pre, post)
    else:
        if isinstance(pre, list) and isinstance(post, list):
            return sorted(list(pre)) == sorted(list(post))
        return pre == post


def dont_run_to_upgrade(versions):
    """Decorator on test definition to not to run that test on given 'versions'

    Usage:

    * If '6.1' in versions, then the test will not run while upgrading from 6.1
    * If '6.2'in versions, then the test will not run while upgrading from 6.2
    * If this decorator is not called on test def, then the test will run on
        all versions

    Example:

        Following test will not run when upgrading from 6.2,
        in short when FROM_VERSION = 6.2

        @dont_run_to_upgrade('6.2')
        def test_something():
            # Do test related things

    Environment Variable:

    FROM_VERSION
        Current satellite version which will be upgraded to next version

    :param str/list versions: The sat versions onto which the test wont run
    :return: If FROM_VERSION is in versions then pytests skips test
    """
    allowed_versions = ('6.0', '6.1', '6.2', '6.3', '6.4')
    if cur_ver not in allowed_versions:
        raise VersionException(
            'Wrong sat version provided in FROM VERSION env var. Provide one '
            'of {}'.format(allowed_versions))
    versions = [versions] if type(versions) is str else versions
    for version in versions:
        if version not in allowed_versions:
            raise VersionException(
                'Wrong sat version provided to run this test. Provide one of '
                '{}'.format(allowed_versions))
    return pytest.mark.skipif(
        cur_ver in versions, reason='Not for version {}'.format(cur_ver))
