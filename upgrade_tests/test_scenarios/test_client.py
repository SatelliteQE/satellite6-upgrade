"""Test for Client related Upgrade Scenario's

:Requirement: Upgraded Satellite

:CaseAutomation: Automated

:CaseLevel: Acceptance

:CaseComponent: CLI

:TestType: Functional

:CaseImportance: High

:Upstream: No
"""
import os
import time

from fabric.api import execute
from nailgun import entities
from unittest2.case import TestCase
from upgrade.helpers.docker import docker_execute_command
from upgrade_tests import post_upgrade, pre_upgrade
from upgrade_tests.helpers.scenarios import (
    create_dict,
    dockerize,
    get_entity_data
)


class Scenario_preupgrade_client_package_installation(TestCase):
    """The test class contains pre and post upgrade scenarios to test if the
    package can be installed on preupgrade client remotely

    Test Steps:

        1. Before Satellite upgrade, Create a content host and register it with
            satellite
        2. Upgrade Satellite and Client
        3. Install package post upgrade on a pre-upgrade client from satellite
        4. Check if the package is installed on the pre-upgrade client
    """
    docker_vm = os.environ.get('DOCKER_VM')
    ak = os.environ.get('RHEV_CLIENT_AK_RHEL7')
    cv = entities.ActivationKey(organization=1).search(
        query={'search': 'name={}'.format(ak)}
    )[0].content_view
    package_name = 'horse'

    @pre_upgrade
    def test_pre_scenario_preclient_package_installation(self):
        """Create product and repo from which the package will be installed
        post upgrade

        :id: preupgrade-eedab638-fdc9-41fa-bc81-75dd2790f7be

        :steps:

            1. Create a content host with existing client ak
            2. Create and sync repo from which the package will be
                installed on content host
            3. Add repo to CV and then in Activation key

        :expectedresults:

            1. The content host is created
            2. The new repo and its product has been added to ak using which
                the content host is created

        """
        rhel7_client = dockerize(distro='rhel7')
        product = entities.Product(
            name='preclient_scenario_product',
            organization=1,
        ).create()
        yum_repo = entities.Repository(
            name='preclient_scenario_repo', product=product
        ).create()
        yum_repo.sync()
        self.cv.repository = [yum_repo]
        cv = self.cv.update(['repository'])
        cv.publish()
        cv = cv.read()  # Published CV with new version
        # Promote CV
        environment = entities.ActivationKey().search(
            query={'search': 'name={}'.format(self.ak)}
        )[0].environment
        cvv = entities.ContentViewVersion(
            id=max([cvv.id for cvv in cv.version])
        ).read()
        cvv.promote(
            data={
                u'environment_id': environment.id,
                u'force': False
            }
        )
        create_dict(
            {self.__class__.__name__: rhel7_client}
        )

    @post_upgrade
    def test_post_scenario_preclient_package_installation(self):
        """Post-upgrade scenario that installs the package on pre-upgrade
        client remotely and then verifies if the package installed

        :id: postupgrade-eedab638-fdc9-41fa-bc81-75dd2790f7be

        :steps: Install package on a pre-upgrade client

        :expectedresults: The package is installed in client
         """
        client = get_entity_data(self.__class__.__name__)
        client_id = entities.Host().search(
            query={'search': 'name={}'.format(client.keys()[0])}
        )[0].id
        entities.Host().install_content(data={
            'organization_id': 1,
            'included': {'ids': [client_id]},
            'content_type': 'package',
            'content': [self.package_name],
        })
        # Validate if that package is really installed
        installed_package = execute(
            docker_execute_command,
            client.values()[0],
            'rpm -q {}'.format(self.package_name),
            host=self.docker_vm
        )[self.docker_vm]
        time.sleep(10)
        self.assertIn(self.package_name, installed_package)


class Scenario_postupgrade_client_package_installation(TestCase):
    """The test class contains post-upgrade scenarios to test if the package
    can be installed on postupgrade client remotely

    Test Steps:

        1. Upgrade Satellite
        2. After Satellite upgrade, Create a content host and register it with
        satellite
        3. Install package a client from satellite
        4. Check if the package is installed on the post-upgrade client
    """
    docker_vm = os.environ.get('DOCKER_VM')
    ak = os.environ.get('RHEV_CLIENT_AK_RHEL7')
    cv = entities.ActivationKey(organization=1).search(
        query={'search': 'name={}'.format(ak)}
    )[0].content_view
    package_name = 'tiger'

    @post_upgrade
    def test_post_scenario_postclient_package_installation(self):
        """Post-upgrade scenario that creates and installs the package on
        post-upgrade client remotely and then verifies if the package installed

        :id: postupgrade-1a881c07-595f-425f-aca9-df2337824a8e

        :steps:

            1. Create a content host with existing client ak
            2. Create and sync repo from which the package will be
                installed on content host
            3. Add repo to CV and then in Activation key
            4. Install package on a pre-upgrade client

        :expectedresults:

            1. The content host is created
            2. The new repo and its product has been added to ak using which
                the content host is created
            3. The package is installed on post-upgrade client
        """
        rhel7_client = dockerize(distro='rhel7')
        product = entities.Product(
            name='postclient_scenario_product',
            organization=1,
        ).create()
        yum_repo = entities.Repository(
            name='postclient_scenario_repo', product=product
        ).create()
        yum_repo.sync()
        self.cv.repository = [yum_repo]
        cv = self.cv.update(['repository'])
        cv.publish()
        cv = cv.read()  # Published CV with new version
        # Promote CV
        environment = entities.ActivationKey().search(
            query={'search': 'name={}'.format(self.ak)}
        )[0].environment
        cvv = entities.ContentViewVersion(
            id=max([cvv.id for cvv in cv.version])
        ).read()
        cvv.promote(
            data={
                u'environment_id': environment.id,
                u'force': False
            }
        )
        client_id = entities.Host().search(
            query={'search': 'name={}'.format(rhel7_client.keys()[0])}
        )[0].id
        entities.Host().install_content(data={
            'organization_id': 1,
            'included': {'ids': [client_id]},
            'content_type': 'package',
            'content': [self.package_name],
        })
        # Validate if that package is really installed
        installed_package = execute(
            docker_execute_command,
            rhel7_client.values()[0],
            'rpm -q {}'.format(self.package_name),
            host=self.docker_vm
        )[self.docker_vm]
        time.sleep(10)
        self.assertIn(self.package_name, installed_package)
