#!/usr/bin/python
# -- Content-Encoding: UTF-8 --
"""
XMPP implementation of Herald
"""

# XMPP
import sleekxmpp

# Herald
import herald.beans as beans

# Standard library
import logging
import ssl

# ------------------------------------------------------------------------------

_logger = logging.getLogger(__name__)

# ------------------------------------------------------------------------------

class XMPPMessenger(object):
    """
    XMPP Messenger for Herald. The setup() method must be called before any
    other.
    """
    def __init__(self):
        """
        Sets up members
        """
        # XMPP client
        self.__xmpp = None


    def setup(self, jabberid, password):
        """
        Instantiates and configures the XMPP client

        :param jabberid: Jabber ID
        :param password: Password associated to the Jabber ID
        """
        # Instantiate the client
        self.__xmpp = sleekxmpp.ClientXMPP(jabberid, password)

        # FIXME: Avoid allowing unencrypted plain authentification
        _logger.info("Changing SSL version")
        self.__xmpp.ssl_version = ssl.PROTOCOL_SSLv3
        self.__xmpp['feature_mechanisms'].unencrypted_plain = True

        # Activate MUC & Ping
        self.__xmpp.register_plugin('xep_0045')
        self.__xmpp.register_plugin('xep_0199')

        # Register to events
        # ... connection events
        self.__xmpp.add_event_handler("socket_error", self.__on_error)
        self.__xmpp.add_event_handler("disconnected", self.__on_disconnect)

        # ... session events
        self.__xmpp.add_event_handler("session_start", self.__on_session_start)
        self.__xmpp.add_event_handler("session_end", self.__on_session_end)
        self.__xmpp.add_event_handler("message", self.__on_message)


    def connect(self, host, port=5222, use_tls=False, use_ssl=False):
        """
        Connects the client to a server.

        :param host: XMPP server host name
        :param port: XMPP server port
        :param use_tls: If True, try to cipher connection with STARTTLS
        :param use_ssl: Connect to an SSL port
        :raise ValueError: setup() has not been called
        """
        if self.__xmpp is None:
            raise ValueError("setup() has not been called yet.")

        # FIXME: see why TLS and SSL don't work (Python ? OpenFire ?)
        if self.__xmpp.connect((host, port), True, use_tls, use_ssl):
            self.__xmpp.process(threaded=True)


    def disconnect(self):
        """
        Disconnects from the server
        """
        if self.__xmpp is None:
            # Ignore
            return

        # Disconnect from the server. Wait for the send queue to be emptied
        self.__xmpp.disconnect(reconnect=False, wait=True)
        self.__xmpp = None


    def send(self, target, message):
        """
        Sends a message to the given target

        :param target: A Jabber ID
        :param message: A Message bean
        """
        assert isinstance(message, beans.Message)
        self.__xmpp.send_message(mto=target, mtype="chat",
                                 msubject=message.topic,
                                 mbody=str(message.payload))


    def send_group(self, group, message):
        """
        Sends a message to a room
        """
        assert isinstance(message, beans.Message)
        self.__xmpp.send_message(mto=group, mtype="groupchat",
                                 msubject=message.topic,
                                 mbody=str(message.payload))


    def __on_disconnect(self, _):
        """
        Disconnected from server
        """
        logging.info("Disconnected from server")


    def __on_error(self, error):
        """
        A socket error occurred
        """
        _logger.exception("A socket error occurred: %s", error)


    def __on_session_start(self, event):
        """
        XMPP session started
        """
        # First thing to do: send a presence stanza
        self.__xmpp.send_presence()

        # Get our roster
        self.__xmpp.get_roster()

        self.send("admin@phenomtwo3000",
                  beans.Message("Greetings", "Hello, Sir"))


    def __on_session_end(self, event):
        """
        XMPP session is ending (still active during this callback)
        """
        self.send("admin@phenomtwo3000",
                  beans.Message("Greetings", "Have a nice day, Sir"))
        _logger.info("XMPP session ended.")


    def __on_message(self, msg):
        """
        XMPP message received
        """
        if msg['type'] not in ('chat', 'groupchat'):
            # Ignore non-chat messages
            return

        # Extract information
        sender_jid = msg['from'].bare
        sender_name = msg['from'].user
        subject = msg['subject']
        payload = msg['body']

        # TODO: handle it
        _logger.info("Got message from=%s, topic=%s, payload=%s",
                     sender_jid, subject, payload)

        msg.reply('Got it, {0}'.format(sender_name)).send()

# ------------------------------------------------------------------------------

def main(host):
    xmpp = XMPPMessenger()
    xmpp.setup("bot@phenomtwo3000/messenger", "bot")
    xmpp.connect(host)

    try:
        raw_input("Press enter to stop...")
    except NameError:
        input("Press enter to stop...")

    xmpp.disconnect()
    _logger.info("Bye!")

if __name__ == '__main__':
    import sys
    logging.basicConfig(level=logging.DEBUG,
                        format='%(levelname)-8s %(message)s')
    logging.debug("Running on Python: %s", sys.version)
    main("127.0.0.1")
