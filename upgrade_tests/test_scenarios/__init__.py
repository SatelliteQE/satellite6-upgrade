"""Initializes of config to be used in Scenario Tests
"""
from automation_tools.satellite6.hammer import set_hammer_config
from upgrade.helpers.tasks import get_satellite_host
from nailgun.config import ServerConfig
from fabric.api import env

# Nailgun Config setup
sat_url = 'https://{}'.format(get_satellite_host())
ServerConfig(url=sat_url, auth=['admin', 'changeme'], verify=False).save()

# Fabric Config setup
env.user = 'root'

# Hammer Config Setup
set_hammer_config()
