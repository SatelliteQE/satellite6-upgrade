from os import environ


FROM_VERSION = environ.get('FROM_VERSION')
TO_VERSION = environ.get('TO_VERSION')

OS = environ.get('OS')

CAPSULE_REPO = environ.get('CAPSULE_URL')

TOOLS_URL_RHEL6 = environ.get('TOOLS_URL_RHEL6')
TOOLS_URL_RHEL7 = environ.get('TOOLS_URL_RHEL7')
MAINTAIN_REPO = environ.get('MAINTAIN_REPO')

RHEV_CLIENT_AK_RHEL6 = environ.get('RHEV_CLIENT_AK_RHEL6')
RHEV_CLIENT_AK_RHEL7 = environ.get('RHEV_CLIENT_AK_RHEL7')
RHEV_CAPSULE_AK = environ.get('RHEV_CAPSULE_AK')

BASE_URL = environ.get('BASE_URL')
CAPSULE_URL = environ.get('CAPSULE_URL')

PRODUCTS = ['satellite', 'capsule', 'client', 'longrun', 'n-1']

LIBVERT_HOSTNAME = environ.get('LIBVIRT_HOSTNAME')

FAKE_MANIFEST_CERT_URL = environ.get('FAKE_MANIFEST_CERT_URL')

DISTRIBUTION = environ.get('DISTRIBUTION')
BASE_URL = environ.get('BASE_URL')
DOCKER_VM = environ.get('DOCKER_VM')
