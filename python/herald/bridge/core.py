#!/usr/bin/python
# -- Content-Encoding: UTF-8 --
"""
:author: Thomas Calmant
:copyright: Copyright 2015, isandlaTech
:license: Apache License 2.0
:version: 0.0.1
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

# Module version
__version_info__ = (0, 0, 1)
__version__ = ".".join(str(x) for x in __version_info__)

# Documentation strings format
__docformat__ = "restructuredtext en"

# ------------------------------------------------------------------------------


class Bridge(object):
    """
    Represents the bridge
    """
    def __init__(self):
        """
        Sets up members
        """
        self.__in = None
        self.__out = None

    def set_in(self, bridge_in):
        """
        Sets bridge in
        """
        self.__in = bridge_in
        if self.__out is not None:
            self.__out.bind_bridge_input(bridge_in)
            self.__in.bind_bridge_output(self.__out)

    def set_out(self, bridge_out):
        """
        Sets bridge out
        """
        self.__out = bridge_out
        if self.__in is not None:
            self.__in.bind_bridge_output(bridge_out)
            self.__out.bind_bridge_input(self.__in)

    def start(self):
        print("Starting in...")
        self.__in.start()

        print("Starting out...")
        self.__out.start()

    def close(self):
        print("Closing out...")
        self.__out.close()
        print("Closing in...")
        self.__in.close()
