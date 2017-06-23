# -*- encoding: utf-8 -*-
"""Test for Upgrade Scenario's

:Requirement: Satellite upgrade

:CaseAutomation: Automated

:CaseLevel: Acceptance

:CaseComponent: CLI

:TestType: Functional

:CaseImportance: High

:Upstream: No
"""
import os
import time

from automation_tools.satellite6 import hammer
from fabric.api import env, execute, run, task
from fauxfactory import gen_alpha
from unittest2.case import TestCase

from upgrade.helpers.docker import (
    docker_execute_command,
    refresh_subscriptions_on_docker_clients
)
from upgrade_tests import post_upgrade, pre_upgrade
from upgrade_tests.helpers.scenarios import (
    create_dict,
    dockerize,
    get_entity_data,
    get_satellite_host,
    rpm1,
    rpm2
)


class ScenarioBug1429201(TestCase):
    """This Class will serve as a whole scenario with pre-upgrade and
    post-upgrade test-case.
    Scenario test to verify if we can create a custom repository and consume it
    via client then we alter the created custom repository and satellite
    will be able to sync back the repo.
    """
    prd_name = 'ScenarioBug1429201' + gen_alpha()
    repo_name = 'ScenarioBug1429201' + gen_alpha()
    lc_name = 'ScenarioBug1429201' + gen_alpha()
    ak_name = 'ScenarioBug1429201' + gen_alpha()
    cv_name = 'ScenarioBug1429201' + gen_alpha()
    docker_vm = os.environ.get('DOCKER_VM')
    org_id = 1
    sat_host = get_satellite_host()
    file_path = '/var/www/html/pub/custom_repo/'
    custom_repo = 'https://' + sat_host + '/pub/custom_repo/'
    _, rpm1_name = os.path.split(rpm1)
    _, rpm2_name = os.path.split(rpm2)

    def setUp(self):
        hammer.set_hammer_config()
        env.host_string = self.sat_host
        env.user = 'root'

    @task
    def create_repo(self):
        """ Creates a custom yum repository, that will be synced to satellite
        """
        try:
            run('rm -rf {0}'.format(self.file_path))
            run('mkdir {0}'.format(self.file_path))
        except OSError:
            run('mkdir /var/www/html/pub/custom_repo')
        run('wget {0} -P {1}'.format(rpm1, self.file_path))
        run('createrepo --database {0}'.format(self.file_path))

    @pre_upgrade
    def test_pre_user_scenario_bug_1429201(self):
        """This is pre-upgrade scenario test to verify if we can create a
         custom repository and consume it via client

         :id: 8fb8ec87-efa5-43ed-8cb3-960ef9cd6df2

         :steps:
             1. Create repository RepoFoo that you will later add to your
                Satellite. This repository should contain PackageFoo-1.0.rpm
             2. Install satellite 6.1
             3. Create custom product ProductFoo pointing to repository RepoFoo
             4. Sync RepoFoo
             5. Create content view CVFoo
             6. Add RepoFoo to CVFoo
             7. Publish version 1 of CVFoo

         :expectedresults: The client and product is created successfully

         :BZ: 1429201
         """
        execute(self.create_repo, self, host=self.sat_host)
        # End to End product + ak association
        print hammer.hammer_product_create(self.prd_name, self.org_id)
        print hammer.hammer_repository_create(
            self.repo_name,
            self.org_id,
            self.prd_name,
            self.custom_repo
            )

        print hammer.hammer(
            'lifecycle-environment create --name "{0}" '
            '--organization-id {1} --prior-id "{2}"'.format(
                                                        self.lc_name,
                                                        self.org_id,
                                                        1
                                                        )
                )
        print hammer.hammer_repository_synchronize(
            self.repo_name,
            self.org_id,
            self.prd_name
            )
        print hammer.hammer_content_view_create(self.cv_name, self.org_id)
        print hammer.hammer_content_view_add_repository(
            self.cv_name,
            self.org_id,
            self.prd_name,
            self.repo_name
            )
        print hammer.hammer_content_view_publish(self.cv_name, self.org_id)
        latest_repo_version = hammer.get_latest_cv_version(self.cv_name)
        lc_result = hammer.hammer(
            '"{0}" info --name "{1}" --organization-id '
            '{2}'.format('lifecycle-environment',
                         self.lc_name,
                         self.org_id
                         )
                                  )
        lifecycle_id = hammer.get_attribute_value(
            lc_result,
            self.lc_name,
            'id'
            )
        print hammer.hammer_content_view_promote_version(
            self.cv_name,
            latest_repo_version,
            lifecycle_id,
            self.org_id
            )
        print hammer.hammer_activation_key_create(
            self.ak_name,
            self.org_id,
            self.cv_name,
            self.lc_name
            )
        print hammer.hammer_activation_key_add_subscription(
            self.ak_name,
            self.org_id,
            self.prd_name
            )
        time.sleep(5)
        # Creating a rhel7 vm and subscribing to AK
        container_ids = dockerize(self.ak_name, 'rhel7')
        time.sleep(30)  # Subscription manager needs time to register
        result = execute(
            docker_execute_command,
            container_ids.values()[0],
            'yum list {0} | grep {0}'.format(self.rpm1_name.split('-')[0]),
            host=self.docker_vm
            )
        # Info on created entities to assert the test case using hammer info
        prd_info = hammer.hammer(
            '"{0}" info --name "{1}" --organization-id '
            '{2}'.format('product', self.prd_name, self.org_id)
        )
        self.assertEqual(
            self.prd_name,
            hammer.get_attribute_value(prd_info, self.prd_name, 'name')
        )
        self.assertIsNotNone(container_ids)
        self.assertIn(self.repo_name, result.values()[0])
        global_dict = {self.__class__.__name__: {
            'prd_name': self.prd_name,
            'ak_name': self.ak_name,
            'repo_name': self.repo_name,
            'container_ids': container_ids
        }
        }
        create_dict(global_dict)

    @post_upgrade
    def test_post_user_scenario_bug_1429201(self):
        """This is post-upgrade scenario test to verify if we can alter the
        created custom repository and satellite will be able to sync back
        the repo

        :id: 9415c3e5-4699-462f-81bc-4143d8b820f1

        :steps:
            1. Remove PackageFoo-1.0.rpm from RepoFoo
            2. Add PackageFoo-2.0.rpm to RepoFoo
            3. Sync RepoFoo
            4. Publish version 2 of CVFoo
            5. Delete version 1 of CVFoo
            6. run /etc/cron.weekly/katello-remove-orphans
            7. Subscribe ClientA to CVFoo
            8. Try to install PackageFoo-1.0.rpm on ClientA
            9. Notice that yum thinks it's there based on the repo metadata
               but then fails to download it with 404
            10. Try to install PackageFoo-2.0.rpm

        :expectedresults: The clients is present after upgrade and deleted
            rpm is unable to be fetched, while new rpm is pulled and installed
            on client

        :BZ: 1429201
        """
        entity_data = get_entity_data(self.__class__.__name__)
        run('wget {0} -P {1}'.format(rpm2, self.file_path))
        run('rm -rf {0}'.format(self.file_path + self.rpm1_name))
        run('createrepo --update {0}'.format(self.file_path))
        # get entities from pickle
        pkcl_ak_name = entity_data['ak_name']
        container_ids = entity_data['container_ids']
        repo_name = entity_data['repo_name']
        prd_name = entity_data['prd_name']
        cv_name, lc_name = hammer.hammer_determine_cv_and_env_from_ak(
            pkcl_ak_name,
            self.org_id
        )
        # Info on created entities to assert the test case using hammer info
        ak_info = hammer.hammer(
            '"{0}" info --name "{1}" --organization-id '
            '{2}'.format('activation-key', pkcl_ak_name, self.org_id)
        )
        print hammer.hammer_repository_synchronize(
            repo_name,
            self.org_id,
            prd_name
        )
        print hammer.hammer_content_view_publish(cv_name, self.org_id)
        latest_repo_version = hammer.get_latest_cv_version(cv_name)

        result = hammer.hammer(
            '"{0}" info --name "{1}" --organization-id '
            '{2}'.format('lifecycle-environment', lc_name, self.org_id)
        )
        lifecycle_id = hammer.get_attribute_value(result, lc_name, 'id')
        print hammer.hammer_content_view_promote_version(
            cv_name,
            latest_repo_version,
            lifecycle_id,
            self.org_id
        )

        hammer.hammer(
            'content-view remove --content-view-version-ids {0}'
            ' --name "{1}" --organization-id {2}'.format(
                latest_repo_version,
                cv_name,
                self.org_id
            )
        )
        run('/etc/cron.weekly/katello-remove-orphans')
        execute(refresh_subscriptions_on_docker_clients,
                container_ids.values(),
                host=self.docker_vm
                )
        time.sleep(30)  # Subscription manager needs time to register
        result_fail = execute(
            docker_execute_command,
            container_ids.values()[0],
            'yum list {0} | grep {0}'.format(self.rpm1_name.split('-')[0]),
            quiet=True,
            host=self.docker_vm
        )  # should be error
        result_pass = execute(
            docker_execute_command,
            container_ids.values()[0],
            'yum install -y {0}'.format(self.rpm2_name.split('-')[0]),
            host=self.docker_vm
        )  # should be successful
        self.assertEqual(
            pkcl_ak_name,
            hammer.get_attribute_value(ak_info, pkcl_ak_name, 'name')
        )
        self.assertIsNotNone(container_ids)
        self.assertIn('Error', result_fail.values()[0])
        self.assertIn('Complete', result_pass.values()[0])


