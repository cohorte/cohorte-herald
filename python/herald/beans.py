#!/usr/bin/python
# -- Content-Encoding: UTF-8 --
"""
Herald core beans definition

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

# Standard library
import functools
import threading
import time
import uuid
import json

# import herald module to use constantes
import herald
import herald.utils as utils

# ------------------------------------------------------------------------------


@functools.total_ordering
class Peer(object):
    """
    Represents a peer in Herald
    """
    def __init__(self, uid, node_uid, app_id, groups, directory):
        """
        Sets up the peer

        :param uid: Peer Unique ID
        :param node_uid: Node Unique ID
        :param app_id: Peer Application ID
        :param groups: The list of groups this peer belongs to
        :param directory: Directory to call back on access update
        :raise ValueError: Invalid Peer UID
        """
        if not uid:
            raise ValueError("The UID of a peer can't be empty")

        self.__uid = uid
        self.__name = uid
        self.__node = node_uid or uid
        self.__node_name = self.__node
        self.__app_id = app_id
        self.__groups = set(groups or [])
        self.__accesses = {}
        self.__directory = directory
        self.__lock = threading.RLock()

    def __repr__(self):
        """
        Peer representation
        """
        return "Peer({0})".format(self.__uid)

    def __str__(self):
        """
        Peer pretty representation
        """
        if self.__name and self.__name != self.__uid:
            return "{0} ({1})".format(self.__name, self.__uid)
        else:
            return self.__uid

    def __hash__(self):
        """
        Use the UID string hash as bean hash
        """
        return hash(self.__uid)

    def __eq__(self, other):
        """
        Equality is based on the UID
        """
        if isinstance(other, Peer):
            return self.__uid == other.uid
        return False

    def __lt__(self, other):
        """
        Ordering is based on the UID
        """
        if isinstance(other, Peer):
            return self.__uid < other.uid
        return False

    @property
    def uid(self):
        """
        Retrieves the UID of the peer
        """
        return self.__uid

    @property
    def app_id(self):
        """
        Returns the ID of the application this peer is part of
        """
        return self.__app_id

    @property
    def name(self):
        """
        Retrieves the name of the peer
        """
        return self.__name

    @name.setter
    def name(self, value):
        """
        Sets the name of the peer

        :param value: A peer name
        """
        self.__name = value or self.__uid

    @property
    def node_uid(self):
        """
        Retrieves the UID of the node hosting the peer
        """
        return self.__node

    @property
    def node_name(self):
        """
        Retrieves the name of the node hosting the peer
        """
        return self.__node_name

    @node_name.setter
    def node_name(self, value):
        """
        Sets the name of the node hosting the peer

        :param value: A node name
        """
        self.__node_name = value or self.__node

    @property
    def groups(self):
        """
        Retrieves the set of groups this peer belongs
        """
        return self.__groups.copy()

    def __callback(self, method_name, *args):
        """
        Calls back the associated directory

        :param method_name: Name of the method to call
        :param args: Arguments of the method to call back
        """
        try:
            method = getattr(self.__directory, method_name)
        except AttributeError:
            # Directory not available/not fully implemented
            pass
        else:
            # Always give this bean as first parameter
            return method(self, *args)

    def dump(self):
        """
        Dumps the content of this Peer into a dictionary

        :return: A dictionary describing this peer
        """
        # Properties
        dump = {name: getattr(self, name)
                for name in ('uid', 'name', 'node_uid', 'node_name',
                             'app_id', 'groups')}

        # Accesses
        dump['accesses'] = {access: data.dump()
                            for access, data in self.__accesses.items()}
        return dump

    def get_access(self, access_id):
        """
        Retrieves the description of the access stored with the given ID

        :param access_id: An access ID (xmpp, http, ...)
        :return: The description associated to the given ID
        :raise KeyError: Access not described
        """
        return self.__accesses[access_id]

    def get_accesses(self):
        """
        Returns the list of access IDs associated to this peer

        :return: A list of access IDs
        """
        return tuple(self.__accesses)

    def has_access(self, access_id):
        """
        Checks if the access is described

        :param access_id: An access ID
        :return: True if the access is described
        """
        return access_id in self.__accesses

    def has_accesses(self):
        """
        Checks if the peer has any access

        :return: True if the peer has at least one access
        """
        return bool(self.__accesses)

    def set_access(self, access_id, data):
        """
        Sets the description associated to an access ID.

        :param access_id: An access ID (xmpp, http, ...)
        :param data: The description associated to the given ID
        """
        with self.__lock:
            try:
                old_data = self.__accesses[access_id]
            except KeyError:
                # Unknown data
                old_data = None

            if data != old_data:
                # Update only if necessary
                self.__accesses[access_id] = data

                if not isinstance(data, RawAccess):
                    self.__callback("peer_access_set", access_id, data)

    def unset_access(self, access_id):
        """
        Removes and returns the description associated to an access ID.

        :param access_id: An access ID (xmpp, http, ...)
        :return: The associated description, or None
        """
        with self.__lock:
            try:
                data = self.__accesses.pop(access_id)
            except KeyError:
                # Unknown access
                return None
            else:
                # Notify the directory
                self.__callback("peer_access_unset", access_id, data)
                return data

# ------------------------------------------------------------------------------


class Target(object):
    """
    The description of a target, used in exceptions
    """
    def __init__(self, uid=None, group=None, uids=None, peer=None):
        """
        Sets the target definition. Only one argument should be set at once.

        :param uid: The UID of the targeted peer
        :param group: The targeted group
        :param uids: The UIDs of the targeted peers (for groups only)
        :param peer: A Peer bean
        """
        if peer is not None:
            self.__uid = peer.uid
        else:
            self.__uid = uid
        self.__group = group
        self.__uids = uids or []

    @property
    def uid(self):
        """
        The UID of the targeted peer
        """
        return self.__uid

    @property
    def group(self):
        """
        The targeted group
        """
        return self.__group

    @property
    def uids(self):
        """
        The UIDs of the targeted peers (for groups only)
        """
        return self.__uids

# ------------------------------------------------------------------------------


class RawAccess(object):
    """
    A peer access stored while no transport directory can load it
    """
    def __init__(self, access_id, raw_data):
        """
        Sets up the bean

        :param access_id: Access ID associated to the data
        :param raw_data: Raw data to store
        """
        self.__access_id = access_id
        self.__raw_data = raw_data

    @property
    def access_id(self):
        """
        The access ID associated to the data
        """
        return self.__access_id

    @property
    def data(self):
        """
        The stored data
        """
        return self.__raw_data

    def dump(self):
        """
        The dump method returns the raw data as-is
        """
        return self.__raw_data

# ------------------------------------------------------------------------------


class DelayedNotification(object):
    """
    Bean to use for delayed notification of peer registration
    """
    def __init__(self, peer, notification_method):
        """
        Sets up the bean

        :param peer: The peer being registered
        :param notification_method: The method to call to notify listeners
        (can be None to ignore notification)
        """
        self.__peer = peer
        self.__method = notification_method

    @property
    def peer(self):
        """
        The peer being registered
        """
        return self.__peer

    def notify(self):
        """
        Calls the notification method

        :return: True if the notification method has been called
        """
        if self.__method is not None:
            self.__method(self.__peer)
            return True
        return False

# ------------------------------------------------------------------------------


class Message(object):
    """
    Represents a message to be sent
    """
    def __init__(self, subject, content=None):
        """
        Sets up members

        :param subject: Subject of the message
        :param content: Content of the message (optional)
        """
        self._subject = subject
        self._content = content
        
        self._headers = {}
        self._headers[herald.MESSAGE_HERALD_VERSION] = herald.HERALD_SPECIFICATION_VERSION
        self._headers[herald.MESSAGE_HEADER_TIMESTAMP] = int(time.time() * 1000) 
        self._headers[herald.MESSAGE_HEADER_UID] = str(uuid.uuid4()).replace('-', '').upper()
        
        self._metadata = {}  

    def __str__(self):
        """
        String representation
        """
        return "{0} ({1})".format(self._subject, self.uid)

    @property
    def subject(self):
        """
        The subject of the message
        """
        return self._subject

    @property
    def content(self):
        """
        The content of the message
        """
        return self._content

    @property
    def timestamp(self):
        """
        Time stamp of the message
        """
        return self._headers[herald.MESSAGE_HEADER_TIMESTAMP]

    @property
    def uid(self):
        """
        Message UID
        """
        return self._headers[herald.MESSAGE_HEADER_UID]

    @property
    def headers(self):
        """
        Message headers
        """
        return self._headers
    
    @property    
    def metadata(self):
        """
        Message metadata
        """
        return self._metadata

    def add_header(self, key, value):
        """
        Adds a header
        """
        self._headers[key] = value
        
    def get_header(self, key):
        """
        Gets a header value 
        """
        if key in self._headers:
            return self._headers[key]       
        return None

    def remove_header(self, key):
        """
        Removes a header from the headers list
        """
        if key in self._headers:
            del self._headers[key]

    def set_content(self, content):
        """
        Set content
        """
        self._content = content
        
    def add_metadata(self, key, value):
        """
        Adds a metadata
        """
        self._metadata[key] = value
        
    def get_metadata(self, key):
        """
        Gets a metadata
        """
        if key in self._metadata:
            return self._metadata[key]
        return None
        
    def remove_metadata(self, key):
        """
        Removes a metadata 
        """
        if key in self._metadata:
            del self._metadata[key]
            
            
class MessageReceived(Message):
    """
    Represents a message received by a transport
    """
    def __init__(self, uid, subject, content, sender_uid, reply_to, access,
                 timestamp=None, extra=None):
        """
        Sets up the bean

        :param uid: Message UID
        :param subject: Subject of the message
        :param content: Content of the message
        :param sender_uid: UID of the sending peer
        :param reply_to: UID of the message this one replies to
        :param access: Access ID of the transport which received this message
        :param timestamp: Message sending time stamp
        :param extra: Extra configuration for the transport in case of reply
        """
        Message.__init__(self, subject, content)
        self._headers[herald.MESSAGE_HEADER_UID] = uid
        self._headers[herald.MESSAGE_HEADER_SENDER_UID] = sender_uid
        self._headers[herald.MESSAGE_HEADER_REPLIES_TO] = reply_to
        self._access = access
        self._extra = extra
        self._headers[herald.MESSAGE_HEADER_TIMESTAMP] = timestamp

    def __str__(self):
        """
        String representation
        """
        return "{0} ({1}) from {2}".format(self._subject, self.uid,
                                           self.sender)

    @property
    def access(self):
        """
        Returns the access ID of the transport which received this message
        """
        return self._access

    @property
    def reply_to(self):
        """
        UID of the message this one replies to
        """
        return self._headers[herald.MESSAGE_HEADER_REPLIES_TO]

    @property
    def sender(self):
        """
        UID of the peer that sent this message
        """
        return self._headers[herald.MESSAGE_HEADER_SENDER_UID]

    @property
    def extra(self):
        """
        Extra information set by the transport that received this message
        """
        return self._extra

    def set_access(self, access):
        """
        Sets the access
        """
        self._access = access
        
    def set_extra(self, extra):
        """
        Sets the extra
        """
        self._extra = extra