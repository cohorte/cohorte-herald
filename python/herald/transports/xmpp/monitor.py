#!/usr/bi    n/python
# -- Content-Encoding: UTF-8 --
"""
Herald XMPP control robot implementation
"""

# XMPP
from sleekxmpp import JID

# Pelix XMPP utility classes
import pelix.misc.xmpp as pelixmpp

# Room creation utility
from .utils import RoomCreator

# Standard library
import logging
import random
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

                        :param rooms_jids: JIDs of the usable rooms
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
        :param *args: String format arguments
        """
        if args:
            text = text.format(*args)

        # Send the reply and log it
        in_message.reply(text).send()
        _logger.info(text)

# ------------------------------------------------------------------------------


def main(host):
    """
    Standalone  monitor entry point
    """
    xmpp = MonitorBot("bot@phenomtwo3000/messenger", "bot", "Bender")
    xmpp.connect(host, use_tls=False)

    xmpp.create_main_room('cohorte')
    xmpp.create_rooms(('herald', 'cohorte', 'monitors', 'node'))

    for _ in range(5):
        _logger.warning("NEW KEY: %s", xmpp.make_key())

    try:
        try:
            # pylint: disable=E0602
            raw_input("Press enter to stop...")
        except NameError:
            input("Press enter to stop...")
    except (KeyboardInterrupt, EOFError):
        _logger.debug("Got interruption")

    xmpp.disconnect()
    _logger.info("Bye!")

if __name__ == '__main__':
    import sys
    logging.basicConfig(level=logging.INFO,
                        format='%(levelname)-8s %(message)s')
    logging.debug("Running on Python: %s", sys.version)
    main("127.0.0.1")
