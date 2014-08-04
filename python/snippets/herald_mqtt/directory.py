"""
Herald's directory
"""

import herald.beans as beans
import threading

class Directory(object):
    """
    Stores information about peers
    """
    def __init__(self):
        """
        """
        # Peer UUID -> Peer object
        self.peers = {}

        # Group Name -> set of peers UUIDs
        self.groups = {}

        # Thread protection
        self.__lock = threading.Lock()


    def get_peer(self, peer_id):
        """
        Returns the description of the given peer

        :param peer_id: UUID of a peer
        :return: Information about the peer
        :raise KeyError: Unknown peer
        """
        with self.__lock:
            return self.peers[peer_id]


    def get_group_peers(self, group_name):
        """
        Returns the UUIDs of the peers from the given group.

        :param group_name: The name of a group
        :return: A list of peers UUIDs, an empty list if the group is unknown)
        """
        with self.__lock:
            return self.groups.get(group_name, [])


    def register(self, peer):
        """
        Registers a peer according to its description

        :param peer: A Peer description bean
        :raise KeyError:
        """
        assert isinstance(peer, beans.Peer)

        with self.__lock:
            # Check presence
            peer_id = peer.peer_id
            if peer_id in self.peers:
                raise KeyError("Already known peer: {0}".format(peer))

            # Store the description
            self.peers[peer_id] = peer

            # Store in the groups
            for name in peer.groups:
                self.groups.setdefault(name, set()).add(peer_id)


    def unregister(self, peer_id):
        """
        Unregisters the given peer

        :param peer_id: A peer UUID
        :raise KeyError: Unknown peer
        """
        with self.__lock:
            # Pop it from accesses (will raise a KeyError if absent)
            peer = self.peers.pop(peer_id)
            assert isinstance(peer, beans.Peer)

            # Remove it from groups
            for name in peer.groups:
                try:
                    # Clean up the group
                    group = self.groups[name]
                    group.remove(peer_id)

                    # Remove it if it's empty
                    if not group:
                        del self.groups[name]

                except KeyError:
                    # Be tolerant here
                    pass
