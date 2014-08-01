#!/usr/bin/python
# -- Content-Encoding: UTF-8 --
"""
Herald Core directory
"""

# Herald
import herald
import herald.beans as beans

# Pelix
from pelix.ipopo.decorators import ComponentFactory, RequiresMap, Provides, \
    Validate, Invalidate, Instantiate
from pelix.utilities import is_string
import pelix.constants


# Standard library
import logging
import threading

# ------------------------------------------------------------------------------

_logger = logging.getLogger(__name__)

# ------------------------------------------------------------------------------


@ComponentFactory("herald-directory-factory")
@Provides(herald.SERVICE_DIRECTORY)
@RequiresMap('_directories', herald.SERVICE_TRANSPORT_DIRECTORY,
             herald.PROP_ACCESS_ID, False, False, True)
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

        # Local bean description
        self._local_uid = None
        self._local = None

        # UID -> Peer bean
        self._peers = {}

        # Name -> Set of Peer UIDs
        self._names = {}

        # Group name -> Set of Peer UIDs
        self._groups = {}

        # Thread safety
        self.__lock = threading.Lock()

    def __make_local_peer(self, context):
        """
        Prepares a Peer bean with local configuration

        :param context: Bundle context
        """
        # Get local peer UID and node UID
        peer_uid = context.get_property(herald.FWPROP_PEER_UID) \
            or context.get_property(pelix.constants.FRAMEWORK_UID)
        node_uid = context.get_property(herald.FWPROP_NODE_UID)

        # Find configured groups
        groups = context.get_property(herald.FWPROP_PEER_GROUPS)
        if not groups:
            groups = []
        elif is_string(groups):
            groups = (group.strip() for group in groups.split(',')
                      if group.strip)
        groups = set(groups)

        # Add pre-configured groups: 'all' and node
        groups.add('all')
        if node_uid:
            groups.add(node_uid)

        # Make the Peer bean
        peer = beans.Peer(peer_uid, node_uid, groups, self)

        # Setup node and name information
        peer.name = context.get_property(herald.FWPROP_PEER_NAME)
        peer.node_name = context.get_property(herald.FWPROP_NODE_NAME)
        return peer

    @Validate
    def _validate(self, context):
        """
        Component validated
        """
        # Clean up remaining data (if any)
        self._peers.clear()
        self._groups.clear()

        self._local = self.__make_local_peer(context)
        self._local_uid = self._local.uid

    @Invalidate
    def _invalidate(self, context):
        """
        Component invalidated
        """
        # Clean all up
        self._peers.clear()
        self._groups.clear()
        self._local = None

    @property
    def local_uid(self):
        """
        Returns the local peer UID
        """
        return self._local_uid

    def get_peer(self, uid):
        """
        Retrieves the peer with the given UID

        :param uid: The UID of a peer
        :return: A Peer bean
        :raise KeyError: Unknown peer
        """
        return self._peers[uid]

    def get_local_peer(self):
        """
        Returns the description of the local peer

        :return: The description of the local peer
        """
        return self._local

    def get_peers(self):
        """
        Returns the list of all known peers

        :return: A tuple containing all known peers
        """
        return tuple(self._peers.values())

    def get_uids_for_name(self, name):
        """
        Returns the UIDs of the peers having the given name

        :param name: The name used by some peers
        :return: A set of UIDs
        :raise KeyError: No peer has this name
        """
        return self._names[name].copy()

    def get_peers_for_name(self, name):
        """
        Returns the Peer beans of the peers having the given name

        :param name: The name used by some peers
        :return: A list of Peer beans
        :raise KeyError: No peer has this name
        """
        return [self._peers[uid] for uid in self._names[name]]

    def get_uids_for_group(self, group):
        """
        Returns the UIDs of the peers having the given name

        :param group: The name of a group
        :return: A set of UIDs
        :raise KeyError: Unknown group
        """
        return self._groups[group].copy()

    def get_peers_for_group(self, group):
        """
        Returns the Peer beans of the peers having the given name

        :param group: The name of a group
        :return: A list of Peer beans
        :raise KeyError: Unknown group
        """
        return [self._peers[uid] for uid in self._groups[group]]

    def peer_access_set(self, peer, access_id, data):
        """
        A new peer access is available. Called by a Peer bean.

        :param peer: The modified Peer bean
        :param access_id: ID of the access
        :param data: Information of the peer access
        """
        try:
            # Get the handling directory
            directory = self._directories[access_id]
        except KeyError:
            # No handler for this directory
            pass
        else:
            try:
                # Notify it
                directory.peer_access_set(peer, data)
            except Exception as ex:
                _logger.exception("Error notifying a transport directory: %s",
                                  ex)

    def peer_access_unset(self, peer, access_id, data):
        """
        A peer access has been removed. Called by  a Peer bean.

        :param peer: The modified Peer bean
        :param access_id: ID of the removed access
        :param data: Previous information of the peer access
        """
        try:
            # Get the handling directory
            directory = self._directories[access_id]
        except KeyError:
            # No handler for this directory
            pass
        else:
            try:
                # Notify it
                directory.peer_access_unset(peer, data)
            except Exception as ex:
                _logger.exception("Error notifying a transport directory: %s",
                                  ex)

        if not peer.has_accesses():
            # Peer has no more access, unregister it
            self.unregister(peer.uid)

    def dump(self):
        """
        Dumps the content of the local directory in a dictionary

        :return: A UID -> description dictionary
        """
        return {peer.uid: peer.dump() for peer in self._peers.values()}

    def load(self, dump):
        """
        Loads the content of a dump

        :param dump: The result of a call to dump()
        """
        for uid, description in dump.items():
            if uid not in self._peers:
                # Do not reload already known peer
                self.register(description)

    def register(self, description):
        """
        Registers a peer

        :param description: Description of the peer, in the format of dump()
        """
        with self.__lock:
            uid = description['uid']
            if uid == self._local_uid or uid in self._peers:
                # Local/Already known peer: ignore
                return

            # Make a new bean
            peer = beans.Peer(uid, description['node_uid'],
                              description['groups'], self)

            # Setup writable properties
            for name in ('name', 'node_name'):
                setattr(peer, name, description[name])

            # Accesses
            for access_id, data in description['accesses'].items():
                try:
                    data = self._directories[access_id].load_access(data)
                except KeyError:
                    # Access not available for parsing
                    pass

                # Store the parsed data, or keep it as is
                peer.set_access(access_id, data)

            # Store the peer
            self._peers[uid] = peer
            self._names.setdefault(peer.name, set()).add(peer)
            for group in peer.groups:
                self._groups.setdefault(group, set()).add(peer)

            _logger.info("Registered peer: %s", peer)

    def unregister(self, uid):
        """
        Unregisters a peer from the directory

        :param uid: UID of the peer
        :return: The Peer bean if it was known, else None
        """
        with self.__lock:
            try:
                # Pop the peer bean
                peer = self._peers.pop(uid)
            except KeyError:
                # Unknown peer
                return
            else:
                # Remove it from other dictionaries
                try:
                    uids = self._names[peer.name]
                    uids.remove(peer.uid)
                    if not uids:
                        del self._names[peer.name]
                except KeyError:
                    # Name wasn't registered...
                    pass

                for group in peer.groups:
                    try:
                        uids = self._groups[group]
                        uids.remove(peer.uid)
                        if not uids:
                            del self._groups[group]
                    except KeyError:
                        # Peer wasn't in that group
                        pass

                return peer
