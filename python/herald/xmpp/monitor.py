#!/usr/bi    n/python
# -- Content-Encoding: UTF-8 --
"""
Herald XMPP control robot implementation
"""

# XMPP
import sleekxmpp

# Pelix XMPP utility classes
import pelix.misc.xmpp as pelixmpp

# Room creation utility
from .utils import RoomCreator

# Standard library
import logging
import random

# ------------------------------------------------------------------------------

_logger = logging.getLogger(__name__)

FEATURE_MUC = 'http://jabber.org/protocol/muc'

# ------------------------------------------------------------------------------


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

        # Nick name
        self._nick = nick

        # MUC service name
        self.__muc_service = None

        # Required and joined rooms
        self.__req_rooms = set()
        self.__rooms = set()
        self.__main_room = None

        # Authorized  keys
        self.__keys = set()

        # Register to events
        self.add_event_handler("message", self.__on_message)

    def create_main_room(self, room):
        """
        Creates the main room

        :param room: Main room name
        """
        self.__main_room = room
        self.create_rooms([room])

    def create_rooms(self, rooms):
        """
        Creates or joins the given rooms

        :param rooms: A list of rooms to join / create
        :raise ValueError: No Multi-User Chat service available
        """
        # Look for the MUC service if necessary
        if not self.__muc_service:
            try:
                self.__muc_service = next(self.iter_services(FEATURE_MUC))
            except StopIteration:
                raise ValueError("No Multi-User Chat service on server")

        # Store the list of rooms to create
        self.__req_rooms.update(rooms)

        # Prepare the room creator
        creator = RoomCreator(self)

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
        try:
            self.__req_rooms.remove(sleekxmpp.JID(room).user)
        except KeyError:
            _logger.debug("Unknown room: %s", room)
        else:
            _logger.info("Room created: %s", room)
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
            _logger.error("Error creating room: %s (%s)", text, condition)

    def __on_message(self, msg):
        """
        An Herald Message received (fire & forget)
        """
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
                        rooms.intersection_update(self.__rooms)
                    except IndexError:
                        # No room specified
                        rooms = set()

                    # Also invite it in the main room, if any
                    if self.__main_room:
                        rooms.add(self.__main_room)

                    for room in rooms:
                        room = sleekxmpp.JID(local=room,
                                             domain=self.__muc_service).bare
                        self.__reply(msg, "Invite {0} to {1}",
                                     from_jid.full, room)

                        # ... invite user in all created rooms
                        self['xep_0045'].invite(room, from_jid.full,
                                                "Client accepted")
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
