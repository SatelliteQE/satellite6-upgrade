from nailgun.config import ServerConfig
from upgrade.helpers.tasks import get_satellite_host

sat_url = 'https://{}'.format(get_satellite_host())
ServerConfig(url=sat_url, auth=['admin', 'changeme'], verify=False).save()
