#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
try:
    from setuptools import find_packages, setup
except ImportError:
    from distutils.core import setup

with open('README.md', 'r') as f:
    readme = f.read()


if os.system('curl --version | grep NSS 2>/dev/null') != 0:
    os.environ['PYCURL_SSL_LIBRARY'] = 'openssl'
    os.system(
        'pip install --compile --install-option="--with-openssl" '
        'pycurl')
else:
    os.environ['PYCURL_SSL_LIBRARY'] = 'nss'
    os.system(
        'pip install --compile --install-option="--with-nss" pycurl')

setup(
    name='satellite6-upgrade',
    version='0.1.0',
    description='Tools to perform and test satellite6 upgrade.'
    'And test framework that validates entities postupgrade.',
    long_description=readme,
    author='Jitendra Yejare',
    author_email='jyejare@redhat.com',
    url='https://github.com/SatelliteQE/satellite6-upgrade',
    license='GNU GPL v3.0',
    classifiers=(
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'Intended Audience :: Testers',
        'Natural Language :: English',
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3.8',
    ),
    packages=find_packages(),
    # some requirements are also in requirements*.txt files
    # Its assumed this is installed as a dependency of robottelo, frozen packages are defined there
    install_requires=[
        'broker==0.2.0',
        'dynaconf[vault]',
        'Fabric3',
        'fauxfactory',
        'jinja2',
        'ovirt-engine-sdk-python',
        'pycurl',
        'pytest',
        # python-bugzilla is on 3.x, and this package is about 5 years old
        # I'm afraid to touch it while un-freezing pytest and fauxfactory
        'python-bugzilla==1.2.2',
        'requests',
        'robozilla',
        'shade',
    ],
)
