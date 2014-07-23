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

        :param message: A Message bean forged by the transport
        """
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
