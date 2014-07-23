#!/usr/bin/python
# -- Content-Encoding: UTF-8 --
"""
Herald Core directory
"""

# Herald
import herald.beans as beans

# Standard library
import logging
from pelix.ipopo.decorators import ComponentFactory, RequiresMap, Provides, \
    Validate, Invalidate, Instantiate

# ------------------------------------------------------------------------------

_logger = logging.getLogger(__name__)

# ------------------------------------------------------------------------------

@ComponentFactory("herald-directory-factory")
@Provides('herald.directory')
@RequiresMap('_directories', 'herald.transport.directory', 'herald.access.id',
             False, False, True)
@Instantiate("herald-directory")
class HeraldDirectory(object):
    """
    Core Directory for Herald
    """
    def __init__(self):
        """
        Sets up the transport
        """
        # Transport-specific directories
        self._directories = {}

        # UID -> Peer bean
        self._peers = {}

        # Group name -> Peer UIDs
        self._groups = {}

    @Validate
    def _validate(self, context):
        """
        Component validated
        """
        self._peers.clear()
        self._groups.clear()

    @Invalidate
    def _invalidate(self, context):
        """
        Component invalidated
        """
        self._peers.clear()
        self._groups.clear()

    def get_peer(self, uid):
        """
        Retrieves the peer with the given UID

        :param uid: The UID of a peer
        :return: A Peer bean
        :raise KeyError: Unknown peer
        """
        return self._peers[uid]

    def dump(self):
        """
        Dumps the content of the local directory in a dictionary

        :return: A UID -> description dictionary
        """
        dump = {}
        for peer in self._peers.values():
            # Properties
            peer_dump = {getattr(peer, name)
                         for name in ('uid', 'name',
                                      'node_uid', 'node_name',
                                      'groups')}

            # Accesses
            accesses = {}
            for access in peer.get_accesses():
                accesses[access] = peer.get_access(access).dump()
            peer_dump['accesses'] = accesses

            dump[peer.uid] = peer_dump

        return dump

    def load(self, dump):
        """
        Loads the content of a dump

        :param dump: The result of a call to dump()
        """
        for uid, description in dump.items():
            if uid in self._peers:
                # Already known peer: ignore
                continue

            # Make the peer bean
            peer = beans.Peer(uid)

            # Setup writable properties
            for name in ('name', 'node_uid', 'node_name', 'groups'):
                setattr(peer, name, description[name])

            # Accesses
            for access_id, data in description['accesses']:
                try:
                    data = self._directories[access_id].load_access(data)
                except KeyError:
                    # Access not available for parsing
                    pass

                # Store the parsed data, or keep it as is
                peer.set_access(access_id, data)

            # Store the peer
            self._peers[uid] = peer


    def register(self, uid, description):
        """
        Registers a peer

        :param uid: UID of the peer
        :param description: Description of the peer, in the format of dump()
        """
        pass

    def unregister(self, uid):
        """
        Unregisters a peer from the directory

        :param uid: UID of the peer
        """
        pass
