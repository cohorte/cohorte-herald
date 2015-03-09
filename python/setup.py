#!/usr/bin/env python
# -- Content-Encoding: UTF-8 --
"""
Cohorte Herald installation script

:author: Thomas Calmant
:copyright: Copyright 2014, isandlaTech
:license: Apache License 2.0
:version: 0.0.3
:status: Alpha

..

    Copyright 2014 isandlaTech

    Licensed under the Apache License, Version 2.0 (the "License");
    you may not use this file except in compliance with the License.
    You may obtain a copy of the License at

        http://www.apache.org/licenses/LICENSE-2.0

    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS,
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    See the License for the specific language governing permissions and
    limitations under the License.
"""

# Module version
__version_info__ = (0, 0, 3)
__version__ = ".".join(str(x) for x in __version_info__)

# Documentation strings format
__docformat__ = "restructuredtext en"

# ------------------------------------------------------------------------------

import os

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

# ------------------------------------------------------------------------------


def read(fname):
    """
    Utility method to read the content of a whole file
    """
    with open(os.path.join(os.path.dirname(__file__), fname)) as fd:
        return fd.read()


setup(
    name='Cohorte-Herald',
    version=__version__,
    license='Apache License 2.0',
    description='An easy-to-use messaging framework',
    long_description=read('README.rst'),
    author='Thomas Calmant',
    author_email='thomas.calmant@isandlatech.com',
    url='https://github.com/isandlaTech/cohorte-herald',
    download_url=
        'https://github.com/isandlaTech/cohorte-herald/archive/master.zip',
    packages=[
        'herald',
        'herald.probe',
        'herald.remote',
        'herald.transports',
        'herald.transports.http',
        'herald.transports.xmpp'],
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: Apache Software License',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.2',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4'
    ],
    install_requires=[
        'iPOPO>=0.5.7',
        'sleekxmpp>=1.3.1',
        'requests>=2.3.0'
    ]
)
