#!/usr/bin/python
# -- Content-Encoding: UTF-8 --
"""
Herald XMPP transport implementation
"""

# Herald
from herald.exceptions import InvalidPeerAccess
from .beans import XMPPAccess
from .bot import HeraldBot
import herald.beans as beans

# Pelix
from pelix.ipopo.decorators import ComponentFactory, Requires, Provides, \
    Property, Validate, Invalidate

# Standard library
import json
import logging

# ------------------------------------------------------------------------------

_logger = logging.getLogger(__name__)

# ------------------------------------------------------------------------------

@ComponentFactory("herald-xmpp-transport")
@Requires('_core', 'herald.core')
@Requires('_directory', 'herald.directory')
@Provides('herald.xmpp.transport', '_controller')
@Property('_access_id', 'herald.access.id', 'xmpp')
@Property('_host', 'xmpp.server', 'localhost')
@Property('_port', 'xmpp.port', 5222)
@Property('_monitor_jid', 'herald.monitor.jid', "bot@phenomtwo3000")
@Property('_key', 'herald.xmpp.key', "42")
@Property('_room', 'herald.xmpp.room', 'herald')
class XmppTransport(object):
    """
    XMPP Messenger for Herald.
    """
    def __init__(self):
        """
        Sets up the transport
        """
        # Herald core service
        self._core = None

        # Herald XMPP Directory
        self._directory = None

        # Service controller
        self._controller = False

        # Properties
        self._access_id = "xmpp"
        self._host = "localhost"
        self._port = 5222
        self._monitor_jid = None
        self._key = "42"
        self._room = 'herald'

        # XMPP bot
        self._bot = HeraldBot()

    @Validate
    def _validate(self, context):
        """
        Component validated
        """
        # Ensure we do not provide the service at first
        self._controller = False

        # Register to session events
        self._bot.add_event_handler("session_start", self.__on_start)
        self._bot.add_event_handler("session_end", self.__on_end)
        self._bot.add_event_handler("muc::{0}::got_online".format(self._room),
                                    self.__room_in)
        self._bot.add_event_handler("muc::{0}::got_offline".format(self._room),
                                    self.__room_out)

        _logger.info("Registering to event: %s",
                     "muc::{0}::got_offline".format(self._room))

        # Register to messages (loop back filtered by the bot)
        self._bot.set_message_callback(self.__on_message)

        # Connect to the server
        self._bot.connect(self._host, self._port, use_tls=False)

    @Invalidate
    def _invalidate(self, context):
        """
        Component invalidated
        """
        # Disconnect the bot and clear callbacks
        self._bot.disconnect()

        self._bot.set_message_callback(None)
        self._bot.del_event_handler("session_start", self.__on_start)
        self._bot.del_event_handler("session_end", self.__on_end)

    def __on_start(self, data):
        """
        XMPP session started
        """
        # Log our JID
        _logger.info("Bot connected with JID: %s", self._bot.boundjid.bare)

        # Get our local peer description
        peer = self._directory.get_local_peer()

        # Ask the monitor to invite us, using our UID as nickname
        _logger.info("Requesting to join %s", self._monitor_jid)
        self._bot.herald_join(peer.uid, self._monitor_jid, self._key)

        # We're on line, register our local access
        peer.set_access(self._access_id, XMPPAccess(self._bot.boundjid.full))

    def __on_message(self, data):
        """
        XMPP message received
        """
        if data['type'] == 'chat' and data['from'].bare == self._monitor_jid:
            # Direct Message from the monitor
            self._handle_monitor_message(data)

        # In any case, do the standard handling
        self._handle_message(data)

    def _handle_message(self, msg):
        """
        Received an XMPP message
        """
        sender_jid = msg['from'].full
        try:
            if msg['type'] == 'groupchat':
                # Group message: resource is the isolate UID
                sender_uid = msg['from'].resource
            else:
                # FIXME: sender_uid = self._directory.from_jid(sender_jid)
                sender_uid = "<unknown>"
        except KeyError:
            sender_uid = "<unknown>"

        try:
            content = json.loads(msg['body'])
        except ValueError:
            # Content can't be decoded, use its string representation as is
            content = msg['body']

        subject = msg['subject']
        uid = msg['thread']
        replies_to = msg['parent_thread']

        # Extra parameters, for a reply
        extra = {"parent_uid": uid,
                 "sender_jid": sender_jid}

        # Call back the core service
        # FIXME: Create a proper message bean with:
        # sender_uid, subject, content, replies_to, extra
        message = beans.Message(subject, content)
        self._core.handle_message(message)

    def _handle_monitor_message(self, msg):
        """
        Received an XMPP message directly from the monitor bot
        """
        parts = [part for part in msg['subject'].split('/') if part]
        if parts[:3] != ('herald', 'xmpp', 'directory'):
            # Not a directory update message
            return

        # Parse content
        content = json.loads(msg['body'])

        if parts[3] == 'register':
            # Register peer(s)
            for uid, descr in content.items():
                self._directory.register(uid, descr)

        elif parts[3] == 'unregister':
            # Remove peer(s)
            for uid, descr in content.items():
                self._directory.unregister(uid)

        elif parts[3] == 'dump':
            # Dump peers & reply to sender
            reply = json.dumps(self._directory.dump())
            msg.reply(reply).send()

    def __on_end(self, data):
        """
        XMPP session ended
        """
        # Clean up our access
        self._directory.get_local_peer().unset_access(self._access_id)

        # Shut down the service
        self._controller = False

    def __room_in(self, data):
        """
        Someone entered the main room

        :param data: MUC presence stanza
        """
        uid = data['from'].resource
        room = data['from'].user
        room_jid = data['from'].bare
        local = self._directory.get_local_peer()

        if uid == local.uid:
            # We're into a room
            _logger.info("I joined %s", room)

            if room_jid == self._room:
                # TODO: maybe set up the local access here
                _logger.info("I JOINED THE MAIN ROOM")
                message = beans.Message('/joining', local.dump())
                self.__send_message("groupchat", room_jid, message)

        else:
            _logger.info("%s is entering %s", data['from'].resource, room)

    def __room_out(self, data):
        """
        Someone exited the main room

        :param data: MUC presence stanza
        """
        _logger.info("%s is exiting %s", data['from'].resource,
                     data['from'].user)

    def __send_message(self, msgtype, target, message):
        """
        Prepares and sends a message over XMPP

        :param msgtype: Kind of message (chat or groupchat)
        :param target: Target JID or MUC room
        :param message: Herald message bean
        :param body: The serialized form of the message body. If not given,
                     the content is the string form of the message.content field
        """
        # Convert content to JSON, with a converter:
        # sets are converted into tuples
        def set_converter(obj):
            if isinstance(obj, (set, frozenset)):
                return tuple(obj)
            raise TypeError
        content = json.dumps(message.content, default=set_converter)

        # Prepare an XMPP message, based on the Herald message
        xmpp_msg = self._bot.make_message(mto=target,
                                          mbody=content,
                                          msubject=message.subject,
                                          mtype=msgtype)
        xmpp_msg['thread'] = message.uid

        _logger.info("Sending message: %s", xmpp_msg)

        # Send it
        xmpp_msg.send()

    def fire(self, peer, message):
        """
        Fires a message to a peer
        """
        try:
            # Get the target JID
            jid = peer.get_access('xmpp').jid

        except KeyError as ex:
            # No XMPP access description
            raise InvalidPeerAccess("No '{0}' access found".format(ex))

        else:
            # Send the XMPP message
            self.__send_message("chat", jid, message)

    def fire_group(self, group, message):
        """
        Fires a message to a group of peers
        """
        # Get the group JID
        group_jid = self._directory.get_group_jid(group)

        # Send the XMPP message
        self.__send_message("groupchat", group_jid, message)