class Scenario_capsule_sync(TestCase):
    """The test class contains pre-upgrade and post-upgrade scenarios to test if
    package added to satellite preupgrade is synced to capsule post upgrade.

    Test Steps:

    1. Before Satellite upgrade, Sync a repo/rpm in satellite.
    2. Upgrade satellite/capsule.
    3. Run capsule sync post upgrade.
    4. Check if the repo/rpm is been synced to capsule.

    """
    cls_name = 'Scenario_capsule_sync'
    sat_host = get_satellite_host()
    env.host_string = sat_host
    env.user = 'root'
    hammer.set_hammer_config()
    repo_name = 'capsulesync_TestRepo_' + cls_name
    repo_path = '/var/www/html/pub/preupgradeCapSync_repo/'
    rpm_name = rpm1.split('/')[-1]
    prod_name = 'Scenario_preUpgradeCapSync_' + cls_name
    activation_key = os.environ.get(
        'CAPSULE_AK', os.environ.get('RHEV_CAPSULE_AK'))
    cv_name = 'Scenario_precapSync_' + cls_name
    _, env_name = hammer.hammer_determine_cv_and_env_from_ak(
        activation_key, '1')
    org_id = '1'
    repo_url = 'http://' + sat_host + '/pub/preupgradeCapSync_repo/'

    def create_repo(self):
        """ Creates a custom yum repository, that will be synced to satellite
        and later to capsule from satellite
        """
        run('rm -rf {}'.format(self.repo_path))
        run('mkdir {}'.format(self.repo_path))
        run('wget {0} -P {1}'.format(rpm1, self.repo_path))
        # Renaming custom rpm to preRepoSync.rpm
        run('createrepo --database {0}'.format(self.repo_path))

    @pre_upgrade
    def test_pre_user_scenario_capsule_sync(self):
        """Pre-upgrade scenario that creates and sync repository with
        rpm in satellite which will be synced in post upgrade scenario.


        :id: preupgrade-eb8970fa-98cc-4a99-99fb-1c12c4e319c9

        :steps:
            1. Before Satellite upgrade, Sync a repo/rpm in satellite.

        :expectedresults: The repo/rpm should be synced to satellite

         """
        self.create_repo()
        print hammer.hammer_product_create(self.prod_name, self.org_id)
        prod_list = hammer.hammer(
            'product list --organization-id {}'.format(self.org_id))
        self.assertEqual(
            self.prod_name,
            hammer.get_attribute_value(prod_list, self.prod_name, 'name')
        )
        print hammer.hammer_repository_create(
            self.repo_name, self.org_id, self.prod_name, self.repo_url)
        repo_list = hammer.hammer(
            'repository list --product {0} --organization-id {1}'.format(
                self.prod_name, self.org_id))
        self.assertEqual(
            self.repo_name,
            hammer.get_attribute_value(repo_list, self.repo_name, 'name')
        )
        print hammer.hammer_repository_synchronize(
            self.repo_name, self.org_id, self.prod_name)
        print hammer.hammer_content_view_create(self.cv_name, self.org_id)
        print hammer.hammer_content_view_add_repository(
            self.cv_name, self.org_id, self.prod_name, self.repo_name)
        print hammer.hammer_content_view_publish(self.cv_name, self.org_id)
        cv_ver = hammer.get_latest_cv_version(self.cv_name)
        env_data = hammer.hammer(
            'lifecycle-environment list --organization-id {0} '
            '--name {1}'.format(self.org_id, self.env_name))
        env_id = hammer.get_attribute_value(
            env_data,
            self.env_name,
            'id'
        )
        print hammer.hammer_content_view_promote_version(
            self.cv_name, cv_ver, env_id, self.org_id)
        global_dict = {self.__class__.__name__: {
            'rpm_name': self.rpm_name}}
        create_dict(global_dict)

    @post_upgrade
    def test_post_user_scenario_capsule_sync(self):
        """Post-upgrade scenario that sync capsule from satellite and then
        verifies if the repo/rpm of pre-upgrade scenario is synced to capsule


        :id: postupgrade-eb8970fa-98cc-4a99-99fb-1c12c4e319c9

        :steps:
            1. Run capsule sync post upgrade.
            2. Check if the repo/rpm is been synced to capsule.

        :expectedresults:
            1. The capsule sync should be successful
            2. The repos/rpms from satellite should be synced to satellite

         """
        cap_host = os.environ.get(
            'RHEV_CAP_HOST',
            os.environ.get('CAPSULE_HOSTNAME')
        )
        cap_data = hammer.hammer('capsule list')
        cap_id = hammer.get_attribute_value(cap_data, cap_host, 'id')
        cap_info = {'id': cap_id, 'name': cap_host}
        org_data = hammer.hammer('organization list')
        org_name = hammer.get_attribute_value(
            org_data, int(self.org_id), 'name')
        print hammer.sync_capsule_content(cap_info, async=False)
        result = execute(
            lambda: run(
                '[ -f /var/lib/pulp/published/yum/http/repos/'
                '{0}/{1}/{2}/custom/{3}/{4}/{5} ]; echo $?'.format(
                    org_name, self.env_name, self.cv_name,
                    self.prod_name, self.repo_name, self.rpm_name)),
            host=cap_host
        )[cap_host]
        self.assertEqual('0', result)


