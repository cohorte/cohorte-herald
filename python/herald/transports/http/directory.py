#!/usr/bin/python
# -- Content-Encoding: UTF-8 --
"""
Herald HTTP transport directory

:author: Thomas Calmant
:copyright: Copyright 2014, isandlaTech
:license: Apache License 2.0
:version: 0.0.1
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
__version_info__ = (0, 0, 2)
__version__ = ".".join(str(x) for x in __version_info__)

# Documentation strings format
__docformat__ = "restructuredtext en"

# ------------------------------------------------------------------------------

# Herald XMPP
from . import ACCESS_ID, SERVICE_HTTP_DIRECTORY
from .beans import HTTPAccess

# Herald
import herald

# Standard library
import logging
from pelix.ipopo.decorators import ComponentFactory, Requires, Provides, \
    Property, Validate, Invalidate, Instantiate

# ------------------------------------------------------------------------------

_logger = logging.getLogger(__name__)

# ------------------------------------------------------------------------------


@ComponentFactory('herald-http-directory-factory')
@Requires('_directory', herald.SERVICE_DIRECTORY)
@Property('_access_id', herald.PROP_ACCESS_ID, ACCESS_ID)
@Provides((herald.SERVICE_TRANSPORT_DIRECTORY, SERVICE_HTTP_DIRECTORY))
@Instantiate('herald-http-directory')
class HTTPDirectory(object):
    """
    HTTP Directory for Herald
    """
    def __init__(self):
        """
        Sets up the transport directory
        """
        # Herald Core Directory
        self._directory = None
        self._access_id = ACCESS_ID

        # Peer UID -> (host, port)
        self._uid_address = {}

    @Validate
    def _validate(self, context):
        """
        Component validated
        """
        self._uid_address.clear()

    @Invalidate
    def _invalidate(self, context):
        """
        Component invalidated
        """
        self._uid_address.clear()

    def load_access(self, data):
        """
        Loads a dumped access

        :param data: Result of a call to HTTPAccess.dump()
        :return: An HTTPAccess bean
        """
        return HTTPAccess(data[0], data[1], data[2])

    def peer_access_set(self, peer, data):
        """
        The access to the given peer matching our access ID has been set

        :param peer: The Peer bean
        :param data: The peer access data, previously loaded with load_access()
        """
        if peer.uid != self._directory.local_uid:
            self._uid_address[peer.uid] = data.address

    def peer_access_unset(self, peer, data):
        """
        The access to the given peer matching our access ID has been removed

        :param peer: The Peer bean
        :param data: The peer access data
        """
        try:
            del self._uid_address[peer.uid]
        except KeyError:
            pass

    def check_access(self, uid, host, port):
        """
        Checks if the peer with the given UID is known to have the given access

        :param uid: The UID of a peer
        :param host: The tested peer host
        :param port: The tested HTTP port
        :return: True if the given access matches the peer UID
        :raise ValueError: The access doesn't match the peer
        """
        try:
            peer_port = self._uid_address[uid][1]
            return peer_port == port
        except KeyError:
            raise ValueError("Unknown peer: {0}".format(uid))
