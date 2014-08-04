#!/usr/bin/python
# -- Content-Encoding: UTF-8 --
"""
IRC client bot for herald
"""

import irc.client

import pelix.threadpool

import fnmatch
import itertools
import logging
import json
import string
import threading
import uuid

# ------------------------------------------------------------------------------

def chunks(data, size):
    """
    Generator that splits the given data into chunks
    """
    for i in range(0, len(data), size):
        yield data[i:i + size]

# ------------------------------------------------------------------------------

class Bot(object):
    """
    A basic bot (parent class)
    """
    def __init__(self, nick, realname, username=None):
        """
        Sets up the bot
        """
        # User information
        self._nickname = nick
        self._realname = realname
        self._username = username or nick

        # IRC Client
        self._irc = irc.client.IRC()
        self._connection = None

        # Connection thread
        self.__thread = None
        self.__stopped = threading.Event()


    def connect(self, host, port=6667, password=None):
        """
        Connects to a server
        """
        # Prepare the callbacks
        self._irc.add_global_handler('all_events', self.__handler)

        # Prepare the connection
        self._connection = self._irc.server().connect(
            host, port, self._nickname, password,
            self._username, self._realname)

        # Start connection thread
        self.__stopped.clear()
        self.__thread = threading.Thread(target=self.__loop,
                                         name="IRC-Bot-Loop")
        self.__thread.daemon = True
        self.__thread.start()


    def get_nick(self, full_name):
        """
        Returns the nick contained in the given full user name
        """
        return irc.client.NickMask(full_name).nick


    def __handler(self, connection, event):
        """
        Handles an IRC event
        """
        try:
            # Find local handler
            method = getattr(self, "on_{0}".format(event.type))
        except AttributeError:
            pass
        else:
            try:
                # Call it
                return method(connection, event)
            except Exception as ex:
                logging.exception("Error calling handler: %s", ex)


    def close(self):
        """
        Disconnects from the server
        """
        # Disconnect with a fancy message, then close connection
        if self._connection is not None:
            self._connection.disconnect("Bot is quitting")
            self._connection.close()
            self._connection = None

        # Stop the client loop
        self.__stopped.set()

        if self.__thread is not None:
            try:
                self.__thread.join(5)
            except RuntimeError:
                pass
            self.__thread = None


    def wait(self, timeout=None):
        """
        Waits for the client to stop its loop
        """
        self.__stopped.wait(timeout)
        return self.__stopped.is_set()


    def __loop(self):
        """
        Client connection loop
        """
        while not self.__stopped.is_set():
            # Process data, loop every second (to get out faster)
            self._irc.process_once(1)

# ------------------------------------------------------------------------------