class Scenario_capsule_sync_2(TestCase):
    """
    The test class contains pre-upgrade and post-upgrade scenarios to test if
    package added postupgrade in satellite is snyced to capsule post upgrade.

    Test Steps:

    1. Upgrade Satellite and Capsule.
    2. Sync a repo/rpm in satellite.
    3. Run capsule sync.
    4. Check if the repo/rpm is been synced to capsule.

    """
    cls_name = 'Scenario_capsule_sync_2'
    sat_host = get_satellite_host()
    env.host_string = sat_host
    env.user = 'root'
    hammer.set_hammer_config()
    repo_name = 'capsulesync_TestRepo_' + cls_name
    repo_path = '/var/www/html/pub/postupgradeCapSync_repo/'
    rpm_name = rpm2.split('/')[-1]
    prod_name = 'Scenario_postUpgradeCapSync_' + cls_name
    activation_key = os.environ.get(
        'CAPSULE_AK', os.environ.get('RHEV_CAPSULE_AK'))
    cv_name = 'Scenario_postcapSync_' + cls_name
    _, env_name = hammer.hammer_determine_cv_and_env_from_ak(
        activation_key, '1')
    org_id = '1'
    repo_url = 'http://' + sat_host + '/pub/postupgradeCapSync_repo/'

    def create_repo(self):
        """ Creates a custom yum repository, that will be synced to satellite
        and later to capsule from satellite
        """
        run('rm -rf {}'.format(self.repo_path))
        run('mkdir {}'.format(self.repo_path))
        run('wget {0} -P {1}'.format(rpm2, self.repo_path))
        # Renaming custom rpm to preRepoSync.rpm
        run('createrepo --database {0}'.format(self.repo_path))

    @post_upgrade
    def test_post_user_scenario_capsule_sync_2(self):
        """Post-upgrade scenario that creates and sync repository with
        rpm, sync capsule with satellite and verifies if the repo/rpm in
        satellite is synced to capsule.


        :id: postupgrade-7c1d3441-3e8d-4ac2-8102-30e18274658c

        :steps:
            1. Post Upgrade , Sync a repo/rpm in satellite.
            2. Run capsule sync.
            3. Check if the repo/rpm is been synced to capsule.

        :expectedresults:
            1. The repo/rpm should be synced to satellite
            2. Capsule sync should be successful
            3. The repo/rpm from satellite should be synced to capsule

        """
        self.create_repo()
        print hammer.hammer_product_create(self.prod_name, self.org_id)
        prod_list = hammer.hammer(
            'product list --organization-id {}'.format(self.org_id))
        self.assertEqual(
            self.prod_name,
            hammer.get_attribute_value(prod_list, self.prod_name, 'name')
        )
        print hammer.hammer_repository_create(
            self.repo_name, self.org_id, self.prod_name, self.repo_url)
        repo_list = hammer.hammer(
            'repository list --product {0} --organization-id {1}'.format(
                self.prod_name, self.org_id))
        self.assertEqual(
            self.repo_name,
            hammer.get_attribute_value(repo_list, self.repo_name, 'name')
        )
        print hammer.hammer_repository_synchronize(
            self.repo_name, self.org_id, self.prod_name)
        print hammer.hammer_content_view_create(self.cv_name, self.org_id)
        print hammer.hammer_content_view_add_repository(
            self.cv_name, self.org_id, self.prod_name, self.repo_name)
        print hammer.hammer_content_view_publish(self.cv_name, self.org_id)
        cv_ver = hammer.get_latest_cv_version(self.cv_name)
        env_data = hammer.hammer(
            'lifecycle-environment list --organization-id {0} '
            '--name {1}'.format(self.org_id, self.env_name))
        env_id = hammer.get_attribute_value(
            env_data,
            self.env_name,
            'id'
        )
        print hammer.hammer_content_view_promote_version(
            self.cv_name, cv_ver, env_id, self.org_id)
        cap_host = os.environ.get(
            'RHEV_CAP_HOST',
            os.environ.get('CAPSULE_HOSTNAME')
        )
        cap_data = hammer.hammer('capsule list')
        cap_id = hammer.get_attribute_value(cap_data, cap_host, 'id')
        cap_info = {'id': cap_id, 'name': cap_host}
        org_data = hammer.hammer('organization list')
        org_name = hammer.get_attribute_value(
            org_data, int(self.org_id), 'name')
        print hammer.sync_capsule_content(cap_info, async=False)
        result = execute(
            lambda: run('[ -f /var/lib/pulp/published/yum/http/repos/'
                        '{0}/{1}/{2}/custom/{3}/{4}/{5} ]; echo $?'.format(
                            org_name, self.env_name, self.cv_name,
                            self.prod_name, self.repo_name, self.rpm_name)),
            host=cap_host
        )[cap_host]
        self.assertEqual('0', result)
