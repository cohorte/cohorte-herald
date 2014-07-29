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

# XMPP
import sleekxmpp

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
@Requires('_xmpp_directory', 'herald.directory.xmpp')
@Provides('herald.transport', '_controller')
@Property('_access_id', 'herald.access.id', 'xmpp')
@Property('_host', 'xmpp.server', 'localhost')
@Property('_port', 'xmpp.port', 5222)
@Property('_monitor_jid', 'herald.monitor.jid')
@Property('_key', 'herald.xmpp.key')
@Property('_room', 'herald.xmpp.room')
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

        # Herald Core directory
        self._directory = None

        # Herald XMPP directory
        self._xmpp_directory = None

        # Service controller
        self._controller = False

        # Properties
        self._access_id = "xmpp"
        self._host = "localhost"
        self._port = 5222
        self._monitor_jid = None
        self._key = None
        self._room = None

        # MUC service
        self._muc_domain = None

        # XMPP bot
        self._bot = HeraldBot()

    @Validate
    def _validate(self, context):
        """
        Component validated
        """
        # Ensure we do not provide the service at first
        self._controller = False

        # Compute the MUC domain
        self._muc_domain = sleekxmpp.JID(self._room).domain

        # Register to session events
        self._bot.add_event_handler("session_start", self.__on_start)
        self._bot.add_event_handler("session_end", self.__on_end)
        self._bot.add_event_handler("muc::{0}::got_online".format(self._room),
                                    self.__room_in)
        self._bot.add_event_handler("muc::{0}::got_offline".format(self._room),
                                    self.__room_out)

        # Register "XEP-0203: Delayed Delivery" plug-in
        self._bot.register_plugin("xep_0203")

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

    def __on_message(self, msg):
        """
        Received an XMPP message

        :param msg: A message stanza
        """
        subject = msg['subject']
        if not subject:
            # No subject: not an Herald message. Abandon.
            return

        if msg['delay']['stamp'] is not None:
            # Delayed message: ignore
            return

        # Check if the message is from Multi-User Chat or direct
        muc_message = (msg['type'] == 'groupchat') \
            or (msg['from'].domain == self._muc_domain)

        sender_jid = msg['from'].full
        try:
            if muc_message:
                # Group message: resource is the isolate UID
                sender_uid = msg['from'].resource
            else:
                sender_uid = self._xmpp_directory.from_jid(sender_jid)
        except KeyError:
            sender_uid = "<unknown>"

        try:
            content = json.loads(msg['body'])
        except ValueError:
            # Content can't be decoded, use its string representation as is
            content = msg['body']

        uid = msg['thread']
        reply_to = msg['parent_thread']

        # Extra parameters, for a reply
        extra = {"parent_uid": uid,
                 "sender_jid": sender_jid}

        # Call back the core service
        message = beans.MessageReceived(uid, subject, content, sender_uid,
                                        reply_to, self._access_id, extra=extra)
        self._core.handle_message(message)

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
        room_jid = data['from'].bare
        local = self._directory.get_local_peer()

        if uid == local.uid and room_jid == self._room:
            # We're on line, in the main room, register our service
            self._controller = True

            # Register our local access
            peer = self._directory.get_local_peer()
            peer.set_access(self._access_id,
                            XMPPAccess(self._bot.boundjid.full))

            # Send the "new comer" message
            message = beans.Message('herald/directory/newcomer', local.dump())
            self.__send_message("groupchat", room_jid, message)

    def __room_out(self, data):
        """
        Someone exited the main room

        :param data: MUC presence stanza
        """
        _logger.info("%s is exiting %s", data['from'].resource,
                     data['from'].user)

    def __send_message(self, msgtype, target, message, parent_uid=None):
        """
        Prepares and sends a message over XMPP

        :param msgtype: Kind of message (chat or groupchat)
        :param target: Target JID or MUC room
        :param message: Herald message bean
        :param parent_uid: UID of the message this one replies to (optional)
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
        if parent_uid:
            xmpp_msg['parent_thread'] = parent_uid

        # Send it
        xmpp_msg.send()

    def fire(self, peer, message, extra=None):
        """
        Fires a message to a peer
        """
        # Try to read extra information
        jid = None
        parent_uid = None
        if extra is not None:
            jid = extra.get('sender_jid')
            parent_uid = extra.get('parent_uid')

        # Try to read information from the peer
        if not jid and peer is not None:
            try:
                # Get the target JID
                jid = peer.get_access('xmpp').jid
            except (KeyError, AttributeError) as ex:
                pass

        if jid:
            # Send the XMPP message
            self.__send_message("chat", jid, message, parent_uid)
        else:
            # No XMPP access description
            raise InvalidPeerAccess("No '{0}' access found".format(ex))

    def fire_group(self, group, message, extra=None):
        """
        Fires a message to a group of peers
        """
        # Get the group JID
        group_jid = self._directory.get_group_jid(group)

        # Send the XMPP message
        self.__send_message("groupchat", group_jid, message)
