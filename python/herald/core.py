#!/usr/bin/python
# -- Content-Encoding: UTF-8 --
"""
Herald Core service
"""

# Herald
from herald.exceptions import InvalidPeerAccess, NoTransport
import herald.beans as beans

# Pelix
from pelix.ipopo.decorators import ComponentFactory, Requires, Provides, \
    Validate, Invalidate, Instantiate, RequiresMap

# Standard library
import logging

# ------------------------------------------------------------------------------

_logger = logging.getLogger(__name__)

# ------------------------------------------------------------------------------

@ComponentFactory("herald-core-factory")
@Provides('herald.core')
@Requires('_directory', 'herald.directory')
@RequiresMap('_transports', 'herald.transport', 'herald.access.id',
             False, False, True)
@Instantiate("herald-core")
class Herald(object):
    """
    Herald core service
    """
    def __init__(self):
        """
        Sets up members
        """
        # Herald core directory
        self._directory = None

        # Herald transports: access ID -> implementation
        self._transports = {}

    @Validate
    def _validate(self, context):
        """
        Component validated
        """
        _logger.debug("Herald core service validated")

    @Invalidate
    def _invalidate(self, context):
        """
        Component invalidated
        """
        _logger.debug("Herald core service invalidated")

    def handle_message(self, message):
        """
        Handles a message received from a transport implementation.

        Unlocks/calls back the senders of the message this one responds to.

        :param message: A MessageReceived bean forged by the transport
        """
        # User a tuple, because list can't be compared to tuples
        parts = tuple(part for part in message.subject.split('/') if part)
        if parts[:2] == ('herald', 'directory'):
            try:
                # Directory update message
                self._handle_directory_message(message, parts[2])
            except IndexError:
                # Not enough arguments for a directory update: ignore
                pass

        # Notify others of the message
        self.__notify(message)

    def _handle_directory_message(self, message, kind):
        """
        Handles a directory update message

        :param message: Message received from another peer
        :param kind: Kind of directory message
        """
        if kind == 'newcomer':
            # A new peer appears: register it
            self._directory.register(message.content)

            # Reply to it
            message.reply('welcome', self._directory.get_local_peer().dump())

        elif kind == 'welcome':
            # A peer replied to our 'newcomer' event
            self._directory.register(message.content)

        elif kind == 'bye':
            # A peer is going away
            self._directory.unregister(message.content)

    def __notify(self, message):
        """
        Calls back message senders about responses or notifies the reception of
        a message

        :param message: The received message
        """
        if message.reply_to:
            # This is an answer to a message: unlock waiting events
            pass
        else:
            # This a new message: call listeners in the task thread
            pass

    def fire(self, target, message):
        """
        Fires (and forget) the given message to the target

        :param target: The UID of a Peer, or a Peer object
        :param message: A Message bean
        :raise KeyError: Unknown peer UID
        :raise NoTransport: No transport found to send the message
        """
        # Get the Peer object
        if not isinstance(target, beans.Peer):
            peer = self._directory.get_peer(target)
        else:
            peer = target

        # Check if some transports are bound
        if not self._transports:
            raise NoTransport("No transport bound yet.")

        # Get accesses
        accesses = peer.get_accesses()
        for access in accesses:
            try:
                transport = self._transports[access]
            except KeyError:
                # No transport for this kind of access
                pass
            else:
                try:
                    # Call it
                    transport.fire(peer, message)
                except InvalidPeerAccess as ex:
                    # Transport can't read peer access data
                    _logger.debug("Error using transport %s: %s", access, ex)
                else:
                    # Success
                    break
        else:
            # No transport for those accesses
            raise NoTransport("No transport found for peer {0}".format(peer))
