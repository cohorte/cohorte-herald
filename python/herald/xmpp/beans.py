#!/usr/bin/python
# -- Content-Encoding: UTF-8 --
"""
Herald XMPP beans definition
"""

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

    def dump(self):
        """
        Returns the content to store in a directory dump to describe this access
        """
        return self.__jid
