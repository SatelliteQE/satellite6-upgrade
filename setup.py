#!/usr/bin/env python
# -*- coding: utf-8 -*-
try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

with open('README.md', 'r') as f:
    readme = f.read()

setup(
    name='satellite6-upgrade',
    version='0.1.0',
    description='Tools to perform and test satellite6 upgrade.'
    'And test framework that validates entities postupgrade.',
    long_description=readme,
    author=u'Jitendra Yejare',
    author_email='jyejare@redhat.com',
    url='https://github.com/SatelliteQE/satellite6-upgrade',
    packages=['satellite6-upgrade'],
    package_data={'': ['LICENSE']},
    package_dir={'satellite6-upgrade': 'satellite6-upgrade'},
    include_package_data=True,
    install_requires=[
        'Fabric',
        'ovirt-engine-sdk-python==3.6.8.0',
        'pycurl',
        'pytest',
        'python-bugzilla==1.2.2',
        'python-novaclient',
        'requests',
        'robozilla'
    ],
    license='GNU GPL v3.0',
    classifiers=(
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'Intended Audience :: Testers',
        'Natural Language :: English',
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
    ),
)
