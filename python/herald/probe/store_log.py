#!/usr/bin/python
# -- Content-Encoding: UTF-8 --
"""
Stores probe data in logs

:author: Thomas Calmant
:copyright: Copyright 2014, isandlaTech
:license: Apache License 2.0
:version: 1.0.0
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
__version_info__ = (1, 0, 0)
__version__ = ".".join(str(x) for x in __version_info__)

# Documentation strings format
__docformat__ = "restructuredtext en"

# ------------------------------------------------------------------------------

# Probe constants
from . import SERVICE_STORE

# Pelix
from pelix.ipopo.decorators import ComponentFactory, Provides, Property, \
    Validate

# Standard library
from pprint import pformat
import logging

# ------------------------------------------------------------------------------


@ComponentFactory('herald-probe-log-factory')
@Provides(SERVICE_STORE)
@Property("_prefix", "logger.prefix", "herald.debug")
class LogStore(object):
    """
    Traces data into a logger
    """
    def __init__(self):
        """
        Sets up members
        """
        self._prefix = __name__

    @Validate
    def validate(self, _):
        """
        Component validated
        """
        self._prefix = self._prefix or __name__

    def __get_logger(self, channel):
        """
        Returns the logger associated to the channel

        :param channel: Name of a channel
        :return: A logger for the channel
        """
        return logging.getLogger("{0}.{1}".format(self._prefix, channel))

    def activate_channel(self, channel):
        """
        A channel has been activated

        :param channel: Name of the channel
        """
        self.__get_logger(channel).setLevel(logging.INFO)

    def deactivate_channel(self, channel):
        """
        A channel has been deactivated

        :param channel: Name of the channel
        """
        self.__get_logger(channel).setLevel(logging.NOTSET)

    def store(self, channel, data):
        """
        Stores data to the given channel

        :param channel: Channel where to store data
        :param data: A dictionary of data to be stored
        """
        self.__get_logger(channel).info("%s", pformat(data))
