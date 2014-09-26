#!/usr/bin/python
# -- Content-Encoding: UTF-8 --
"""
Utilities to debug sleekXMPP objects

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

# SleekXMPP
import sleekxmpp

# Standard library
import logging
import threading

try:
    # Python 2
    # pylint: disable=F0401
    from StringIO import StringIO
except ImportError:
    # Python 3
    from io import StringIO

# ------------------------------------------------------------------------------


def dump_element(element):
    """
    Dumps the content of the given ElementBase object to a string

    :param element: An ElementBase object
    :return: A full description of its content
    :raise TypeError: Invalid object
    """
    # Check type
    try:
        assert isinstance(element, sleekxmpp.ElementBase)
    except AssertionError:
        raise TypeError("Not an ElementBase: {0}".format(type(element)))

    # Prepare string
    output = StringIO()
    output.write("ElementBase : {0}\n".format(type(element)))
    output.write("- name......: {0}\n".format(element.name))
    output.write("- namespace.: {0}\n".format(element.namespace))

    output.write("- interfaces:\n")
    for itf in sorted(element.interfaces):
        output.write("\t- {0}: {1}\n".format(itf, element[itf]))

    if element.sub_interfaces:
        output.write("- sub-interfaces:\n")
        for itf in sorted(element.sub_interfaces):
            output.write("\t- {0}: {1}\n".format(itf, element[itf]))

    return output.getvalue()

# ------------------------------------------------------------------------------


class RoomData(object):
    """
    Stores data about a room to create
    """
    def __init__(self, room, nick, configuration, callback, errback):
        """
        Stores the description of the room.

        :param room: Bare JID of the room
        :param nick: Nick of the room creator
        :param configuration: Room configuration
        :param callback: Method to callback on success
        :param errback: Method to callback on error
        """
        self.room = room
        self.nick = nick
        self.configuration = configuration
        self.callback = callback
        self.errback = errback


class RoomCreator(object):
    """
    XMPP Room creation utility.

    The associated client must have registered plug-ins XEP-0004 and XEP-0045.
    """
    def __init__(self, client, logname=None):
        """
        Sets up the room creator

        The given client must have registered plug-ins XEP-0004 and XEP-0045.

        :param client: A ClientXMPP object
        :param logname: Logger name
        """
        # XMPP client
        self.__xmpp = client
        self.__muc = client['xep_0045']

        # Logger
        self.__logger = logging.getLogger(logname)

        # Room name -> RoomData
        self.__rooms = {}

        # Some thread safety...
        self.__lock = threading.Lock()

    def create_room(self, room, service, nick, config=None,
                    callback=None, errback=None):
        """
        Prepares the creation of a room.

        The callback is a method with two arguments:
          - room: Bare JID of the room
          - nick: Nick used to create the room

        The errback is a method with 4 arguments:
          - room: Bare JID of the room
          - nick: Nick used to create the room
          - condition: error category (XMPP specification or "not-owner")
          - text: description of the error


        :param room: Name of the room
        :param service: Name of the XMPP MUC service
        :param config: Configuration of the room
        :param callback: Method called back on success
        :param errback: Method called on error
        """
        self.__logger.info("Creating room: %s", room)

        with self.__lock:
            # Format the room JID
            room_jid = sleekxmpp.JID(local=room, domain=service).bare

            if not self.__rooms:
                # First room to create: register to events
                self.__xmpp.add_event_handler("presence", self.__on_presence)

            # Store information
            self.__rooms[room_jid] = RoomData(room_jid, nick, config,
                                              callback, errback)

        # Send the presence, i.e. request creation of the room
        self.__muc.joinMUC(room_jid, nick)

    def __safe_callback(self, room_data):
        """
        Safe use of the callback method, to avoid errors propagation

        :param room_data: A RoomData object
        """
        method = room_data.callback
        if method is not None:
            try:
                method(room_data.room, room_data.nick)
            except Exception as ex:
                self.__logger.exception("Error calling back room creator: %s",
                                        ex)

    def __safe_errback(self, room_data, err_condition, err_text):
        """
        Safe use of the callback method, to avoid errors propagation

        :param room_data: A RoomData object
        :param err_condition: Category of error
        :param err_text: Description of the error
        """
        method = room_data.errback
        if method is not None:
            try:
                method(room_data.room, room_data.nick, err_condition, err_text)
            except Exception as ex:
                self.__logger.exception("Error calling back room creator: %s",
                                        ex)

    def __on_presence(self, data):
        """
        Got a presence stanza
        """
        room_jid = data['from'].bare
        muc_presence = data['muc']
        room = muc_presence['room']
        nick = muc_presence['nick']

        with self.__lock:
            try:
                # Get room state machine
                room_data = self.__rooms[room]
                if room_data.nick != nick:
                    # Not about the room creator
                    return
            except KeyError:
                # Unknown room (or not a room)
                return
            else:
                # Clean up, as we got what we wanted
                del self.__rooms[room]

            if not self.__rooms:
                # No more rooms: no need to listen to presence anymore
                self.__xmpp.del_event_handler("presence", self.__on_presence)

        if data['type'] == 'error':
            # Got an error: update the state machine and clean up
            self.__safe_errback(room_data, data['error']['condition'],
                                data['error']['text'])

        elif muc_presence['affiliation'] != 'owner':
            # We are not the owner the room: consider it an error
            self.__safe_errback(room_data, 'not-owner',
                                'We are not the owner of the room')

        else:
            # Success: we own the room
            # Setup room configuration
            try:
                config = self.__muc.getRoomConfig(room_jid)
            except ValueError:
                # Can't differentiate IQ errors from a "no configuration"
                # result
                pass
            else:
                # Prepare our configuration
                custom_values = room_data.configuration or {}

                # Filter options that are not known from the server
                known_fields = config['fields']
                to_remove = [key for key in custom_values
                             if key not in known_fields]
                for key in to_remove:
                    del custom_values[key]

                # Send configuration (use a new form to avoid OpenFire to have
                # an internal error)
                form = self.__xmpp['xep_0004'].make_form("submit")
                form['values'] = custom_values
                self.__muc.setRoomConfig(room_jid, form)

                # Call back the creator
                self.__safe_callback(room_data)
