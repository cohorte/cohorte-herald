#!/usr/bin/python
# -- Content-Encoding: UTF-8 --
"""
Pelix Shell commands for Herald
"""

# Herald
from herald.exceptions import NoTransport, HeraldTimeout, NoListener
import herald
import herald.beans as beans

# Pelix
from pelix.ipopo.decorators import ComponentFactory, Requires, Provides, \
    Instantiate
import pelix.shell

# ------------------------------------------------------------------------------


@ComponentFactory("herald-shell-factory")
@Requires("_herald", herald.SERVICE_HERALD)
@Requires("_directory", herald.SERVICE_DIRECTORY)
@Requires("_utils", pelix.shell.SERVICE_SHELL_UTILS)
@Provides(pelix.shell.SERVICE_SHELL_COMMAND)
@Instantiate("herald-shell")
class HeraldCommands(object):
    """
    iPOPO shell commands
    """
    def __init__(self):
        """
        Sets up the object
        """
        self._herald = None
        self._directory = None
        self._utils = None

    def get_namespace(self):
        """
        Retrieves the name space of this command handler
        """
        return "herald"

    def get_methods(self):
        """
        Retrieves the list of tuples (command, method) for this command handler
        """
        return [("fire", self.fire),
                ("fire_group", self.fire_group),
                ("send", self.send),
                ("post", self.post),
                ("forget", self.forget),
                ("peers", self.list_peers),
                ("local", self.local_peer), ]

    def fire(self, io_handler, target, subject, *words):
        """
        Fires a message to the given peer.
        """
        try:
            uid = self._herald.fire(target,
                                    beans.Message(subject, ' '.join(words)))
        except KeyError:
            io_handler.write_line("Unknown target: {0}", target)
        except NoTransport:
            io_handler.write_line("No transport to join {0}", target)
        else:
            io_handler.write_line("Message sent: {0}", uid)

    def fire_group(self, io_handler, group, subject, *words):
        """
        Fires a message to the given group of peers.
        """
        try:
            uid, missed = self._herald.fire_group(
                group, beans.Message(subject, ' '.join(words)))
        except KeyError:
            io_handler.write_line("Unknown group: {0}", group)
        except NoTransport:
            io_handler.write_line("No transport to join {0}", group)
        else:
            io_handler.write_line("Message sent: {0}", uid)
            if missed:
                io_handler.write_line("Missed peers: {0}", ",".join(missed))

    def send(self, io_handler, target, subject, *words):
        """
        Sends a message to the given peer(s). Prints responses in the shell.
        """
        try:
            # Send the message with a 10 seconds timeout
            # (we're blocking the shell here)
            result = self._herald.send(target,
                                       beans.Message(subject, ' '.join(words)),
                                       10)
        except KeyError:
            io_handler.write_line("Unknown target: {0}", target)
        except NoTransport:
            io_handler.write_line("No transport to join {0}", target)
        except NoListener:
            io_handler.write_line("No listener for {0}", subject)
        except HeraldTimeout:
            io_handler.write_line("No response given before timeout")
        else:
            io_handler.write_line("Response: {0}", result.subject)
            io_handler.write_line(result.content)

    def post(self, io_handler, target, subject, *words):
        """
        Post a message to the given peer.
        """
        def callback(_, message):
            """
            Received a reply
            """
            io_handler.write_line("Got answer to {0}:", message.reply_to)
            io_handler.write_line(message.content)

        def errback(_, exception):
            """
            Error during message transmission
            """
            io_handler.write_line("Error posting message: {0} ({1})",
                                  type(exception).__name__, exception)

        try:
            uid = self._herald.post(target,
                                    beans.Message(subject, ' '.join(words)),
                                    callback, errback)
        except KeyError:
            io_handler.write_line("Unknown target: {0}", target)
        except NoTransport:
            io_handler.write_line("No transport to join {0}", target)
        else:
            io_handler.write_line("Message sent: {0}", uid)

    def forget(self, io_handler, uid):
        """
        Forgets about the given message
        """
        if self._herald.forget(uid):
            io_handler.write_line("Herald forgot about {0}", uid)
        else:
            io_handler.write_line("Herald wasn't aware of {0}", uid)

    def __print_peer(self, io_handler, peer):
        """
        Prints information about the given peer
        """
        lines = []
        lines.append("Peer {0}".format(peer.uid))
        lines.append("\t- UID......: {0}".format(peer.uid))
        lines.append("\t- Name.....: {0}".format(peer.name))
        lines.append("\t- Node UID.: {0}".format(peer.node_uid))
        lines.append("\t- Node Name: {0}".format(peer.node_name))
        lines.append("\t- Groups...:")
        for group in sorted(peer.groups):
            lines.append("\t\t- {0}".format(group))
        lines.append("\t- Accesses.:")
        for access in sorted(peer.get_accesses()):
            lines.append("\t\t- {0}: {1}"
                         .format(access, peer.get_access(access)))

        lines.append("")
        io_handler.write("\n".join(lines))

    def local_peer(self, io_handler):
        """
        Prints information about the local peer
        """
        self.__print_peer(io_handler, self._directory.get_local_peer())

    def list_peers(self, io_handler):
        """
        Lists known peers and their accesses
        """
        for peer in self._directory.get_peers():
            self.__print_peer(io_handler, peer)
            io_handler.write_line("")
