#!/usr/bin/python
# -- Content-Encoding: UTF-8 --
"""
:author: Thomas Calmant
:copyright: Copyright 2014, isandlaTech
:license: Apache License 2.0
:version: 1.0.0
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
__version_info__ = (1, 0, 0)
__version__ = ".".join(str(x) for x in __version_info__)

# Documentation strings format
__docformat__ = "restructuredtext en"

# ------------------------------------------------------------------------------

# Herald XMPP
from . import FACTORY_TRANSPORT, SERVICE_XMPP_DIRECTORY, ACCESS_ID, \
    PROP_XMPP_SERVER, PROP_XMPP_PORT, PROP_XMPP_JID, PROP_XMPP_PASSWORD, \
    PROP_XMPP_KEEPALIVE_INTERVAL, PROP_XMPP_KEEPALIVE_DELAY
from .beans import XMPPAccess
from .bot import HeraldBot
import herald.transports.peer_contact as peer_contact

# Room creation utility
from .utils import RoomCreator, MarksCallback

# Herald Core
from herald.exceptions import InvalidPeerAccess
import herald
import herald.beans as beans
import herald.utils as utils

# XMPP
import sleekxmpp

# Pelix
from pelix.ipopo.decorators import ComponentFactory, Requires, Provides, \
    Property, Validate, Invalidate, RequiresBest
from pelix.utilities import to_str, to_bytes
import pelix.misc.jabsorb as jabsorb
import pelix.threadpool as threadpool

# Standard library
import hashlib
import json
import logging
import threading
import time
import uuid

# ------------------------------------------------------------------------------

_logger = logging.getLogger(__name__)

FEATURE_MUC = 'http://jabber.org/protocol/muc'

# ------------------------------------------------------------------------------


@ComponentFactory(FACTORY_TRANSPORT)
@RequiresBest('_probe', herald.SERVICE_PROBE)
@Requires('_herald', herald.SERVICE_HERALD_INTERNAL)
@Requires('_directory', herald.SERVICE_DIRECTORY)
@Requires('_xmpp_directory', SERVICE_XMPP_DIRECTORY)
@Provides(herald.SERVICE_TRANSPORT, '_controller')
@Property('_access_id', herald.PROP_ACCESS_ID, ACCESS_ID)
@Property('_host', PROP_XMPP_SERVER, 'localhost')
@Property('_port', PROP_XMPP_PORT, 5222)
@Property('_username', PROP_XMPP_JID)
@Property('_password', PROP_XMPP_PASSWORD)
@Property('_xmpp_keepalive_interval', PROP_XMPP_KEEPALIVE_INTERVAL, 15)
@Property('_xmpp_keepalive_delay', PROP_XMPP_KEEPALIVE_DELAY, 5)
class XmppTransport(object):
    """
    XMPP Messenger for Herald.
    """

    def __init__(self):
        """
        Sets up the transport
        """
        # Probe service
        self._probe = None

        # Herald core service
        self._herald = None

        # Herald Core directory
        self._directory = None

        # Herald XMPP directory
        self._xmpp_directory = None

        # Service controller
        self._controller = False

        # Peer contact handling
        self.__contact = None

        # Properties
        self._access_id = ACCESS_ID
        self._host = "localhost"
        self._port = 5222
        self._username = None
        self._password = None
        # Herald XMPP Keppalive interval
        self._xmpp_keepalive_interval = 15
        # Herald XMPP Keepalive delay
        self._xmpp_keepalive_delay = 5

        # XMPP bot
        self._authenticated = False
        self._bot = None

        # MUC service name
        self.__muc_service = None

        # Pending count downs and joined rooms
        self.__countdowns = set()
        self.__countdowns_lock = threading.Lock()

        # Message sending queue
        self.__pool = threadpool.ThreadPool(max_threads=1,
                                            logname="Herald-XMPP-SendThread")

        # Bot possible states : creating, created, destroying, destroyed
        self._bot_state = "destroyed"

        # Bot state's lock
        self._bot_lock = threading.RLock()

        # Bot method recall timer
        self._bot_recall_timer = None

    @Validate
    def _validate(self, _):
        """
        Component validated
        """
        self.__create_new_bot()

    def __create_new_bot(self):
        """
        (Re)Creates a new XMPP bot object
        """
        # Cancel the current timer
        if self._bot_recall_timer is not None:
            self._bot_recall_timer.cancel()
            self._bot_recall_timer = None

        with self._bot_lock:
            if self._bot_state == "destroyed":
                threading.Thread(target=self._create_new_bot,
                                 name="Herald-CreateBot").start()
                self._bot_state = "creating"
                _logger.info("changing XMPP bot state to : creating")

            elif self._bot_state == "destroying":
                # Wait before trying to create new bot
                self._bot_recall_timer = \
                    threading.Timer(1, self.__create_new_bot)
                self._bot_recall_timer.start()

            elif self._bot_state == "creating":
                pass
            elif self._bot_state == "created":
                pass

    def _create_new_bot(self):
        """
        Really (re)creates a new XMPP bot object
        """
        # Clear & Start the thread pool
        self.__pool.clear()
        self.__pool.start()

        # Prepare the peer contact handler
        self.__contact = peer_contact.PeerContact(self._directory, None,
                                                  __name__ + ".contact")

        if self._username:
            # Generate the bot full JID: resource is set to be peer's UUID
            bot_jid = sleekxmpp.JID(self._username)
            bot_jid.resource = self._directory.local_uid
        else:
            # Anonymous login
            bot_jid = None

        # Create the bot
        self._bot = HeraldBot(bot_jid, self._password,
                              self._directory.local_uid)

        # Avoids bot's auto reconnection.
        # when disconnected event is captured,
        # we destroy the old bot and re-create a new one.
        self._bot.auto_reconnect = False

        # This avoids to wait too long between initial reattempts, i.e. if
        # the first server addresses (DNS records) aren't responding
        self._bot.reconnect_max_delay = 5

        # Register to session events
        self._bot.add_event_handler("session_start", self._on_session_start)
        self._bot.add_event_handler("failed_auth", self._on_failed_auth)
        self._bot.add_event_handler("session_end", self._on_session_end)
        self._bot.add_event_handler("disconnected", self._on_disconnected)

        # Register the Multi-User Chat plug-in
        self._bot.register_plugin('xep_0045')

        # Register "XEP-0203: Delayed Delivery" plug-in
        self._bot.register_plugin("xep_0203")

        # Register to messages (loop back filtered by the bot)
        self._bot.set_message_callback(self.__on_message)

        # Connect to the server
        # set reattempt to True to try to reconnect to the server in case of
        # network problems or address errors.
        if not self._bot.connect(self._host, self._port, reattempt=True):
            _logger.error("Can't connect to the XMPP server at %s port %s",
                          self._host, self._port)
            # the bot is fully created and activated when all rooms are created
            # (see __on_ready)

    def __destroy_bot(self):
        """
        Destroys the current bot
        """
        # Cancel the current timer
        if self._bot_recall_timer is not None:
            self._bot_recall_timer.cancel()
            self._bot_recall_timer = None

        with self._bot_lock:
            if self._bot_state == "destroyed":
                pass
            elif self._bot_state == "destroying":
                pass

            elif self._bot_state == "creating":
                # Wait before trying to destroying existing bot
                self._bot_recall_timer = threading.Timer(1, self.__destroy_bot)
                self._bot_recall_timer.start()

            elif self._bot_state == "created":
                # Destroy the bot, in a new thread
                threading.Thread(target=self._destroy_bot,
                                 name="Herald-DestroyBot").start()
                self._bot_state = "destroying"
                _logger.info("changing XMPP bot state to : destroying")

    def _destroy_bot(self):
        """
        Destroys the current bot
        """
        # Stop & Clear the pool
        self.__pool.stop()
        self.__pool.clear()

        # Disconnect the bot and clear callbacks
        if self._bot is not None:
            # self._bot.plugin['xep_0199'].disable_keepalive()
            self._bot.set_message_callback(None)
            self._bot.del_event_handler("session_start", self._on_session_start)
            self._bot.del_event_handler("failed_auth", self._on_failed_auth)
            self._bot.del_event_handler("session_end", self._on_session_end)
            self._bot.del_event_handler("disconnected", self._on_disconnected)

            self._bot.disconnect(reconnect=False)
            self._bot.set_stop()
            self._bot = None
        else:
            _logger.warning("trying to destroy an already destroyed XMPP bot!")

        # Clean up internal storage
        if self.__contact is not None:
            self.__contact.clear()
            self.__contact = None
        if self._bot_lock:
            # unregister provided service
            self._controller = False
            # change state
            self._bot_state = "destroyed"
            _logger.info("changing XMPP bot state to : destroyed")

    @Invalidate
    def _invalidate(self, _):
        """
        Component invalidated
        """
        self.__destroy_bot()

    def room_jid(self, room_name):
        """
        Prepares a JID object for the given room in the current MUC domain

        :param room_name: The short name of a room
        :return: A JID object
        """
        if self.__muc_service == "groupchat.google.com":
            # Special case: Google Talk requires a specific room name format
            # Make a MD5 hash of the full room name
            app_id = self._directory.get_local_peer().app_id
            full_name = "cohorte-{0}-{1}".format(app_id, room_name)
            md5 = hashlib.md5(to_bytes(full_name)).hexdigest()

            # Format the room name to be Google Talk-compatible
            room_name = "private-chat-{0}".format(str(uuid.UUID(md5)))

        return sleekxmpp.JID(local=room_name, domain=self.__muc_service)

    def __create_rooms(self, rooms, nickname):
        """
        Creates or joins the given rooms

        :param rooms: A list of rooms to join / create
        :param nickname: Nickname to use in MUC rooms
        :raise ValueError: No Multi-User Chat service available
        """
        # Look for the MUC service if necessary
        if not self.__muc_service:
            if self._bot.boundjid.domain == "gmail.com":
                # Special case: Google Talk
                self.__muc_service = "groupchat.google.com"
            else:
                try:
                    self.__muc_service = next(
                        self._bot.iter_services(FEATURE_MUC))
                except StopIteration:
                    raise ValueError("No Multi-User Chat service on server")

        # Generate rooms JIDs
        rooms_jids = {room: self.room_jid(room) for room in rooms}

        # Prepare a callback
        self.__countdowns.add(
            MarksCallback((str(room_jid) for room_jid in rooms_jids.values()),
                          self.__on_ready, __name__ + ".RoomCreator"))

        # Prepare the room creator
        creator = RoomCreator(self._bot, __name__ + ".RoomCreator")

        # Prepare rooms configuration
        rooms_config = {
            # ... no max users limit
            'muc#roomconfig_maxusers': '0',
            # ... open to anyone
            'muc#roomconfig_membersonly': '0',
            # ... every participant can send invites
            'muc#roomconfig_allowinvites': '1',
            # ... room can disappear
            'muc#roomconfig_persistentroom': '0',
            # ... OpenFire: Forbid nick changes
            'x-muc#roomconfig_canchangenick': '0'}

        # Create rooms, with our computing JID
        for room, room_jid in rooms_jids.items():
            creator.create_room(room, self.__muc_service, nickname,
                                rooms_config, self.__room_created,
                                self.__room_error, room_jid)

    def __room_created(self, room, _):
        """
        A room has been correctly created, and we're its owner

        :param room: Bare JID of the room
        :param _: Our nick in the room
        """
        with self.__countdowns_lock:
            to_remove = set()
            for countdown in self.__countdowns:
                # Mark the room
                countdown.set(room)

                # Check for cleanup
                if countdown.is_done():
                    to_remove.add(countdown)

            # Cleanup
            self.__countdowns.difference_update(to_remove)

    def __room_error(self, room, nick, condition, text):
        """
        Error creating a room

        :param room: Bare JID of the room
        :param nick: Our nick in the room
        :param condition: Category of error
        :param text: Description of the error
        """
        if condition == 'not-owner':
            _logger.debug("We are not the owner of %s", room)
            self.__room_created(room, nick)
        else:
            with self.__countdowns_lock:
                to_remove = set()
                for countdown in self.__countdowns:
                    # Mark the room
                    countdown.set_error(room)

                    # Check for cleanup
                    if countdown.is_done():
                        to_remove.add(countdown)

                # Cleanup
                self.__countdowns.difference_update(to_remove)

            _logger.error("Error creating room: %s (%s)", text, condition)

    def _on_failed_auth(self, _):
        """
        An authentication attempt failed
        """
        self._authenticated = False

    def _on_session_start(self, _):
        """
        The bot session has started: create the main room
        """
        self._authenticated = True

        # Log our JID
        _logger.info("Bot connected with JID: %s", self._bot.boundjid.bare)

        # Get our local peer description
        peer = self._directory.get_local_peer()

        # Create/join rooms for each group
        all_rooms = ["{0}--{1}".format(peer.app_id, group)
                     for group in peer.groups]
        all_rooms.append(peer.app_id)

        # Wait to have joined all rooms before activating the service
        _logger.debug("Creating XMPP rooms...")
        self.__create_rooms(all_rooms, peer.uid)

        # activate keepalive (ping) plugin xep_0199
        self._bot.plugin['xep_0199'].enable_keepalive(
            self._xmpp_keepalive_interval, self._xmpp_keepalive_delay)


    def __on_ready(self, joined, erroneous):
        """
        Called when all MUC rooms have created or joined

        :param joined: List of joined rooms
        :param erroneous: List of room that couldn't be joined
        """
        _logger.debug("Client joined rooms: %s", ", ".join(joined))
        if erroneous:
            _logger.error("Error joining rooms: %s", ", ".join(erroneous))

        # Register our local access
        local_peer = self._directory.get_local_peer()
        local_peer.set_access(self._access_id,
                              XMPPAccess(self._bot.boundjid.full))

        # Listen to peers going away from the main room
        self._bot.add_event_handler(
            "muc::{0}::got_offline".format(self.room_jid(local_peer.app_id)),
            self._on_room_out)

        if self._bot_lock:
            # We're on line, register our service
            _logger.debug("XMPP transport service activating...")
            self._controller = True
            _logger.info("XMPP transport service activated")
            self._bot_state = "created"
            _logger.info("changing XMPP bot state to : created")

        # Start the discovery handshake, with everybody
        _logger.debug("Sending discovery step 1...")
        message = beans.Message(peer_contact.SUBJECT_DISCOVERY_STEP_1,
                                local_peer.dump())
        self.__send_message("groupchat", self.room_jid(local_peer.app_id),
                            message)

    def _on_session_end(self, _):
        """
        End of session
        """
        if self._authenticated:
            _logger.info("End of session")
        else:
            _logger.warning("End of session due to authentication error")

        with self._bot_lock:
            if self._bot_state in ("creating", "created"):
                # disable keepalive plugin
                self._bot.plugin['xep_0199'].disable_keepalive()
                # try:
                # Clean up our access
                local_peer = self._directory.get_local_peer()
                if local_peer is not None:
                    local_peer.unset_access(self._access_id)

                    # Shut down the service (MOD: see _destroy_bot)
                    # self._controller = False

                    # Stop listening to the main room
                    # Listen to peers going away from the main room
                    self._bot.del_event_handler(
                        "muc::{0}::got_offline".format(
                            self.room_jid(local_peer.app_id)),
                        self._on_room_out)
                    # except:
                    # pass

    def _on_room_out(self, data):
        """
        Someone exited the main room

        :param data: MUC presence stanza
        """
        uid = data['from'].resource
        room_jid = data['from'].bare
        local_peer = self._directory.get_local_peer()
        app_room_jid = self.room_jid(local_peer.app_id)

        if uid != self._directory.local_uid and room_jid == app_room_jid:
            # Someone else is leaving the main room: clean up the directory
            try:
                peer = self._directory.get_peer(uid)
                peer.unset_access(ACCESS_ID)
            except KeyError:
                pass
            else:
                _logger.debug("Peer %s disconnected from XMPP", peer)

    def _on_disconnected(self, _):
        """
        The bot has been disconnected, maybe due to a network problem
        """
        # create a new bot (which implies the deletion of the old one)
        _logger.warning("Bot disconnected: reconnect (state=%s)",
                        self._bot_state)
        
        with self._bot_lock:
            # Destroy the old bot, if any
            if self._bot_state == "created":
                self.__destroy_bot()

        # Create a new bot
        self.__create_new_bot()

    def __on_message(self, msg):
        """
        Received an XMPP message

        :param msg: A message stanza
        """
        if msg['delay']['stamp'] is not None:
            # Delayed message: ignore
            return

        subject = msg['subject']
        if not subject:
            # No subject: not an Herald message, treat it differently
            self.__handle_raw_message(msg)
            return

        # Check if the message is from Multi-User Chat or direct
        muc_message = msg['type'] == 'groupchat' \
            or msg['from'].domain == self.__muc_service

        sender_jid = msg['from'].full
        try:
            if muc_message:
                # Group message: resource is the isolate UID
                sender_uid = msg['from'].resource
            else:
                sender_uid = self._xmpp_directory.from_jid(sender_jid).uid
        except KeyError:
            sender_uid = "<unknown>"

        try:            
            received_msg = utils.from_json(msg['body'])
            content = received_msg.content
        except ValueError:
            # Content can't be decoded, use its string representation as is
            content = msg['body']

        uid = msg['thread']
        reply_to = msg['parent_thread']

        # Extra parameters, for a reply
        extra = {"parent_uid": uid,
                 "sender_jid": sender_jid}
                 
        received_msg.add_header(herald.MESSAGE_HEADER_UID, uid)
        received_msg.add_header(herald.MESSAGE_HEADER_SENDER_UID, sender_uid)
        received_msg.add_header(herald.MESSAGE_HEADER_REPLIES_TO, reply_to)
        received_msg.set_content(content)
        received_msg.set_access(self._access_id)
        received_msg.set_extra(extra)
        
        # Call back the core service
        message = received_msg

        # Log before giving message to Herald
        self._probe.store(
            herald.PROBE_CHANNEL_MSG_RECV,
            {"uid": message.uid, "timestamp": time.time(),
             "transport": ACCESS_ID, "subject": message.subject,
             "source": sender_uid, "repliesTo": reply_to or "",
             "transportSource": str(sender_jid)})

        if subject.startswith(peer_contact.SUBJECT_DISCOVERY_PREFIX):
            # Handle discovery message
            self.__contact.herald_message(self._herald, message)
        else:
            # All other messages are given to Herald Core
            self._herald.handle_message(message)

    def __handle_raw_message(self, msg):
        """
        Handles a message that is not from Herald

        :param msg: An XMPP message
        """
        # Generate a UUID for this message
        uid = str(uuid.uuid4())

        # No sender
        sender_uid = "<unknown>"

        # Give the raw body as content
        content = msg['body']

        # Extra parameters, for a reply
        sender_jid = msg['from'].full
        extra = {"sender_jid": sender_jid, "raw": True}

        # Call back the core service
        message = beans.MessageReceived(uid, herald.SUBJECT_RAW,
                                        content, sender_uid,
                                        None, self._access_id, extra=extra)

        # Log before giving message to Herald
        self._probe.store(
            herald.PROBE_CHANNEL_MSG_RECV,
            {"uid": message.uid, "timestamp": time.time(),
             "transport": ACCESS_ID, "subject": message.subject,
             "source": sender_uid, "repliesTo": "",
             "transportSource": str(sender_jid)})

        # All other messages are given to Herald Core
        self._herald.handle_message(message)

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

    def __send_message(self, msgtype, target, message, parent_uid=None, target_peer=None, target_group=None):
        """
        Prepares and sends a message over XMPP

        :param msgtype: Kind of message (chat or groupchat)
        :param target: Target JID or MUC room
        :param message: Herald message bean
        :param parent_uid: UID of the message this one replies to (optional)
        """
        # Convert content to JSON
        if message.subject in herald.SUBJECTS_RAW:
            content = to_str(message.content)
        else:
            # update headers
            local_peer = self._directory.get_local_peer()
            message.add_header(herald.MESSAGE_HEADER_SENDER_UID, local_peer.uid)
            if target_peer is not None:
                message.add_header(herald.MESSAGE_HEADER_TARGET_PEER, target_peer.uid)
            if target_group is not None:
                message.add_header(herald.MESSAGE_HEADER_TARGET_GROUP, target_group)
            content = utils.to_json(message)
        
        # Prepare an XMPP message, based on the Herald message
        xmpp_msg = self._bot.make_message(mto=target,
                                          mbody=content,
                                          msubject=message.subject,
                                          mtype=msgtype)
        xmpp_msg['thread'] = message.uid
        if parent_uid:
            xmpp_msg['parent_thread'] = parent_uid

        # Store message content
        self._probe.store(
            herald.PROBE_CHANNEL_MSG_CONTENT,
            {"uid": message.uid, "content": content}
        )

        # Send it, using the 1-thread pool, and wait for its execution
        future = self.__pool.enqueue(xmpp_msg.send)
        return future.result()

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
            # Log before sending
            self._probe.store(
                herald.PROBE_CHANNEL_MSG_SEND,
                {"uid": message.uid, "timestamp": time.time(),
                 "transport": ACCESS_ID, "subject": message.subject,
                 "target": peer.uid if peer else "<unknown>",
                 "transportTarget": str(jid), "repliesTo": parent_uid or ""})

            # Send the XMPP message
            self.__send_message("chat", jid, message, parent_uid, target_peer=peer)
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
        # Get the local application ID
        app_id = self._directory.get_local_peer().app_id

        # Special case for the main room
        if group in ('all', 'others'):
            group_jid = self.room_jid(app_id)
        else:
            # Get the group JID
            group_jid = self.room_jid("{0}--{1}".format(app_id, group))

        # Log before sending
        self._probe.store(
            herald.PROBE_CHANNEL_MSG_SEND,
            {"uid": message.uid, "timestamp": time.time(),
             "transport": ACCESS_ID, "subject": message.subject,
             "target": group, "transportTarget": str(group_jid),
             "repliesTo": ""})

        # Send the XMPP message
        self.__send_message("groupchat", group_jid, message, target_group=group)
        return peers
