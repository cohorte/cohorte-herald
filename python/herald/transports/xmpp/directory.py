#!/usr/bin/python
# -- Content-Encoding: UTF-8 --
"""
Herald XMPP transport directory

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
__version_info__ = (0, 0, 1)
__version__ = ".".join(str(x) for x in __version_info__)

# Documentation strings format
__docformat__ = "restructuredtext en"

# ------------------------------------------------------------------------------

# Herald XMPP
from . import SERVICE_XMPP_DIRECTORY, ACCESS_ID
from .beans import XMPPAccess

# Herald
import herald

# Standard library
import logging
from pelix.ipopo.decorators import ComponentFactory, Requires, Provides, \
    Property, Validate, Invalidate, Instantiate

# ------------------------------------------------------------------------------

_logger = logging.getLogger(__name__)

# ------------------------------------------------------------------------------


@ComponentFactory('herald-xmpp-directory-factory')
@Requires('_directory', herald.SERVICE_DIRECTORY)
@Property('_access_id', herald.PROP_ACCESS_ID, ACCESS_ID)
@Provides((herald.SERVICE_TRANSPORT_DIRECTORY, SERVICE_XMPP_DIRECTORY))
@Instantiate('herald-xmpp-directory')
class XMPPDirectory(object):
    """
    XMPP Directory for Herald
    """
    def __init__(self):
        """
        Sets up the transport directory
        """
        # Herald Core Directory
        self._directory = None
        self._access_id = ACCESS_ID

        # JID -> Peer UID
        self._jid_uid = {}

        # Group name -> XMPP room JID
        self._groups = {}

    @Validate
    def _validate(self, context):
        """
        Component validated
        """
        self._jid_uid.clear()
        self._groups.clear()

    @Invalidate
    def _invalidate(self, context):
        """
        Component invalidated
        """
        self._jid_uid.clear()
        self._groups.clear()

    def load_access(self, data):
        """
        Loads a dumped access

        :param data: Result of a call to XmppAccess.dump()
        :return: An XMPPAccess bean
        """
        return XMPPAccess(data)

    def peer_access_set(self, peer, data):
        """
        The access to the given peer matching our access ID has been set

        :param peer: The Peer bean
        :param data: The peer access data, previously loaded with load_access()
        """
        if peer.uid != self._directory.local_uid:
            self._jid_uid[data.jid] = peer

    def peer_access_unset(self, peer, data):
        """
        The access to the given peer matching our access ID has been removed

        :param peer: The Peer bean
        :param data: The peer access data
        """
        try:
            del self._jid_uid[data.jid]
        except KeyError:
            pass

    def from_jid(self, jid):
        """
        Returns the peer UID associated to the given JID

        :param jid: A peer (full) JID
        :return: A peer UID
        :raise KeyError: Unknown JID
        """
        return self._jid_uid[jid]
