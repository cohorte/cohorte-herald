#!/usr/bin/python
# -- Content-Encoding: UTF-8 --
"""
Herald XMPP bot

:author: Thomas Calmant
:copyright: Copyright 2014, isandlaTech
:license: Apache License 2.0
:version: 1.0.1
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

# Bundle version
import herald.version
__version__=herald.version.__version__

# ------------------------------------------------------------------------------

# Pelix XMPP utility classes
import pelix.misc.xmpp as pelixmpp

# Standard library
import logging

# ------------------------------------------------------------------------------

_logger = logging.getLogger(__name__)

# ------------------------------------------------------------------------------


class HeraldBot(pelixmpp.BasicBot, pelixmpp.ServiceDiscoveryMixin):
    """
    XMPP Messenger for Herald.
    """
    def __init__(self, jid=None, password=None, nick=None):
        """
        Sets up the robot

        :param jid: Bot JID (None for anonymous connection)
        :param password: Authentication password
        :param nick: Nick name used in MUC rooms
        """
        # Set up the object
        pelixmpp.BasicBot.__init__(self, jid, password)
        pelixmpp.ServiceDiscoveryMixin.__init__(self)
        self._nick = nick

        # Message callback
        self.__cb_message = None

        # Register to events
        self.add_event_handler("message", self.__on_message)

    def set_message_callback(self, callback):
        """
        Sets the method to call when a message is received.

        The method takes the message stanza as parameter.

        :param callback: Method to call when a message is received
        """
        self.__cb_message = callback

    def __callback(self, data):
        """
        Safely calls back a method

        :param data: Associated stanza
        """
        method = self.__cb_message
        if method is not None:
            try:
                method(data)
            except Exception as ex:
                _logger.exception("Error calling method: %s", ex)

    def __on_message(self, msg):
        """
        XMPP message received
        """
        msgtype = msg['type']
        msgfrom = msg['from']
        if msgtype == 'groupchat':
            # MUC Room chat
            if self._nick == msgfrom.resource:
                # Loopback message
                return
        elif msgtype not in ('normal', 'chat'):
            # Ignore non-chat messages
            return

        # Callback
        self.__callback(msg)
