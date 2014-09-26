#!/usr/bin/python
# -- Content-Encoding: UTF-8 --
"""
Herald XMPP bot

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

# Pelix XMPP utility classes
import pelix.misc.xmpp as pelixmpp

# Herald
import herald.beans as beans

# Standard library
import logging

# ------------------------------------------------------------------------------

_logger = logging.getLogger(__name__)

# ------------------------------------------------------------------------------


class HeraldBot(pelixmpp.BasicBot, pelixmpp.InviteMixIn):
    """
    XMPP Messenger for Herald.
    """
    def __init__(self, jid=None, password=None):
        """
        Sets up the robot
        """
        # Set up the object
        pelixmpp.BasicBot.__init__(self, jid, password)
        pelixmpp.InviteMixIn.__init__(self, None)

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

    def __callback(self, method, data):
        """
        Safely calls back a method

        :param method: Method to call, or None
        :param data: Associated stanza
        """
        if method is not None:
            try:
                method(data)
            except Exception as ex:
                _logger.exception("Error calling method: %s", ex)

    def herald_join(self, nick, monitor_jid, key, groups=None):
        """
        Requests to join Herald's XMPP groups

        :param nick: Multi-User Chat nick
        :param monitor_jid: JID of a monitor bot
        :param key: Key to send to the monitor bot
        :param groups: Groups to join
        """
        # Update nick for the Invite MixIn
        self._nick = nick

        # Compute & send message
        groups_str = ",".join(str(group)
                              for group in groups if group) if groups else ""
        msg = beans.Message("boostrap.invite",
                            ":".join(("invite", str(key or ''), groups_str)))
        self.__send_message("chat", monitor_jid, msg)

    def __send_message(self, msgtype, target, message, body=None):
        """
        Prepares and sends a message over XMPP

        :param msgtype: Kind of message (chat or groupchat)
        :param target: Target JID or MUC room
        :param message: Herald message bean
        :param body: The serialized form of the message body. If not given,
                     the content is the string form of the message.content
                     field
        """
        if body is None:
            # String form of the message as content
            body = str(message.content)

        # Prepare an XMPP message, based on the Herald message
        xmpp_msg = self.make_message(mto=target, mbody=body,
                                     msubject=message.subject, mtype=msgtype)
        xmpp_msg['thread'] = message.uid

        # Send it
        xmpp_msg.send()

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
        self.__callback(self.__cb_message, msg)
