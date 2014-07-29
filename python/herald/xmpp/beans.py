#!/usr/bin/python
# -- Content-Encoding: UTF-8 --
"""
Herald XMPP beans definition
"""

# Standard library
import functools

# ------------------------------------------------------------------------------

@functools.total_ordering
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

    def __eq__(self, other):
        """
        Equality based on JID
        """
        if isinstance(other, XMPPAccess):
            return self.__jid.lower() == other.jid.lower()
        return False

    def __lt__(self, other):
        """
        JID string ordering
        """
        if isinstance(other, XMPPAccess):
            return self.__jid.lower() < other.jid.lower()
        return False

    def __str__(self):
        """
        String representation
        """
        return "XMPP:{0}".format(self.__jid)

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

    def dump(self):
        """
        Returns the content to store in a directory dump to describe this access
        """
        return self.__jid