class CommandBot(Bot):
    """
    A bot that supports some commands
    """
    def __init__(self, nick, realname, username=None):
        """
        Sets up members
        """
        super(CommandBot, self).__init__(nick, realname, username)
        self.__pool = pelix.threadpool.ThreadPool(1)


    def on_welcome(self, connection, event):
        """
        Server welcome: we're connected
        """
        # Start the pool
        self.__pool.start()

        logging.info("! Connected to server '%s': %s",
                     event.source, event.arguments[0])
        connection.join("#cohorte")

    def on_disconnect(self, connection, event):
        """
        Disconnected from server
        """
        # Stop the pool
        self.__pool.stop()


    def on_pubmsg(self, connection, event):
        """
        Got a message from a channel
        """
        sender = self.get_nick(event.source)
        channel = event.target
        message = event.arguments[0]

        self.handle_message(connection, sender, channel, message)


    def on_privmsg(self, connection, event):
        """
        Got a message from a user
        """
        sender = self.get_nick(event.source)
        message = event.arguments[0]
        
        if sender == 'NickServ':
            logging.info("Got message from NickServ: %s", message)
            if "password" in message.lower():
                connection.privmsg("NickServ", "pass")
            else:
                connection.join('#cohorte')
            
            return

        self.handle_message(connection, sender, sender, message)


    def handle_message(self, connection, sender, target, message):
        """
        Handles a received message
        """
        parts = message.strip().split(' ', 2)
        if parts and parts[0].lower() == '!bot':
            try:
                command = parts[1].lower()
            except IndexError:
                self.safe_send(connection, target, "No command given")
                return

            try:
                payload = parts[2]
            except IndexError:
                payload = ""

            self.__pool.enqueue(self._handle_command,
                                connection, sender, target, command, payload)


    def on_invite(self, connection, event):
        """
        Got an invitation to a channel
        """
        sender = self.get_nick(event.source)
        invited = self.get_nick(event.target)
        channel = event.arguments[0]

        if invited == self._nickname:
            logging.info("! I am invited to %s by %s", channel, sender)
            connection.join(channel)

        else:
            logging.info(">> %s invited %s to %s", sender, invited, channel)


    def _handle_command(self, connection, sender, target, command, payload):
        """
        Handles a command, if any
        """
        try:
            # Find the handler
            handler = getattr(self, "cmd_{0}".format(command))
        except AttributeError:
            self.safe_send(connection, target, "Unknown command: %s",
                            command)
        else:
            try:
                logging.info("! Handling command: %s", command)
                handler(connection, sender, target, payload)
            except Exception as ex:
                logging.exception("Error calling command handler: %s", ex)


    def safe_send(self, connection, target, message, *args, **kwargs):
        """
        Safely sends a message to the given target
        """
        # Compute maximum length of payload
        prefix = "PRIVMSG {0} :".format(target)
        max_len = 510 - len(prefix)

        for chunk in chunks(message.format(*args, **kwargs), max_len):
            connection.send_raw("{0}{1}".format(prefix, chunk))

# ------------------------------------------------------------------------------

class HeraldBot(CommandBot):
    def __init__(self, nick, realname, herald):
        """
        Sets up members
        """
        super(HeraldBot, self).__init__(nick, realname, nick)
        self.__herald = herald
        self.__event = threading.Event()


    def wait_stop(self):
        self.__event.wait()

    def cmd_stop(self, *args):
        self.__event.set()

    def parse_payload(self, payload):
        """
        Parses a bot payload
        """
        parts = payload.split(' ', 2)
        return parts[0:3]


    def cmd_send(self, connection, sender, target, payload):
        """
        Sends a message
        """
        msg_target, topic, content = self.parse_payload(payload)
        results = self.__herald.send(msg_target, topic, content)
        self.safe_send(connection, target, "GOT RESULT: {0}".format(results))


    def cmd_fire(self, connection, sender, target, payload):
        """
        Sends a message
        """
        msg_target, topic, content = self.parse_payload(payload)

        def callback(sender, payload):
            logging.info("FIRE ACK from %s", sender)

        self.__herald.fire(msg_target, topic, content, callback)


    def cmd_notice(self, connection, sender, target, payload):
        """
        Sends a message
        """
        msg_target, topic, content = self.parse_payload(payload)

        def callback(sender, payload):
            logging.info("NOTICE ACK from %s: %s", sender, payload)

        self.__herald.notice(msg_target, topic, content, callback)


    def cmd_post(self, connection, sender, target, payload):
        """
        Sends a message
        """
        msg_target, topic, content = self.parse_payload(payload)

        def callback(sender, payload):
            logging.info("POST RES from %s: %s", sender, payload)

        self.__herald.post(msg_target, topic, content, callback)


    def cmd_big(self, connection, sender, target, payload):
        def callback(sender, payload):
            logging.info("POST RES from %s: %s", sender, payload)

        cycle = itertools.cycle(string.digits)
        content = ''.join(next(cycle) for _ in range(int(payload or 600)))

        self.__herald.post(target, "/titi/toto", content, callback)


# ------------------------------------------------------------------------------

