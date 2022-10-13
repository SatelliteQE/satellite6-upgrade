"""Upgrade needed Constants"""
from packaging.version import Version

from upgrade.helpers import settings

os_ver = int(settings.upgrade.os.strip('rhel'))
arch = 'x86_64'
target_cap_version = settings.upgrade.to_version \
    if settings.upgrade.from_version != settings.upgrade.to_version and \
    settings.upgrade.distribution == 'cdn' else settings.upgrade.from_version
maintenance_ver = target_cap_version if Version(target_cap_version) > Version('6.10') else '6'
os_repo_tags = ['server', 'rhscl', 'ansible'] if os_ver < 8 else ['baseos', 'appstream']

RH_CONTENT = {
    # RHEL7 repos
    'server': {
        'prod': 'Red Hat Enterprise Linux Server',
        'reposet': f'Red Hat Enterprise Linux {os_ver} Server (RPMs)',
        'repo': f'Red Hat Enterprise Linux {os_ver} Server RPMs {arch} {os_ver}Server',
        'label': f'rhel-{os_ver}-server-rpms',
    },
    'rhscl': {
        'prod': 'Red Hat Software Collections (for RHEL Server)',
        'reposet': f'Red Hat Software Collections RPMs for Red Hat Enterprise Linux {os_ver} '
        'Server',
        'repo': f'Red Hat Software Collections RPMs for Red Hat Enterprise Linux {os_ver} '
        f'Server x86_64 {os_ver}Server',
        'label': f'rhel-server-rhscl-{os_ver}-rpms'
    },
    'ansible': {
        'prod': 'Red Hat Ansible Engine',
        'reposet': f'Red Hat Ansible Engine 2.9 RPMs for Red Hat Enterprise Linux {os_ver} Server',
        'repo': f'Red Hat Ansible Engine 2.9 RPMs for Red Hat Enterprise Linux {os_ver} Server '
        f'{arch}',
        'label': f'rhel-{os_ver}-server-ansible-2.9-rpms'
    },
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
        'prod': 'Red Hat Enterprise Linux Server',
        'reposet': f'Red Hat Satellite Client 6 (for RHEL {os_ver} Server) (RPMs)',
        'repo': f'Red Hat Satellite Client 6 for RHEL {os_ver} Server RPMs {arch}',
        'label': f'rhel-{os_ver}-server-satellite-client-6-rpms'
    } if os_ver < 8 else {
        'prod': f'Red Hat Enterprise Linux for {arch}',
        'reposet': f'Red Hat Satellite Client 6 for RHEL {os_ver} {arch} (RPMs)',
        'repo': f'Red Hat Satellite Client 6 for RHEL {os_ver} {arch} RPMs',
        'label': f'satellite-client-6-for-rhel-{os_ver}-{arch}-rpms'
    },
    'tools': {
        'prod': 'Red Hat Enterprise Linux Server',
        'reposet': f'Red Hat Satellite Tools {target_cap_version} (for RHEL {os_ver} Server) '
        '(RPMs)',
        'repo': f'Red Hat Satellite Tools {target_cap_version} for RHEL {os_ver} Server RPMs '
        f'{arch}',
        'label': f'rhel-{os_ver}-server-satellite-tools-{target_cap_version}-rpms',
    },
    'capsule': {
        'prod': 'Red Hat Satellite Capsule',
        'reposet': f'Red Hat Satellite Capsule {target_cap_version} (for RHEL {os_ver} Server) '
        '(RPMs)',
        'repo': f'Red Hat Satellite Capsule {target_cap_version} for RHEL {os_ver} Server RPMs '
        f'{arch}',
        'label': f'rhel-{os_ver}-server-satellite-capsule-{target_cap_version}-rpms'
    } if os_ver < 8 else {
        'prod': 'Red Hat Satellite Capsule',
        'reposet': f'Red Hat Satellite Capsule {target_cap_version} for RHEL {os_ver} {arch} '
        '(RPMs)',
        'repo': f'Red Hat Satellite Capsule {target_cap_version} for RHEL {os_ver} {arch} RPMs',
        'label': f'satellite-capsule-{target_cap_version}-for-rhel-{os_ver}-{arch}-rpms'
    },
    'maintenance': {
        'prod': 'Red Hat Enterprise Linux Server',
        'reposet': f'Red Hat Satellite Maintenance {maintenance_ver} (for RHEL {os_ver} Server) '
        '(RPMs)',
        'repo': f'Red Hat Satellite Maintenance {maintenance_ver} for RHEL {os_ver} Server RPMs '
        f'{arch}',
        'label': f'rhel-{os_ver}-server-satellite-maintenance-{maintenance_ver}-rpms'
    } if os_ver < 8 else {
        'prod': f'Red Hat Enterprise Linux for {arch}',
        'reposet': f'Red Hat Satellite Maintenance {maintenance_ver} for RHEL {os_ver} {arch} '
        '(RPMs)',
        'repo': f'Red Hat Satellite Maintenance {maintenance_ver} for RHEL {os_ver} {arch} RPMs',
        'label': f'satellite-maintenance-{maintenance_ver}-for-rhel-{os_ver}-{arch}-rpms'
    },
}

OS_REPOS = dict(filter(lambda i: i[0] in os_repo_tags, RH_CONTENT.items()))

CUSTOM_CONTENT = {
    'capsule': {
        'prod': 'capsule_latest',
        'reposet': 'capsule_latest_repo',
    },
    'capsule_tools': {
        'prod': 'capsuletools_product',
        'reposet': 'capsuletools_repo',
    },
    'tools': {
        'prod': 'tools_latest_{client_os}',
        'reposet': 'tools_latest_repo_{client_os}',
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
    "sat": {
        "repository": "sat",
        "repository_name": "satellite",
        "base_url": f"{settings.repos.satellite_repo}",
    },
    "sattools": {
        "repository": "sattools",
        "repository_name": "satellite-tools",
        "base_url": f"{settings.repos.sattools_repo[settings.upgrade.os]}",
    },
    "maintenance": {
        "repository": "maintenance",
        "repository_name": "satellite-maintenance",
        "base_url": f"{settings.repos.satmaintenance_repo}",
    },
    "satclient": {
        "repository": "satclient",
        "repository_name": "sat-client",
        "base_url": f"{settings.repos.satclient_repo[settings.upgrade.os]}",
    },
}


CAPSULE_SUBSCRIPTIONS = {
    "sat_infra": "Red Hat Satellite Infrastructure Subscription",
}


DEFAULT_LOCATION = "Default Location"
DEFAULT_ORGANIZATION = "Default Organization"
DEFAULT_ORGANIZATION_LABEL = "Default_Organization"
