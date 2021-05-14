"""Upgrade needed Constants"""
from upgrade.helpers import settings

os_ver = settings.upgrade.os[-1]
arch = "x86_64"
target_cap_version = settings.upgrade.to_version \
    if settings.upgrade.from_version != settings.upgrade.to_version and \
    settings.upgrade.distribution == "cdn" else settings.upgrade.from_version

RHEL_CONTENTS = {
    'rhscl': {
        'prod': 'Red Hat Software Collections for RHEL Server',
        'repofull': f'Red Hat Software Collections RPMs for Red Hat Enterprise Linux '
        f'{os_ver} Server x86_64 {os_ver}Server',
        'repo': f'Red Hat Software Collections RPMs for Red Hat Enterprise Linux {os_ver} '
        f'Server',
        'label': f'rhel-server-rhscl-{os_ver}-rpms'
    },
    'rhscl_sat64': {
        'prod': 'Red Hat Software Collections (for RHEL Server)'
    },
    'server': {
        'prod': 'Red Hat Enterprise Linux Server',
        'repofull': f'Red Hat Enterprise Linux {os_ver} Server RPMs {arch} {os_ver}Server',
        'repo': f'Red Hat Enterprise Linux {os_ver} Server (RPMs)',
        'label': f'rhel-{os_ver}-server-rpms',
    },
    'tools': {
        'prod': 'Red Hat Enterprise Linux Server',
        'repofull': f'Red Hat Satellite Tools {target_cap_version} '
        f'(for RHEL {os_ver} Server) (RPMs)',
        'repo': f'Red Hat Satellite Tools {target_cap_version} for RHEL {os_ver} Server RPMs'
        f' {arch}',
        'label': f'rhel-{os_ver}-server-satellite-tools-{target_cap_version}-rpms',
    },
    'capsule': {
        'prod': 'Red Hat Satellite Capsule',
        'repofull': f'Red Hat Satellite Capsule {target_cap_version} '
        f'(for RHEL {os_ver} Server) (RPMs)',
        'repo': f'Red Hat Satellite Capsule {target_cap_version} for RHEL {os_ver} Server RPMs'
        f' {arch}',
        'label': f'rhel-{os_ver}-server-satellite-capsule-{target_cap_version}-rpms'
    },
    'maintenance': {
        'prod': 'Red Hat Enterprise Linux Server',
        'repofull': f'Red Hat Satellite Maintenance 6 (for RHEL {os_ver} Server) (RPMs)',
        'repo': f'Red Hat Satellite Maintenance 6 for RHEL {os_ver} Server RPMs {arch}',
        'label': f"rhel-{os_ver}-server-satellite-maintenance-6-rpms"
    },
}

CUSTOM_CONTENTS = {
    'capsule': {
        'prod': 'capsule6_latest',
        'repo': 'capsule6_latest_repo',
    },
    'capsule_tools': {
        'prod': 'capsuletools_product',
        'repo': 'capsuletools_repo',
    },
    'tools': {
        'prod': 'tools6_latest_{client_os}',
        'repo': 'tools6_latest_repo_{client_os}',
    },
    'maintenance': {
        'prod': f'maintenance_latest_{os_ver}',
        'repo': 'maintenance_repo',
    },
}


CUSTOM_SAT_REPO = {
    "sat6": {
        "repository": "sat6",
        "repository_name": "satellite 6",
        "base_url": f"{settings.repos.satellite6_repo}",
        "enable": 1,
        "gpg": 0,
    },
    "sat6tools7": {
        "repository": "sat6tools7",
        "repository_name": "satellite6-tools7",
        "base_url": f"{settings.repos.sattools_repo[settings.upgrade.os]}",
        "enable": 1,
        "gpg": 0,
    },
    "foreman-maintain": {
        "repository": "maintenance6",
        "repository_name": "maintenance6-repo",
        "base_url": f"{settings.repos.satmaintenance_repo}",
        "enable": 1,
        "gpg": 0,
    }
}


CAPSULE_SUBSCRIPTIONS = {
    "rhel_subscription": "Red Hat Enterprise Linux Server, Premium "
                         "\(Physical or Virtual Nodes\)",  # noqa
    "satellite_infra": "Red Hat Satellite Infrastructure Subscription",
}


DEFAULT_LOCATION = "Default Location"
DEFAULT_ORGANIZATION = "Default Organization"
DEFAULT_ORGANIZATION_LABEL = "Default_Organization"
