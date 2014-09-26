#!/usr/bin/python
# -- Content-Encoding: UTF-8 --
"""
Herald XMPP transport implementation

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
from . import FACTORY_TRANSPORT, SERVICE_XMPP_DIRECTORY, ACCESS_ID, \
    PROP_XMPP_SERVER, PROP_XMPP_PORT, PROP_MONITOR_JID, PROP_MONITOR_KEY, \
    PROP_XMPP_ROOM_JID
from .beans import XMPPAccess
from .bot import HeraldBot

# Herald Core
from herald.exceptions import InvalidPeerAccess
import herald
import herald.beans as beans
import herald.utils as utils

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


@ComponentFactory(FACTORY_TRANSPORT)
@Requires('_core', herald.SERVICE_HERALD_INTERNAL)
@Requires('_directory', herald.SERVICE_DIRECTORY)
@Requires('_xmpp_directory', SERVICE_XMPP_DIRECTORY)
@Provides(herald.SERVICE_TRANSPORT, '_controller')
@Property('_access_id', herald.PROP_ACCESS_ID, ACCESS_ID)
@Property('_host', PROP_XMPP_SERVER, 'localhost')
@Property('_port', PROP_XMPP_PORT, 5222)
@Property('_monitor_jid', PROP_MONITOR_JID)
@Property('_key', PROP_MONITOR_KEY)
@Property('_room', PROP_XMPP_ROOM_JID)
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
        self._access_id = ACCESS_ID
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
        self._bot.herald_join(peer.uid, self._monitor_jid, self._key,
                              peer.groups)

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
        local_peer = self._directory.get_local_peer()

        if uid == local_peer.uid and room_jid == self._room:
            # We're on line, in the main room, register our service
            self._controller = True

            # Register our local access
            local_peer.set_access(self._access_id,
                                  XMPPAccess(self._bot.boundjid.full))

            # Send the "new comer" message
            message = beans.Message('herald/directory/newcomer',
                                    local_peer.dump())
            self.__send_message("groupchat", room_jid, message)

    def __room_out(self, data):
        """
        Someone exited the main room

        :param data: MUC presence stanza
        """
        uid = data['from'].resource
        room_jid = data['from'].bare

        if uid != self._directory.local_uid and room_jid == self._room:
            # Someone else is leaving the main room: clean up the directory
            try:
                peer = self._directory.get_peer(uid)
                peer.unset_access(ACCESS_ID)
            except KeyError:
                pass

    def __send_message(self, msgtype, target, message, parent_uid=None):
        """
        Prepares and sends a message over XMPP

        :param msgtype: Kind of message (chat or groupchat)
        :param target: Target JID or MUC room
        :param message: Herald message bean
        :param parent_uid: UID of the message this one replies to (optional)
        """
        # Convert content to JSON
        content = json.dumps(message.content, default=utils.json_converter)

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

    def __get_jid(self, peer, extra):
        """
        Retrieves the JID to use to communicate with a peer

        :param peer: A Peer bean or None
        :param extra: The extra information for a reply or None
        :return: The JID to use to reply, or None
        """
        # Get JID from reply information
        jid = None
        if extra is not None:
            jid = extra.get('sender_jid')

        # Try to read information from the peer
        if not jid and peer is not None:
            try:
                # Get the target JID
                jid = peer.get_access(self._access_id).jid
            except (KeyError, AttributeError):
                pass

        return jid

    def fire(self, peer, message, extra=None):
        """
        Fires a message to a peer

        :param peer: A Peer bean
        :param message: Message to send
        :param extra: Extra information used in case of a reply
        """
        # Get the request message UID, if any
        parent_uid = None
        if extra is not None:
            parent_uid = extra.get('parent_uid')

        # Try to read extra information
        jid = self.__get_jid(peer, extra)

        if jid:
            # Send the XMPP message
            self.__send_message("chat", jid, message, parent_uid)
        else:
            # No XMPP access description
            raise InvalidPeerAccess(beans.Target(uid=peer.uid),
                                    "No '{0}' access found"
                                    .format(self._access_id))

    def fire_group(self, group, peers, message):
        """
        Fires a message to a group of peers

        :param group: Name of a group
        :param peers: Peers to communicate with
        :param message: Message to send
        :return: The list of reached peers
        """
        # Special case for the main room
        if group == 'all':
            group_jid = self._room
        else:
            # Get the group JID
            group_jid = sleekxmpp.JID(local=group, domain=self._muc_domain)

        # Send the XMPP message
        self.__send_message("groupchat", group_jid, message)
        return peers
