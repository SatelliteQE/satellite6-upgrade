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
    load_dotenv=True,
)

# Use to create the variant based on the supported satellite version list
# If the to_version is not available then append that version and popped up one older version
# from the list to maintain the variants matrix support
# (supported only 3 released and 1 downstream version)

supported_sat_versions = settings.upgrade.supported_sat_versions
if not (settings.upgrade.to_version in supported_sat_versions):
    supported_sat_versions.append(settings.upgrade.to_version)
while len(supported_sat_versions) > 4:
    supported_sat_versions.pop(0)
    settings.upgrade.supported_sat_versions = supported_sat_versions
