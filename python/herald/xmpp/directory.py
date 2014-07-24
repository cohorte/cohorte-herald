#!/usr/bin/python
# -- Content-Encoding: UTF-8 --
"""
Herald XMPP directory
"""

# Herald XMPP beans
from .beans import XMPPAccess

# Standard library
import logging
from pelix.ipopo.decorators import ComponentFactory, Requires, Provides, \
    Property, Validate, Invalidate

# ------------------------------------------------------------------------------

_logger = logging.getLogger(__name__)

# ------------------------------------------------------------------------------

@ComponentFactory("herald-xmpp-directory")
@Requires('_directory', 'herald.directory')
@Property('_access_id', 'herald.access.id', 'xmpp')
@Provides(('herald.transport.directory', 'herald.xmpp.directory'))
class XMPPDirectory(object):
    """
    XMPP Directory for Herald
    """
    def __init__(self):
        """
        Sets up the transport
        """
        # Herald Core Directory
        self._directory = None
        self._access_id = "xmpp"

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

    def from_jid(self, jid):
        """
        Returns the peer UID associated to the given JID

        :param jid: A peer (full) JID
        :return: A peer UID
        :raise KeyError: Unknown JID
        """
        return self._jid_uid[jid]