class MessageBot(Bot):
    """
    Bot for messaging purpose
    """
    def __init__(self, *args, **kwargs):
        """
        Sets up members
        """
        # Prepare IRC client
        super(MessageBot, self).__init__(*args, **kwargs)

        # Message parts queue
        self._queue = {}

        # Task queue
        self._pool = pelix.threadpool.ThreadPool(1)

        # Log a bit
        logging.info("Bot created... %s", self._nickname)

        # Message handling callback
        self.handle_message = None


    def start(self):
        """
        Starts the thread pool
        """
        self._pool.start()


    def stop(self):
        """
        Stops the thread pool
        """
        self._pool.stop()


    def on_welcome(self, connection, event):
        """
        Server welcome: we're connected
        """
        logging.info("! Connected to server '%s': %s",
                     event.source, event.arguments[0])
        connection.join("#cohorte")


    def on_invite(self, connection, event):
        """
        Got an invitation to a channel
        """
        sender = self.get_nick(event.source)
        invited = self.get_nick(event.target)
        channel = event.arguments[0]

        if invited == self._nickname:
            logging.info("! I am invited to %s by %s", channel, sender)
            connection.join(channel)


    def on_privmsg(self, connection, event):
        """
        Got a message from a channel
        """
        sender = self.get_nick(event.source)
        message = event.arguments[0]
        
        if sender == 'NickServ':
            logging.info("Got message from NickServ: %s", message)
            if "password" in message.lower():
                connection.privmsg("NickServ", "pass")
            else:
                connection.join('#cohorte')
            
            return
        
        self._pool.enqueue(self.__on_message, connection, sender, message)

    # Same behavior for private and channel messages
    on_pubmsg = on_privmsg


    def __on_message(self, connection, sender, message):
        """
        Got a message from a channel
        """
        if message.strip() == '!bot send':
            cycle = itertools.cycle(string.digits)
            content = ''.join(next(cycle) for _ in range(100))
            self.send_message(sender, content)

        else:
            parts = message.split(':', 2)
            if not parts or parts[0] != 'HRLD':
                return

            if parts[1] == 'BEGIN':
                # Beginning of multi-line message
                self._queue[parts[2]] = []

            elif parts[1] == 'END':
                # End of multi-line message
                content = ''.join(self._queue.pop(parts[2]))
                self.__notify(sender, content)

            elif parts[1] == 'MSG':
                # Single-line message
                content = parts[2]
                self.__notify(sender, content)

            else:
                # Multi-line message continuation
                uid = parts[1]
                self._queue[uid].append(parts[2])


    def __notify(self, sender, content):
        """
        Calls back listener when a message is received
        """
        if self.handle_message is not None:
            try:
                self.handle_message(sender, content)
            except Exception as ex:
                logging.exception("Error calling message listener: %s", ex)


    def _make_line(self, uid, command=None):
        """
        Prepares an IRC line in Herald's format
        """
        if command:
            return ":".join(("HRLD", command, uid))
        else:
            return ":".join(("HRLD", uid))


    def send_message(self, target, content, uid=None):
        """
        Sends a message through IRC
        """
        # Compute maximum length of payload
        prefix = "PRIVMSG {0} :".format(target)
        single_prefix = self._make_line("MSG:")
        single_prefix_len = len(single_prefix)
        max_len = 510 - len(prefix)

        content_len = len(content)
        if (content_len + single_prefix_len) < max_len:
            # One pass message
            self._connection.send_raw("{0}{1}{2}" \
                                       .format(prefix, single_prefix, content))

        else:
            # Multiple-passes message
            uid = uid or str(uuid.uuid4()).replace('-', '').upper()
            prefix = "{0}{1}:".format(prefix, self._make_line(uid))
            max_len = 510 - len(prefix)

            self._connection.privmsg(target, self._make_line(uid, "BEGIN"))

            for chunk in chunks(content, max_len):
                self._connection.send_raw(''.join((prefix, chunk)))

            self._connection.privmsg(target, self._make_line(uid, "END"))

# ------------------------------------------------------------------------------

