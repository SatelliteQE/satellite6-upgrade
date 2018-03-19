"""Common helper functions to run upgrade existence and scenario tests
"""
import os
import pytest

cur_ver = os.environ.get('FROM_VERSION')


class VersionException(Exception):
    """Version Exception if wrong satellite version provided"""
    pass


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
    allowed_versions = ('6.0', '6.1', '6.2', '6.3')
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
