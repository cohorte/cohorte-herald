#!/usr/bin/python
# -- Content-Encoding: UTF-8 --
"""
Herald XMPP control robot implementation

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

# XMPP
from sleekxmpp import JID

# Herald XMPP
from . import FACTORY_MONITOR, SERVICE_MONITOR_BOT, \
    PROP_MONITOR_JID, PROP_MONITOR_PASSWORD, PROP_MONITOR_NICK, \
    PROP_XMPP_SERVER, PROP_XMPP_PORT, PROP_XMPP_ROOM_NAME

# Pelix
from pelix.ipopo.decorators import ComponentFactory, Provides, \
    Property, Validate, Invalidate
from pelix.ipopo.constants import use_ipopo
import pelix.framework
import pelix.misc.xmpp as pelixmpp

# Room creation utility
from .utils import RoomCreator

# Standard library
import logging
import random
import sys
import threading

# ------------------------------------------------------------------------------

_logger = logging.getLogger(__name__)

FEATURE_MUC = 'http://jabber.org/protocol/muc'

# ------------------------------------------------------------------------------


class _MarksCallback(object):
    """
    Calls back a method when a list of elements have been marked
    """
    def __init__(self, elements, callback):
        """
        Sets up the count down.

        The callback method must accept two arguments: successful elements and
        erroneous ones. The elements must be hashable, as sets are used
        internally.

        :param elements: A list of elements to wait for
        :param callback: Method to call back when all elements have been
                         marked
        """
        self.__elements = set(elements)
        self.__callback = callback
        self.__called = False
        self.__successes = set()
        self.__errors = set()

    def __call(self):
        """
        Calls the callback method
        """
        try:
            if self.__callback is not None:
                self.__callback(self.__successes, self.__errors)
        except Exception as ex:
            _logger.exception("Error calling back count down handler: %s", ex)
        else:
            self.__called = True

    def __mark(self, element, mark_set):
        """
        Marks an element

        :param element: The element to mark
        :param mark_set: The set corresponding to the mark
        :return: True if the element was known
        """
        try:
            self.__elements.remove(element)
            mark_set.add(element)
        except KeyError:
            return False
        else:
            if not self.__elements:
                # No more elements to wait for
                self.__call()
            return True

    def is_done(self):
        """
        Checks if the call back has been called, i.e. if this object can be
        deleted
        """
        return self.__called

    def set(self, element):
        """
        Marks an element as successful

        :param element: An element
        :return: True if the element was known
        """
        return self.__mark(element, self.__successes)

    def set_error(self, element):
        """
        Marks an element as erroneous

        :param element: An element
        :return: True if the element was known
        """
        return self.__mark(element, self.__errors)


class MonitorBot(pelixmpp.BasicBot, pelixmpp.ServiceDiscoveryMixin):
    """
    A bot that creates chat rooms and invites other bots there
    """
    def __init__(self, jid, password, nick):
        """
        Sets up the robot
        """
        # Set up the object
        pelixmpp.BasicBot.__init__(self, jid, password)
        pelixmpp.ServiceDiscoveryMixin.__init__(self)

        # Register the Multi-User Chat plug-in
        self.register_plugin('xep_0045')
        # Register the Delayed Message plug-in
        self.register_plugin("xep_0203")

        # Nick name
        self._nick = nick

        # MUC service name
        self.__muc_service = None

        # Pending count downs and joined rooms
        self.__countdowns = set()
        self.__countdowns_lock = threading.Lock()
        self.__rooms = set()
        self.__main_room = None

        # Authorized  keys
        self.__keys = set()

        # Register to events
        self.add_event_handler("message", self.__on_message)

    def create_main_room(self, room, callback=None):
        """
        Creates the main room

        :param room: Main room name
        :param callback: Method to call back when the room has been created
        """
        self.__main_room = room
        self.create_rooms([room], callback)

    def create_rooms(self, rooms, callback=None):
        """
        Creates or joins the given rooms

        :param rooms: A list of rooms to join / create
        :param callback: Method to call back when all rooms have been created
        :raise ValueError: No Multi-User Chat service available
        """
        # Look for the MUC service if necessary
        if not self.__muc_service:
            try:
                self.__muc_service = next(self.iter_services(FEATURE_MUC))
            except StopIteration:
                raise ValueError("No Multi-User Chat service on server")

        if callback is not None:
            # Prepare a callback
            self.__countdowns.add(
                _MarksCallback((JID(local=room, domain=self.__muc_service)
                                for room in rooms), callback))

        # Prepare the room creator
        creator = RoomCreator(self, "Herald-XMPP-RoomCreator")

        # Prepare rooms configuration
        rooms_config = {
            # ... no max users limit
            'muc#roomconfig_maxusers': '0',
            # ... accepted members only
            'muc#roomconfig_membersonly': '1',
            # ... every participant can send invites
            'muc#roomconfig_allowinvites': '1',
            # ... room can disappear
            'muc#roomconfig_persistentroom': '0',
            # ... OpenFire: Forbid nick changes
            'x-muc#roomconfig_canchangenick': '0'}

        # Create rooms
        for room in rooms:
            creator.create_room(room, self.__muc_service, self._nick,
                                rooms_config, self.__room_created,
                                self.__room_error)

    def make_key(self):
        """
        Prepares a key to accept other robots in rooms

        :return: A 256 bits integer hexadecimal string
        """
        # Use the best randomizer available
        try:
            rnd = random.SystemRandom()
        except NotImplementedError:
            rnd = random

        # Create a key (256 bits)
        key = rnd.getrandbits(256)
        self.__keys.add(key)
        return '{0:X}'.format(key)

    def on_session_start(self, data):
        """
        XMPP session started.

        :param data: Session start stanza
        """
        pelixmpp.BasicBot.on_session_start(self, data)

        try:
            # Look for the Multi-User Chat service early
            self.__muc_service = next(self.iter_services(FEATURE_MUC))
        except StopIteration:
            _logger.error("No Multi-User Chat service on this server.")

    def __room_created(self, room, nick):
        """
        A room has been correctly created, and we're its owner

        :param room: Bare JID of the room
        :param nick: Our nick in the room
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

            # Keep track of the room
            self.__rooms.add(room)

    def __room_error(self, room, nick, condition, text):
        """
        Error creating a room

        :param room: Bare JID of the room
        :param nick: Our nick in the room
        :param condition: Category of error
        :param text: Description of the error
        """
        if condition == 'not-owner':
            _logger.warning("We are not the owner of %s", room)
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

    def __on_message(self, msg):
        """
        An Herald Message received (fire & forget)
        """
        if msg['delay']['stamp'] is not None:
            # Delayed message: ignore
            return

        if msg['type'] in ('chat', 'normal'):
            # Check message source
            from_jid = msg['from']
            if from_jid.bare == self.boundjid.bare:
                # Loopback message
                return

            try:
                content = msg['body'].split(':', 2)
                if content[0] != 'invite':
                    # Not a request for invitation
                    self.__reply(msg, "Unhandled command: {0}", content[0])
                    return

                try:
                    # Convert the key in an integer and look for it
                    if content[1] != "42":
                        key = int(content[1], 16)
                        self.__keys.remove(key)
                except KeyError:
                    self.__reply(msg, "Unauthorized key")
                except (TypeError, ValueError):
                    self.__reply(msg, "Invalid key")
                else:
                    try:
                        # Authorized client: invite it to requested rooms
                        rooms = set(content[2].split(','))
                    except IndexError:
                        # No room specified
                        rooms = set()

                    # Also invite it in the main room, if any
                    if self.__main_room:
                        rooms.add(self.__main_room)

                    rooms_jids = set(JID(local=room, domain=self.__muc_service)
                                     for room in rooms)

                    def rooms_ready(successes, failures):
                        """
                        Invites the requester in the rooms it requested, as
                        soon as they are ready

                        :param successes: JIDs of the usable rooms
                        :param failures: JIDs of the rooms which
                        failed
                        """
                        for room_jid in rooms_jids.difference(failures):
                            # Invite to valid rooms (old and new ones)
                            self['xep_0045'].invite(room_jid, from_jid.full,
                                                    "Client accepted")

                    # Create rooms if necessary...
                    to_create = rooms.difference(self.__rooms)
                    if to_create:
                        # We'll have to wait for the rooms before inviting
                        # the sender
                        self.create_rooms(to_create, rooms_ready)
                    else:
                        # All rooms already exist
                        rooms_ready(rooms_jids, [])

            except IndexError:
                self.__reply(msg, "Bad command format")

    def __reply(self, in_message, text, *args):
        """
        Replies to an XMPP message and logs the text in the reply.

        WARNING: Modifies the in_message bean by cleaning its original
        information

        :param in_message: Message received
        :param text: Text of the reply, with string.format syntax
        :param args: String format arguments
        """
        if args:
            text = text.format(*args)

        # Send the reply and log it
        in_message.reply(text).send()
        _logger.info(text)

