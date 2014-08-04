"""
Herald's core module
"""

import herald.beans as beans
import herald.directory

class Herald(object):
    """
    Herald's service
    """
    def __init__(self):
        """
        """
        # Peers directory
        self._directory = herald.directory.Directory()

        # Routers
        self._routers = []


    def _get_link(self, peer):
        """
        Returns a link to the given peer

        :return: A Link object
        :raise ValueError: Unknown peer
        """
        assert isinstance(peer, beans.Peer)

        # Look for a link to the peer, using routers
        for router in self._routers:
            link = router.get_link(peer)
            if link:
                return link

        # Not found
        raise ValueError("No link to peer {0}".format(peer))


    def send(self, peer_id, message):
        """
        Synchronously sends a message

        :param peer_id: UUID of a peer
        :param message: Message to send to the peer
        :raise KeyError: Unknown peer
        :raise ValueError: No link to the peer
        """
        assert isinstance(message, beans.RawMessage)

        # Get peer description (raises KeyError)
        peer = self._directory.get_peer(peer_id)

        # Get a link to the peer (raises ValueError)
        link = self._get_link(peer)
        assert isinstance(link, beans.AbstractLink)

        # Call the link, and return its result
        return link.send(message)


    def post(self, peer_id, message):
        """
        Sends a message and returns a Future object to get its result later

        :param peer_id: UUID of a peer
        :param message: Message to send to the peer
        :return: A Future object to grab the response(s) to the message
        :raise KeyError: Unknown peer
        :raise ValueError: No link to the peer
        """
        assert isinstance(message, beans.RawMessage)

        # Get peer description (raises KeyError)
        peer = self._directory.get_peer(peer_id)

        # Get a link to the peer (raises ValueError)
        link = self._get_link(peer)
        assert isinstance(link, beans.AbstractLink)

        # Call the link, and return its result (a Future bean)
        return link.post(message)
