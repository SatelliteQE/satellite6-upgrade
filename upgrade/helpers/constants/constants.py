"""Upgrade needed Constants"""
from upgrade.helpers import settings

os_ver = int(settings.upgrade.os.strip('rhel'))
arch = 'x86_64'
target_version = settings.upgrade.to_version \
    if settings.upgrade.from_version != settings.upgrade.to_version and \
    settings.upgrade.distribution == 'cdn' else settings.upgrade.from_version
os_repo_tags = ['baseos', 'appstream']

RH_CONTENT = {
    # RHEL8+ repos
    'baseos': {
        'prod': f'Red Hat Enterprise Linux for {arch}',
        'reposet': f'Red Hat Enterprise Linux {os_ver} for {arch} - BaseOS (RPMs)',
        'repo': f'Red Hat Enterprise Linux {os_ver} for {arch} - BaseOS RPMs {arch} {os_ver}',
        'label': f'rhel-{os_ver}-for-{arch}-baseos-rpms',
    },
    'appstream': {
        'prod': f'Red Hat Enterprise Linux for {arch}',
        'reposet': f'Red Hat Enterprise Linux {os_ver} for {arch} - AppStream (RPMs)',
        'repo': f'Red Hat Enterprise Linux {os_ver} for {arch} - AppStream RPMs {arch} {os_ver}',
        'label': f'rhel-{os_ver}-for-{arch}-appstream-rpms',
    },
    # PRODUCT repos
    'client': {
        'prod': f'Red Hat Enterprise Linux for {arch}',
        'reposet': f'Red Hat Satellite Client 6 for RHEL {os_ver} {arch} (RPMs)',
        'repo': f'Red Hat Satellite Client 6 for RHEL {os_ver} {arch} RPMs',
        'label': f'satellite-client-6-for-rhel-{os_ver}-{arch}-rpms'
    },
    'capsule': {
        'prod': 'Red Hat Satellite Capsule',
        'reposet': f'Red Hat Satellite Capsule {target_version} for RHEL {os_ver} {arch} '
        '(RPMs)',
        'repo': f'Red Hat Satellite Capsule {target_version} for RHEL {os_ver} {arch} RPMs',
        'label': f'satellite-capsule-{target_version}-for-rhel-{os_ver}-{arch}-rpms'
    },
    'maintenance': {
        'prod': f'Red Hat Enterprise Linux for {arch}',
        'reposet': f'Red Hat Satellite Maintenance {target_version} for RHEL {os_ver} {arch} '
        '(RPMs)',
        'repo': f'Red Hat Satellite Maintenance {target_version} for RHEL {os_ver} {arch} RPMs',
        'label': f'satellite-maintenance-{target_version}-for-rhel-{os_ver}-{arch}-rpms'
    },
    'satellite': {
        'prod': 'Red Hat Satellite',
        'reposet': f'Red Hat Satellite {target_version} for RHEL {os_ver} {arch} (RPMs)',
        'repo': f'Red Hat Satellite {target_version} for RHEL {os_ver} {arch} RPMs',
        'label': f'satellite-{target_version}-for-rhel-{os_ver}-{arch}-rpms'
    },
}

OS_REPOS = dict(filter(lambda i: i[0] in os_repo_tags, RH_CONTENT.items()))

CUSTOM_CONTENT = {
    'capsule': {
        'prod': 'capsule_latest',
        'reposet': 'capsule_latest_repo',
    },
    'capsule_client': {
        'prod': 'capsuleclient_product',
        'reposet': 'capsuleclient_repo',
    },
    'capsule_utils': {
        'prod': 'capsuleutils_product',
        'reposet': 'capsuleutils_repo',
    },
    'maintenance': {
        'prod': f'maintenance_latest_{os_ver}',
        'reposet': 'maintenance_repo',
    },
    'client': {
        'prod': 'client_latest_{client_os}',
        'reposet': 'client_repo',
    },
}


CUSTOM_SAT_REPO = {
    "satellite": {
        "repository": "satellite",
        "repository_name": "Satellite",
        "base_url": f"{settings.repos.satellite_repo}",
    },
    "maintenance": {
        "repository": "maintenance",
        "repository_name": "Satellite Maintenance",
        "base_url": f"{settings.repos.satmaintenance_repo}",
    },
    "capsule": {
        "repository": "capsule",
        "repository_name": "Capsule",
        "base_url": f"{settings.repos.capsule_repo}",
    },
    "satclient": {
        "repository": "satclient",
        "repository_name": "Satellite Client",
        "base_url": f"{settings.repos.satclient_repo[settings.upgrade.os]}",
    },
}


CAPSULE_SUBSCRIPTIONS = {
    "sat_infra": "Red Hat Satellite Infrastructure Subscription",
}


DEFAULT_LOCATION = "Default Location"
DEFAULT_ORGANIZATION = "Default Organization"
DEFAULT_ORGANIZATION_LABEL = "Default_Organization"