# ------------------------------------------------------------------------------


@ComponentFactory(FACTORY_MONITOR)
@Provides(SERVICE_MONITOR_BOT)
@Property('_jid', PROP_MONITOR_JID, None)
@Property('_password', PROP_MONITOR_PASSWORD, None)
@Property('_nick', PROP_MONITOR_NICK, 'HeraldMonitorBot')
@Property('_main_room', PROP_XMPP_ROOM_NAME, 'herald')
@Property('_host', PROP_XMPP_SERVER, 'localhost')
@Property('_port', PROP_XMPP_PORT, 5222)
class MonitorBotWrapper(object):
    """
    An iPOPO component which wraps a MonitorBot instance
    """
    def __init__(self):
        """
        Sets up members
        """
        # Component properties
        self._jid = None
        self._password = None
        self._nick = 'HeraldMonitorBot'
        self._main_room = 'herald'
        self._host = 'localhost'
        self._port = 5222

        # The wrapped monitor bot
        self.__bot = None

    @Validate
    def _validate(self, context):
        """
        Component validated
        """
        self.__bot = MonitorBot(self._jid, self._password, self._nick)
        self.__bot.connect(self._host, self._port, use_tls=False)
        self.__bot.create_main_room(self._main_room)

    @Invalidate
    def _invalidate(self, context):
        """
        Component invalidated
        """
        self.__bot.disconnect()
        self.__bot = None

    def create_main_room(self, room, callback=None):
        """
        Creates a room and use it as the main one

        :param room: Main room name
        :param callback: Method to call back when the room has been created
        """
        return self.__bot.create_main_room(room, callback)

    def create_rooms(self, rooms, callback=None):
        """
        Creates or joins the given rooms

        :param rooms: A list of rooms to join / create
        :param callback: Method to call back when all rooms have been created
        :raise ValueError: No Multi-User Chat service available
        """
        return self.__bot.create_rooms(rooms, callback)

    def make_key(self):
        """
        Prepares a key to accept other robots in rooms

        :return: A 256 bits integer hexadecimal string
        """
        return self.__bot.make_key()


