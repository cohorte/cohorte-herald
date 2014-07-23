#!/usr/bin/python
# -- Content-Encoding: UTF-8 --
"""
Herald XMPP bot
"""

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

        # Events callbacks
        self.__cb_message = None
        self.__cb_start = None
        self.__cb_end = None

        # Register to events
        self.add_event_handler("session_start", self.__on_session_start)
        self.add_event_handler("session_end", self.__on_session_end)
        self.add_event_handler("message", self.__on_message)


    def set_callbacks(self, start=None, end=None, message=None):
        """
        Sets the methods to call back on an event.
        Each callback takes the stanza as parameter.

        :param start: Called when session starts
        :param end: Called when session ends
        :param message: Called when a message is received
        """
        self.__cb_start = start
        self.__cb_end = end
        self.__cb_message = message


    def __call_back(self, method, data):
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
        groups = ",".join(str(group)\
                          for group in groups if group) if groups else ""
        msg = beans.Message("boostrap.invite",
                            ":".join(("invite", key, groups)))
        self.__send_message("chat", monitor_jid, msg)


    def herald_fire(self, target, message, body=None):
        """
        Sends a message to the given target

        :param target: A Jabber ID
        :param message: A Message bean
        """
        assert isinstance(message, beans.Message)
        self.__send_message("chat", target, message, body)


    def herald_fire_group(self, group, message, body=None):
        """
        Sends a message to a room

        :param room: The name of a Multi-User Chat room
        :param message: A message bean
        """
        assert isinstance(message, beans.Message)
        self.__send_message("groupchat", group, message, body)


    def __send_message(self, msgtype, target, message, body=None):
        """
        Prepares and sends a message over XMPP

        :param msgtype: Kind of message (chat or groupchat)
        :param target: Target JID or MUC room
        :param message: Herald message bean
        :param body: The serialized form of the message body. If not given,
                     the content is the string form of the message.content field
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

    def __on_session_start(self, data):
        """
        XMPP session started
        """
        # Callback method
        self.__call_back(self.__cb_start, data)

    def __on_message(self, msg):
        """
        XMPP message received
        """
        msgtype = msg['type']
        msgfrom = msg['from']
        if msgtype == 'groupchat':
            # MUC Room chat
            if self.boundjid.user == msgfrom.resource:
                # Loopback message
                return
        elif msgtype not in ('normal', 'chat'):
            # Ignore non-chat messages
            return

        # Callback
        self.__call_back(self.__cb_message, msg)

    def __on_session_end(self, data):
        """
        XMPP session ended
        """
        self.__call_back(self.__cb_end, data)

# ------------------------------------------------------------------------------

def main(host):
    client = HeraldBot()
    client.connect(host, use_tls=False)

    # Use last created client
    client.herald_join("bot@phenomtwo3000", "42")

    try:
        try:
            raw_input("Press enter to stop...")
        except NameError:
            input("Press enter to stop...")
    except (KeyboardInterrupt, EOFError):
        _logger.debug("Got interruption")

    client.disconnect()

    _logger.info("Bye!")

if __name__ == '__main__':
    import sys
    logging.basicConfig(level=logging.INFO,
                        format='%(levelname)-8s %(message)s')
    logging.debug("Running on Python: %s", sys.version)
    main("127.0.0.1")
