"""Upgrade needed Constants"""

rhelcontents = {
    'rhscl': {
        'prod': 'Red Hat Software Collections (for RHEL Server)',
        'repofull': 'Red Hat Software Collections RPMs for Red Hat Enterprise Linux '
                    '{os_ver} Server {arch} {os_ver}Server',
        'repo': 'Red Hat Software Collections RPMs for Red Hat Enterprise Linux {os_ver} Server',
        'label': 'rhel-server-rhscl-{os_ver}-rpms'
    },
    'server': {
        'prod': 'Red Hat Enterprise Linux Server',
        'repofull': 'Red Hat Enterprise Linux {os_ver} Server RPMs {arch} {os_ver}Server',
        'repo': 'Red Hat Enterprise Linux {os_ver} Server (RPMs)',
        'label': 'rhel-{os_ver}-server-rpms',
    },
    'tools': {
        'prod': 'Red Hat Enterprise Linux Server',
        'repofull': 'Red Hat Satellite Tools {sat_ver} for RHEL {os_ver} Server RPMs {arch}',
        'repo': 'Red Hat Satellite Tools {sat_ver} (for RHEL {os_ver} Server) (RPMs)',
        'label': 'rhel-{os_ver}-server-satellite-tools-{sat_ver}-rpms',
    },
    'capsule': {
        'prod': 'Red Hat Satellite Capsule',
        'repofull': 'Red Hat Satellite Capsule {cap_ver} for RHEL {os_ver} Server (RPMs) {arch}',
        'repo': 'Red Hat Satellite Capsule {cap_ver} (for RHEL {os_ver} Server) (RPMs)',
        'label': 'rhel-{os_ver}-server-satellite-capsule-{cap_ver}-rpms'
    },
}

customcontents = {
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
    }
}