def main(args=None):
    """
    Standalone  monitor entry point
    """
    import argparse
    if not args:
        args = sys.argv[1:]

    # Define arguments
    parser = argparse.ArgumentParser(description="Herald XMPP Monitor Bot")

    # Server configuration
    group = parser.add_argument_group("XMPP server",
                                      "Access to the XMPP server")
    group.add_argument("-s", "--server", action="store", default="localhost",
                       dest="xmpp_server", help="Host of the XMPP server")
    group.add_argument("-p", "--port", action="store", type=int, default=5222,
                       dest="xmpp_port", help="Port of the XMPP server")

    # Bot account configuration
    group = parser.add_argument_group("Monitor bot account",
                                      "Definition of the bot's credentials")
    group.add_argument("--jid", action="store", default=None,
                       dest="jid", help="Full JID to use")
    group.add_argument("--password", action="store", default=None,
                       dest="password", help="Password associated to the JID")
    group.add_argument("--nick", action="store", default="HeraldMonitorBot",
                       dest="nick", help="Nickname to use in chat rooms")

    # Main Room configuration
    group = parser.add_argument_group("Herald configuration")
    group.add_argument("-r", "--room", action="store",
                       default="herald", dest="main_room",
                       help="Main chat room (XMPP MUC) to use for Herald")

    # Parse arguments
    args = parser.parse_args(args)

    # Prepare properties
    properties = {
        PROP_XMPP_SERVER: args.xmpp_server,
        PROP_XMPP_PORT: args.xmpp_port,
        PROP_MONITOR_JID: args.jid,
        PROP_MONITOR_PASSWORD: args.password,
        PROP_MONITOR_NICK: args.nick,
        PROP_XMPP_ROOM_NAME: args.main_room
    }

    # Start a Pelix framework
    framework = pelix.framework.create_framework(('pelix.ipopo.core',
                                                  'pelix.shell.core',
                                                  'pelix.shell.ipopo',
                                                  'pelix.shell.console'))
    framework.start()

    context = framework.get_bundle_context()
    with use_ipopo(context) as ipopo:
        # Register the component factory
        ipopo.register_factory(context, MonitorBotWrapper)

        # Create the component
        ipopo.instantiate(FACTORY_MONITOR, 'herald-xmpp-monitor', properties)

    try:
        framework.wait_for_stop()
    except (KeyboardInterrupt, EOFError):
        framework.stop()

if __name__ == '__main__':
    # Setup logger and start the monitor with default arguments
    logging.basicConfig(level=logging.INFO,
                        format='%(levelname)-8s %(message)s')
    main()
