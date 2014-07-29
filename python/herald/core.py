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
        _logger.warning("Got message %s from %s",
                        message.subject, message.sender)

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
            self.reply(message, self._directory.get_local_peer().dump(),
                       'herald/directory/welcome')

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

    def fire(self, target, message, reply_to=None):
        """
        Fires (and forget) the given message to the target

        :param target: The UID of a Peer, or a Peer object
                       (ignored if reply_to is given)
        :param message: A Message bean
        :param reply_to: MessageReceived bean this message replies to
                         (optional)
        :raise KeyError: Unknown peer UID
        :raise NoTransport: No transport found to send the message
        """
        if reply_to is not None:
            # Use the message source peer
            try:
                transport = self._transports[reply_to.access]
            except KeyError:
                # Reception transport is not available anymore...
                _logger.warning("No reply transport for access %s",
                                reply_to.access)
                pass
            else:
                # Try to get the Peer bean. If unknown, consider that the
                # "extra" data will help the transport to reply
                try:
                    peer = self._directory.get_peer(reply_to.sender)
                except KeyError:
                    peer = None

                try:
                    # Send the reply
                    transport.fire(peer, message, reply_to.extra)
                except InvalidPeerAccess as ex:
                    _logger.error("Can't reply to %s using %s transport",
                                  peer, reply_to.access)
                else:
                    # Reply sent. Stop here
                    return

        # Standard behavior
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

    def reply(self, message, content, subject=None):
        """
        Replies to a message

        :param message: Original message
        :param content: Content of the response
        :param subject: Reply message subject (same as request if None)
        """
        # Normalize subject
        if not subject:
            subject = message.subject

        try:
            # Fire the reply
            self.fire(message.sender, beans.Message(subject, content), message)
        except KeyError:
            _logger.error("No access to reply to %s", message.sender)
