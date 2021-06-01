import os

from dynaconf import Dynaconf
from nailgun.config import ServerConfig


"""
Save the satellite host details in the nailgun server config, that helps to execute
all the nailgun API's
"""

sat_url = f"https://{os.environ.get('satellite_hostname')}"
nailgun_conf = ServerConfig(url=sat_url, auth=('admin', 'changeme'), verify=False)

"""
The dynaconf object use to access the environment variable
"""
settings = Dynaconf(
    envvar_prefix="UPGRADE",
    core_loaders=["YAML"],
    preload=["conf/*.yaml"],
    envless_mode=True,
    lowercase_read=True,
)
