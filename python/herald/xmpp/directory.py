#!/usr/bin/python
# -- Content-Encoding: UTF-8 --
"""
Herald XMPP directory
"""

# Standard library
import logging
from pelix.ipopo.decorators import ComponentFactory, Requires, Provides, \
    Validate, Invalidate

# ------------------------------------------------------------------------------

_logger = logging.getLogger(__name__)

# ------------------------------------------------------------------------------

class XMPPAccess(object):
    """
    Description of an XMPP access
    """
    def __init__(self, jid):
        """
        Sets up the access

        :param jid: JID of the associated peer
        """
        self.__jid = jid

    @property
    def access_id(self):
        """
        Retrieves the access ID associated to this kind of access
        """
        return "xmpp"

    @property
    def jid(self):
        """
        Retrieves the JID of the associated peer
        """
        return self.__jid

# ------------------------------------------------------------------------------

@ComponentFactory("herald-xmpp-directory")
@Requires('_directory', 'herald.core.directory')
@Provides('herald.xmpp.directory')
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

    def dump(self):
        """
        Dumps the content of the local directory in a dictionary

        :return: A UID -> description dictionary
        """
        return {}

    def register(self, uid, description):
        """
        Registers a peer

        :param uid: UID of the peer
        :param description: Description of the peer, in the format of dump()
        """
        pass

    def unregister(self, uid):
        """
        Unregisters a peer from the directory

        :param uid: UID of the peer
        """
        try:
            # Local clean up
            del self._jid_uid[self._peer_jid.pop(uid)]
        except KeyError:
            # Not an XMPP peer, not a problem
            pass

        # Core Directory clean up
        self._directory.unregister(uid)

    def from_jid(self, jid):
        """
        Returns the peer UID associated to the given JID

        :param jid: A peer (full) JID
        :return: A peer UID
        :raise KeyError: Unknown JID
        """
        return self._jid_uid[jid]
