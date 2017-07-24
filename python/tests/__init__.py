#!/usr/bin/env python
# -- Content-Encoding: UTF-8 --
"""
Test package for Herald Python

:author: Bassem Debbabi
:copyright: Copyright 2015, isandlaTech
:license: Apache License 2.0
:version: 1.0.1
:status: Alpha

..

    Copyright 2015 isandlaTech

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

# Documentation strings format
__docformat__ = "restructuredtext en"

import logging


def log_on():
    """
    Enables the logging
    """
    logging.disable(logging.NOTSET)


def log_off():
    """
    Disables the logging
    """
    logging.disable(logging.CRITICAL)