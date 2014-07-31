#!/usr/bin/python
# -- Content-Encoding: UTF-8 --
"""
Herald core beans definition
"""

# Standard library
import functools
import time
import uuid

# ------------------------------------------------------------------------------


@functools.total_ordering
class Peer(object):
    """
    Represents a peer in Herald
    """
    def __init__(self, uid, directory=None):
        """
        Sets up the peer

        :param uid: Peer Unique ID
        :param directory: Directory to call back on access update
        :raise ValueError: Invalid UID
        """
        if not uid:
            raise ValueError("The UID of a peer can't be empty")

        self.__uid = uid
        self.__name = uid
        self.__node = uid
        self.__node_name = uid
        self.__groups = set()
        self.__accesses = {}
        self.__directory = directory

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

    @node_uid.setter
    def node_uid(self, value):
        """
        Sets the UID of the node hosting the peer

        :param value: A node UID
        """
        self.__node = value or self.__uid
        if not self.__node_name:
            self.__node_name = self.__node

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
        self.__node_name = value or self.__node or self.__uid

    @property
    def groups(self):
        """
        Retrieves the set of groups this peer belongs
        """
        return self.__groups.copy()

    @groups.setter
    def groups(self, values):
        """
        Sets the groups this peer belong to. Callable only once.

        :param values: A list of names of groups
        """
        if not self.__groups:
            self.__groups.update(values)

    def __callback(self, method_name, *args):
        """
        Calls back the associated directory

        :param method_name: Name of the method to call
        :param *args: Arguments of the method to call back
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
                for name in ('uid', 'name', 'node_uid', 'node_name', 'groups')}

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
        self.__accesses[access_id] = data
        self.__callback("peer_access_set", access_id, data)

    def unset_access(self, access_id):
        """
        Removes and returns the description associated to an access ID.

        :param access_id: An access ID (xmpp, http, ...)
        :return: The associated description, or None
        """
        try:
            data = self.__accesses.pop(access_id)
        except KeyError:
            # Unknown access
            return None
        else:
            # Notify the directory
            self.__callback("peer_access_unset", access_id, data)
            return data

    def set_directory(self, directory):
        """
        Sets the directory associated to this peer

        :param directory: The directory to call back on update
        """
        self.__directory = directory

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
        self._uid = str(uuid.uuid4()).replace('-', '').upper()
        self._timestamp = int(time.time() * 1000)
        self._subject = subject
        self._content = content

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
        return self._timestamp

    @property
    def uid(self):
        """
        Message UID
        """
        return self._uid


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
        self._uid = uid
        self._sender = sender_uid
        self._reply_to = reply_to
        self._access = access
        self._extra = extra
        self._timestamp = timestamp

    def __str__(self):
        """
        String representation
        """
        return "{0} from {1}".format(self._subject, self._sender)

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
        return self._reply_to

    @property
    def sender(self):
        """
        UID of the peer that sent this message
        """
        return self._sender

    @property
    def extra(self):
        """
        Extra information set by the transport that received this message
        """
        return self._extra
