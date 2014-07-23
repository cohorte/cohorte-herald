#!/usr/bin/python
# -- Content-Encoding: UTF-8 --
"""
First bot for XMPP
"""

# XMPP
import sleekxmpp

# Standard library
import itertools
import json
import logging
import os
import string

class BasicBot(sleekxmpp.ClientXMPP):
    """
    Basic bot
    """
    def __init__(self, jid, password):
        """
        Sets up the bot

        :param jid: Jabber ID
        :param password: Jabber account password
        """
        # Setup the XMPP client
        sleekxmpp.ClientXMPP.__init__(self, jid, password, lang='fr')

        # Just to know the one we chose
        self.nick = 'RobotNick'

        # Register to events
        self.add_event_handler("session_start", self.__session_start)
        self.add_event_handler("message", self.__message)
        self.add_event_handler("groupchat_message", self.__muc_message)


        # Message handling callback
        self.handle_message = None


    def __session_start(self, event):
        """
        Session started
        """
        self.send_presence()
        self.get_roster()
        self.send_message(mto="admin@phenomtwo3000",
                          mbody="Hello, World !",
                          mtype="chat")


    def __message(self, msg):
        """
        Got a message
        """
        if msg['type'] not in ('chat', 'normal'):
            logging.debug("Ignored message of type '%s' from %s",
                          msg['type'], msg['from'])
            return

        message = msg['body']
        pure_message = message.strip().lower()
        if pure_message.startswith('!bot'):
            command = pure_message.split(' ', 2)[1]
            if command == 'send':
                cycle = itertools.cycle(string.digits)
                content = ''.join(next(cycle) for _ in range(10000))
                msg.reply(content).send()

            elif command == 'echo':
                msg.reply(pure_message.split(' ', 2)[2]).send()

            elif command == 'json':
                environ = {key: str(value) for key, value in os.environ.items()}
                msg.reply(json.dumps(environ, indent=2)).send()

            elif command == 'join':
                # Join the MUC room
                self.plugin['xep_0045'].joinMUC(
                    "central@conference.phenomtwo3000",
                    self.nick, wait=True)

            else:
                msg.reply("Unknown command: {0}".format(command)).send()

        else:
            self.__notify(msg['from'], message)


    def __muc_message(self, msg):
        """
        Got a message from a room
        """
        if msg['mucnick'] != self.nick and self.nick in msg['body']:
            self.send_message(mto=msg['from'].bare,
                              mbody="I heard that, {0}.".format(msg['mucnick']),
                              mtype='groupchat')


    def __notify(self, sender, content):
        """
        Calls back listener when a message is received
        """
        if self.handle_message is not None:
            try:
                self.handle_message(sender, content)
            except Exception as ex:
                logging.exception("Error calling message listener: %s", ex)


def on_message(sender, message):
    logging.info("From %s >> %s", sender, message)

def main():
    xmpp = BasicBot("bot@phenomtwo3000/python", "bot")
    xmpp.handle_message = on_message

    # Allow unencrypted plain authentification
    xmpp['feature_mechanisms'].unencrypted_plain = True

    # Activate MUC
    xmpp.register_plugin('xep_0045')

    # Connect to the server
    xmpp.connect(("localhost", 5222), use_tls=False, use_ssl=False)
    xmpp.process(block=True)

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG,
                        format='%(levelname)-8s %(message)s')
    main()
