#!/usr/bin/python
# -- Content-Encoding: UTF-8 --
"""
Tunnel service implementation

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

import socket

SOCK_TYPE_STR = {
    socket.SOCK_DGRAM: "udp",
    socket.SOCK_STREAM: "tcp",
    socket.SOCK_RAW: "raw"
}

# ------------------------------------------------------------------------------


class InputSocketConfiguration(object):
    """
    Configuration of a server socket
    """
    def __init__(self):
        """
        Sets up members
        """
        self.kind = "socket"
        self.address = 'localhost'
        self.port = 0
        self.sock_type = socket.SOCK_STREAM

    def __str__(self):
        """
        String representation
        """
        return "{0}-{3}: {1}:{2}".format(self.kind, self.address, self.port,
                                         SOCK_TYPE_STR[self.sock_type])

    def to_map(self):
        """
        Converts object fields to a map
        """
        return {
            "kind": self.kind,
            "address": self.address,
            "port": self.port,
            "sock_type": self.sock_type
        }


class OutputSocketConfiguration(object):
    """
    Configuration of a client socket
    """
    def __init__(self, address, port, sock_type):
        """
        Sets up members
        """
        self.address = address
        self.port = port
        self.sock_type = sock_type

        # Compute address family
        info = socket.getaddrinfo(address, port, 0, sock_type)
        self.sock_family = info[0][0]

    def __str__(self):
        """
        String representation
        """
        return "{0}-{3}: {1}:{2}".format("socket", self.address, self.port,
                                         SOCK_TYPE_STR[self.sock_type])

# ------------------------------------------------------------------------------


class FileConfiguration(object):
    def __init__(self):
        """
        Sets up members
        """
        self.kind = "file"
        self.filename = ""

    def __str__(self):
        """
        String representation
        """
        return "{0}: {1}".fromat(self.kind, self.filename)

    def to_map(self):
        """
        Converts object fields to a map
        """
        return {"kind": self.kind, "filename": self.filename}
