# Satellite6-upgrade

Satellite6 upgrade contains a set of tools that helps to perform various upgrade specific scenarios and
moreover, it helps to validate data between pre and post upgrade to ensure data integrity after upgrade.

**The major tasks of Satellite6 upgrade are:**

1. Create and delete satellite/capsule instances using RHEVM templates/Openstack images
2. Upgrade Satellite6, Capsule instances spawn from RHEVM templates and
clients generated through docker
3. In case user has its own existing satellite/capsule and clients setup and wants to perform upgrade then
Satellite6 upgrade has the capability to perform upgrade on user provided setups
4. Performs data validation post upgrade to ensure the entities created before upgrade
exists post upgrade as well

**Supported Upgrade Paths are:**

Product | Major Version | zStream
--------|----------------|---------
Satellite| 6.1 -> 6.2 and 6.2-> 6.3  | 6.1 -> 6.1 and 6.2 -> 6.2
Capsule | 6.1 -> 6.2 and 6.2-> 6.3 | 6.1 -> 6.1 and 6.2 -> 6.2
Clients | 6.1 -> 6.2 and 6.2-> 6.3 | 6.1 -> 6.1 and 6.2 -> 6.2

## Installation

 Satellite6-Upgrade depends on ```pycurl``` being installed, but installing it,
 specially on a virtual environment is not straight forward. You must run the
 [pycurl install script](https://github.com/SatelliteQE/robottelo-ci/blob/master/scripts/pip-install-pycurl.sh) in order to have ```pycurl``` installed properly.
 
Finally, python packages listed in ```requirements.txt``` must be installed before
satellite6-upgrade can be used:

    pip install -r requirements.txt

## Basic Usage Examples

### Create Satellite/Capsule Instance from RHEVM template
To create a live satellite/capsule instance from RHEVM template:
*Pre-Conditions: The template should have a satellite/capsule populated in it already.*

    RHEV_USER=<user@domain> RHEV_PASSWD=<passwd> RHEV_URL='https://<rhev_url:port>/api'
    fab create_rhevm_instance:<new_instance_name>,<template_name>,<datacenter>,<quota>,
    <cluster>,<timeout_in_minutes>

### Delete Satellite/Capule Instance from RHEVM template
To delete a satellite/capsule instance from RHEVM template:
*Pre-Condition - The instance should be already created*

    RHEV_USER=<user@domain> RHEV_PASSWD=<passwd> RHEV_URL='https://<rhev_url:port>/api'
    fab delete_rhevm_instance:<new_instance_name>,<timeout_in_minutes>

## Upgrade

**Following are the upgrade type we support:**

1. Satellite
    * Upgrades only Satellite and NOT its capsule nor clients
2. Capsule
    * Upgrades Capsule and its associated Satellite and NOT clients
3. Clients
    * Upgrades Clients and its associated Satellite and NOT capsule
4. Longrun
    * Upgrades Satellite, Capsules and clients

We would need different environment variables and fab commands depends on Upgrade Types.

As we look in usage examples above, the command is consisted of mainly two parts:
1. ```Environment variables```
Again, environment variables required for each upgrade type has been divided into
parts and its subparts, those are:
    * Common Environment Variables required for all types of upgrade
    * Environment Variables required for specific type of upgrade
        * Downstream Environment Variables
        * CDN Environment Variable
        * RHEVM Environment Variables
        * User Setup Environment Variables
2. ```fab commands```
After Setting Environment Variables in Shell, We are good to run fab commands that will run upgrades on setup.

### Environment Variables:
#### Common Environment Variables required for all types and combinations of upgrade

    1. FROM_VERSION=<preSat_ver> TO_VERSION=<nextSat_ver> OS=<rhel6|rhel7>
    2. Set FROM_VERSION and TO_VERSION to same current satellite version for Z-Stream Upgrade

#### Environment Variables required for specific type of upgrade

##### SATELLITE UPGRADE
**Environment Variables for only Satellite Upgrade**

**Downstream Environment Variables**

    BASE_URL=<satellite_downstream_base_url_from_snap>

**CDN Environment Variables**

    Dont set BASE_URL environment variable

**RHEVM Environment Variables**

    RHEV_SAT_IMAGE=<sat_image> RHEV_SAT_HOST=<rhev_sat_hostname>
    RHEV_USER=<rhev_user> RHEV_PASSWD=<rhev_passwd> RHEV_URL=<rhev_url:443/api>
    RHN_USERNAME=<rhn_user> RHN_POOLID=<rhn_pool> RHN_PASSWORD=<rhn_pass>

**User Setup Environment Variables**

    1. SATELLITE_HOSTNAME=<satellite_hostname>
    2. Don't set any RHEVM Environment Variable

##### CAPSULE UPGRADE
**Environment Variables for both Satellite and Capsule Upgrade**

**Downstream Environment Variables**

    1. CAPSULE_URL=<capsule_downstream_url_from_snap> RHEV_CAPSULE_AK=<ak_name_for_capsule_subscription>
    2. Satellite Downstream environment Variables

**CDN Environment Variables**

    1. Don't set BASE_URL and CAPSULE_URL environment variable
    2. RHEV_CAPSULE_AK=<ak_name_for_capsule_subscription>

**RHEVM Environment Variables**

    1. RHEV_CAP_IMAGE=<cap_image_name> RHEV_CAP_HOST=<rhev_cap_hostname>
    RHEV_USER=<rhev_user> RHEV_PASSWD=<rhev_passwd> RHEV_URL=<rhev_url:443/api>
    RHN_USERNAME=<rhn_user> RHN_POOLID=<rhn_pool> RHN_PASSWORD=<rhn_pass>
    2. Satellite RHEVM environment variables

**User Setup Environment Variables**

    1. CAPSULE_HOSTNAMES=<caps_hostname1, caps_hostname2, ...>
    2. Don't set any RHEVM Environment Variable
    3. Satellite User Setup environment Variables

##### CLIENTS UPGRADE
**Environment Variables for both Satellite and Client Upgrade**

**Downstream Environment Variables**

    1. TOOLS_URL_RHEL7=<client_rhel7_downstream_url> TOOLS_URL_RHEL6=<client_rhel6_downstream_url>
    RHEV_CLIENT_AK_RHEL7=<rhel7_ak_name_for_client_subscription>
    RHEV_CLIENT_AK_RHEL6=<rhel6_ak_name_for_client_subscription>
    2. Satellite Downstream environment Variables

**CDN Environment Variables**

    1. Dont set BASE_URL, TOOLS_URL_RHEL7 and TOOLS_URL_RHEL6 environment variable
    2. RHEV_CLIENT_AK_RHEL7=<rhel7_ak_name_for_client_subscription>
    RHEV_CLIENT_AK_RHEL6=<rhel6_ak_name_for_client_subscription>

**RHEVM and Docker Environment Variables**

    1. RHEV_USER=<rhev_user> RHEV_PASSWD=<rhev_passwd> RHEV_URL=<rhev_url:443/api>
    RHN_USERNAME=<rhn_user> RHN_POOLID=<rhn_pool> RHN_PASSWORD=<rhn_pass>
    DOCKER_VM=<ip_of_vm_where_rhel6_rhel7_docker_images_installed>
    CLIENTS_COUNT=<number_of_clients_to_generate_equally_on_rhel_6_and_7>
    2. Satellite RHEVM environment variables

**User Setup Environment Variables**

    1. CLIENT6_HOSTS=<client6_1, client6_2, ...>
    CLIENT7_HOSTS=<client7_1, client7_2, ...>
    2. Don't set any RHEVM and Docker Environment Variable
    3. Satellite User Setup environment Variables

##### LONGRUN UPGRADE:
**Environment Variables for Satellite, Capsule and Clients Upgrade**

**Downstream Environment Variables**

    Satellite, Capsule and Clients Downstream Environment Variables

**CDN Environment Variables**

    1. Don't Set BASE_URL, CAPSULE_URL, TOOLS_URL_RHEL7 and TOOLS_URL_RHEL6 environment variables
    2. Capsule and Clients CDN Environment variables

**RHEVM and Docker Environment Variables**

    Satellite, Capsule and Clients RHEVM environment variables

**User Setup Environment Variables**

    1. Don't set any RHEVM and Docker Environment Variable
    2. Satellite, Capsule and Clients User Setup Environment Variables

### Fab Commands for Setup and Upgrade Execution
These fab commands sets up the pre-requisites for upgrade and runs upgrade on satellite, capsule and clients.

Pre-Condition:
    - If RHEVM Setup, the ssh key of your machine should be added to the RHEVM images of satellite/capsule
    - If User setup, the ssh key of your machine should be added to user satellite, capsule and clients

**NOTE: To run upgrade, one needs to run both ```setup``` and ```upgrade``` commands listed below.**

##### SATELLITE UPGRADE
**Satellite Upgrade will only upgrade Satellite, NOT Capsule and NOT Clients**

    Setup : fab setup_products_for_upgrade:satellite,<os: rhel6|rhel7>
    Upgrade: fab product_upgrade:satellite

##### CAPSULE UPGRADE
**Capsule Upgrade will only upgrade Satellite and Capsule, NOT Clients**

    Setup : fab setup_products_for_upgrade:capsule,<os: rhel6|rhel7>
    Upgrade: fab product_upgrade:capsule

##### CLIENTS UPGRADE
**Clients Upgrade will only upgrade Satellite and Clients, NOT Capsule**

    Setup : fab setup_products_for_upgrade:client,<os: rhel6|rhel7>
    Upgrade: fab product_upgrade:client

##### LONGRUN UPGRADE
**Longrun Upgrade will upgrade Satellite, Capsule and Clients**

    Setup : fab -u root setup_products_for_upgrade:longrun,<os: rhel6|rhel7>
    fab product_upgrade:longrun

## Post Upgrade Satellite Entity Verification
Satellite6-upgrade provides a facility to check if the entities before upgrade are existing/retained post upgrade.

Its very simple, We collect the data before upgrade and post upgrade from satellite and then we compare each entity.
And display the results on stdout as well as XML file of reports will be generated, which further can be used.

This solely depends on ```pytest``` python package. So make sure that is installed.

To run the Satellite Post Upgrade Entity Verification, follow below steps :
1. Set ```RUN_EXISTANCE_TESTS=true``` environment variable, with the environment variables for upgrade and
   before setup and upgrade fab commands.
2. After Upgrade is Completed Successfully, for post upgrade entity verification results run following command :
    ```
    py.test --junit-xml=reports.xml --continue-on-collection-errors upgrade_tests/test_existance_relations/
    ```
The results will be displayed on stdout and reports.xml file will be generate after all entities verification.
