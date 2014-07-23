#!/usr/bin/python
# -- Content-Encoding: UTF-8 --
"""
Herald XMPP transport implementation
"""

# Herald
from herald.exceptions import InvalidPeerAccess
from .bot import HeraldBot

# Pelix
import pelix.constants
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
@Requires('_directory', 'herald.xmpp.directory')
@Provides('herald.xmpp.transport', '_controller')
@Property('_access_id', 'herald.access.id', 'xmpp')
@Property('_host', 'xmpp.server', 'localhost')
@Property('_port', 'xmpp.port', 5222)
@Property('_monitor_jid', 'herald.monitor.jid', "bot@phenomtwo3000")
@Property('_key', 'herald.xmpp.key', "42")
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

        # Bundle context
        self._context = None

        # Properties
        self._access_id = "xmpp"
        self._host = "localhost"
        self._port = 5222
        self._monitor_jid = None
        self._key = "42"

        # XMPP bot
        self._bot = HeraldBot()

    @Validate
    def _validate(self, context):
        """
        Component validated
        """
        # Ensure we do not provide the service at first
        self._controller = False
        self._context = context

        # Setup the bot
        self._bot.set_callbacks(self.__on_start, self.__on_end,
                                self.__on_message)

        # Connect to the server
        self._bot.connect(self._host, self._port, use_tls=False)

    @Invalidate
    def _invalidate(self, context):
        """
        Component invalidated
        """
        # Disconnect the bot and clear callbacks
        self._bot.disconnect()
        self._bot.set_callbacks()

    def __on_start(self, data):
        """
        XMPP session started
        """
        # Log our JID
        _logger.info("Bot connected with JID: %s", self.boundjid.bare)

        # Get our framework UID
        local_uid = self._context.get_property(pelix.constants.FRAMEWORK_UID)

        # Ask the monitor to invite us, using our UID as nickname
        self._bot.herald_join(self._monitor_jid, self._key, local_uid)

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
                sender_uid = self._directory.from_jid(sender_jid)
        except KeyError:
            sender_uid = "<unknown>"

        subject = msg['subject']
        content = json.loads(msg['body'])
        uid = msg['thread']
        replies_to = msg['thread']['parent']

        # Extra parameters, for a reply
        extra = {"parent_uid": uid,
                 "sender_jid": sender_jid}

        # Call back the core service
        self._core.handle_message(sender_uid, subject, content, replies_to,
                                  extra)

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
        # Shut down the service
        self._controller = False


    def __send_message(self, msgtype, target, message):
        """
        Prepares and sends a message over XMPP

        :param msgtype: Kind of message (chat or groupchat)
        :param target: Target JID or MUC room
        :param message: Herald message bean
        :param body: The serialized form of the message body. If not given,
                     the content is the string form of the message.content field
        """
        # Prepare an XMPP message, based on the Herald message
        xmpp_msg = self.make_message(mto=target,
                                     mbody=json.dumps(message.content),
                                     msubject=message.subject,
                                     mtype=msgtype)
        xmpp_msg['thread'] = message.uid

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