class Herald(object):
    """
    The Herald (kind of) core service
    """
    def __init__(self, bot):
        """
        Sets up members
        """
        self.__client = bot
        self.__client.handle_message = self.on_message
        self.__callbacks = {}
        self.__pool = pelix.threadpool.ThreadPool(5)
        self.__listeners = {}

    def register(self, pattern, listener):
        self.__listeners.setdefault(pattern, []).append(listener)


    def start(self):
        self.__pool.start()

    def stop(self):
        self.__pool.stop()


    def __make_message(self, topic, content):
        """
        Prepares the message content
        """
        return {"uid": str(uuid.uuid4()).replace('-', '').upper(),
                "topic": topic,
                "content": content}


    def fire(self, target, topic, content, callback=None):
        """
        Fires a message
        """
        message = self.__make_message(topic, content)
        if callback is not None:
            self.__callbacks[message['uid']] = ('fire', callback)

        self.__client.send_message(target, json.dumps(message), message['uid'])


    def notice(self, target, topic, content, callback=None):
        """
        Fires a message
        """
        message = self.__make_message(topic, content)
        if callback is not None:
            self.__callbacks[message['uid']] = ('notice', callback)

        self.__client.send_message(target, json.dumps(message), message['uid'])


    def send(self, target, topic, content):
        """
        Fires a message
        """
        event = threading.Event()
        results = []

        def got_message(sender, content):
            results.append(content)
            event.set()

        self.post(target, topic, content, got_message)
        event.wait()

        return results


    def post(self, target, topic, content, callback=None):
        """
        Fires a message
        """
        message = self.__make_message(topic, content)
        if callback is not None:
            self.__callbacks[message['uid']] = ('send', callback)

        self.__client.send_message(target, json.dumps(message), message['uid'])


    def _notify_listeners(self, sender, message):
        """
        Notifies listeners of a new message
        """
        uid = message['uid']
        msg_topic = message['topic']


        self._ack(sender, uid, 'fire')

        all_listeners = set()
        for lst_topic, listeners in self.__listeners.items():
            if fnmatch.fnmatch(msg_topic, lst_topic):
                all_listeners.update(listeners)

        self._ack(sender, uid, 'notice', 'ok' if all_listeners else 'none')

        try:
            results = []
            for listener in all_listeners:
                result = listener.handle_message(sender,
                                                 message['topic'],
                                                 message['content'])
                if result:
                    results.append(result)

            self._ack(sender, uid, 'send', json.dumps(results))
        except:
            self._ack(sender, uid, 'send', "Error")


    def _ack(self, sender, uid, level, payload=None):
        """
        Replies to a message
        """
        content = {'reply-to': uid,
                   'reply-level': level,
                   'payload': payload}
        self.__client.send_message(sender, json.dumps(content))


    def on_message(self, sender, content):
        """
        Got a message from the client
        """
        try:
            message = json.loads(content)

        except (ValueError, TypeError) as ex:
            logging.error("Not a valid JSON string: %s", ex)
            return

        try:
            # Check the replied message
            reply_uid = message['reply-to']
            reply_level = message['reply-level']

        except KeyError:
            # Got a new message
            logging.info("Got message %s from %s", message['content'], sender)

            # Notify listeners
            self.__pool.enqueue(self._notify_listeners, sender, message)

        else:
            # Got a reply
            try:
                level, callback = self.__callbacks[reply_uid]

            except KeyError:
                # Nobody to callback...
                pass

            else:
                if level == reply_level:
                    # Match
                    try:
                        callback(sender, message['payload'])
                    except Exception as ex:
                        logging.exception("Error notifying sender: %s", ex)


class LogHandler(object):
    def handle_message(self, sender, topic, content):
        logging.info("Got message %s from %s:\n> %s", topic, sender, content)
        return "LogHandler got {0} from {1}".format(topic, sender)


def main():
    """
    Entry point
    """
    client_1 = MessageBot("verne", "Jules Verne")
    client_1.start()
    client_1.connect("127.0.0.1")

    client_2 = MessageBot("adams", "Douglas Adams")
    client_2.start()
    client_2.connect("127.0.0.1")

    herald_1 = Herald(client_1)
    herald_1.start()

    herald_2 = Herald(client_2)
    herald_2.start()

    handler = LogHandler()
    herald_1.register('/toto/*', handler)
    herald_2.register('/toto/*', handler)

    cmd = HeraldBot("bot", "Robotnik", herald_1)
    cmd.connect("127.0.0.1")

    cmd.wait_stop()

    for closable in (client_1, client_2, herald_1, herald_2):
        closable.close()

    logging.info("Bye !")

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    main()
