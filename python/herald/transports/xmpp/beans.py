#!/usr/bin/python
# -- Content-Encoding: UTF-8 --
"""
Herald XMPP beans definition

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
from . import ACCESS_ID

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

    def __hash__(self):
        """
        Hash is based on JID
        """
        return hash(self.__jid)

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
        Returns the access ID associated to this kind of access
        """
        return ACCESS_ID

    @property
    def jid(self):
        """
        Returns the JID of the associated peer
        """
        return self.__jid

    def dump(self):
        """
        Returns the content to store in a directory dump to describe this
        access
        """
        return self.__jid
