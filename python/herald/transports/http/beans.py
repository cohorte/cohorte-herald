#!/usr/bin/python
# -- Content-Encoding: UTF-8 --
"""
Herald HTTP beans definition

:author: Thomas Calmant
:copyright: Copyright 2014, isandlaTech
:license: Apache License 2.0
:version: 1.0.1
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

# Bundle version
import herald.version
__version__=herald.version.__version__

# ------------------------------------------------------------------------------

# Herald HTTP
from . import ACCESS_ID

# Standard library
import functools

# ------------------------------------------------------------------------------


@functools.total_ordering
class HTTPAccess(object):
    """
    Description of an HTTP access
    """
    def __init__(self, host, port, path):
        """
        Sets up the access

        :param host: HTTP server host
        :param port: HTTP server port
        :param path: Path to the Herald service
        """
        # Normalize path
        if path[0] == '/':
            path = path[1:]

        self.__host = host
        self.__port = int(port)
        self.__path = path

    def __hash__(self):
        """
        Hash is based on the access tuple
        """
        return hash(self.access)

    def __eq__(self, other):
        """
        Equality based on JID
        """
        if isinstance(other, HTTPAccess):
            return self.access == other.access
        return False

    def __lt__(self, other):
        """
        JID string ordering
        """
        if isinstance(other, HTTPAccess):
            return self.access < other.access
        return False

    def __str__(self):
        """
        String representation
        """
        return "http://{0}:{1}/{2}".format(self.__host, self.__port,
                                           self.__path)

    @property
    def access_id(self):
        """
        Retrieves the access ID associated to this kind of access
        """
        return ACCESS_ID

    @property
    def access(self):
        """
        Returns the access to the peer as a 3-tuple (host, port, path)
        """
        return self.__host, self.__port, self.__path

    @property
    def address(self):
        """
        Returns the address of the HTTP server to access the peer (host, port)
        """
        return self.__host, self.__port

    @property
    def host(self):
        """
        Retrieves the host address of the associated peer
        """
        return self.__host

    @property
    def port(self):
        """
        Retrieves the host port of the associated peer
        """
        return self.__port

    @property
    def path(self):
        """
        Retrieves the path to the Herald service
        """
        return self.__path

    def dump(self):
        """
        Returns the content to store in a directory dump to describe this
        access
        """
        return self.access
