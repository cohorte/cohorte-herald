#!/usr/bin/python
# -- Content-Encoding: UTF-8 --
"""
Herald Core directory

:author: Thomas Calmant
:copyright: Copyright 2014, isandlaTech
:license: Apache License 2.0
:version: 1.0.0
:status: Alpha

..

    Copyright 2014 isandlaTech

    Licensed under the Apache License, Version 2.0 (the "License");
    you may not use this file except in compliance with the License.
    You may obtain a copy of the License at

        http://www.apache.org/licenses/LICENSE-2.0

    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS,
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    See the License for the specific language governing permissions and
    limitations under the License.
"""

# Module version
import pelix.ipopo.decorators

__version_info__ = (1, 0, 0)
__version__ = ".".join(str(x) for x in __version_info__)

# Documentation strings format
__docformat__ = "restructuredtext en"

# ------------------------------------------------------------------------------

# Herald
import herald
import herald.beans as beans

# Pelix
from pelix.ipopo.decorators import ComponentFactory, Requires, RequiresMap, \
    Provides, BindField, UnbindField, Validate, Invalidate, Instantiate
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
@Requires('_listeners', herald.SERVICE_DIRECTORY_LISTENER, True, True)
@Requires('_group_listeners', herald.SERVICE_DIRECTORY_GROUP_LISTENER,
          True, True)
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

        # Directory listeners
        self._listeners = []

        # Directory group listeners
        self._group_listeners = []

        # Local bean description
        self._local = None

        # UID -> Peer bean
        self._peers = {}

        # Name -> Set of Peer UIDs
        self._names = {}

        # Group name -> Set of Peers
        self._groups = {}

        # Thread safety
        self.__lock = threading.Lock()

    def __contains__(self, peer):
        """
        Adds support for the "in" keyword: checks if the given peer is
        registered in this directory

        :param peer: A peer UID or object
        :return: True if the peer is known
        """
        return peer in self._peers or peer in self._peers.values()

    def __make_local_peer(self, context):
        """
        Prepares a Peer bean with local configuration

        :param context: Bundle context
        """
        # Get local peer UID, node UID and application ID
        peer_uid = context.get_property(herald.FWPROP_PEER_UID) \
            or context.get_property(pelix.constants.FRAMEWORK_UID)
        node_uid = context.get_property(herald.FWPROP_NODE_UID)
        app_id = context.get_property(herald.FWPROP_APPLICATION_ID) \
            or herald.DEFAULT_APPLICATION_ID

        # Find configured groups
        groups = context.get_property(herald.FWPROP_PEER_GROUPS)
        if not groups:
            groups = []
        elif is_string(groups):
            groups = (group.strip() for group in groups.split(',')
                      if group.strip)
        groups = set(groups)

        # Add pre-configured group: node UID
        if node_uid:
            groups.add(node_uid)

        # Make the Peer bean
        peer = beans.Peer(peer_uid, node_uid, app_id, groups, self)

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
        self._names.clear()
        self._groups.clear()

        # Prepare local peer
        self._local = self.__make_local_peer(context)
        for group in self._local.groups:
            # Create (empty) groups
            self._groups[group] = set()

    @Invalidate
    def _invalidate(self, _):
        """
        Component invalidated
        """
        # Clean all up
        self._peers.clear()
        self._names.clear()
        self._groups.clear()
        self._local = None

    @BindField('_directories')
    def _bind_directory(self, _, svc, svc_ref):
        """
        A transport directory has been bound
        """
        access_id = svc_ref.get_property(herald.PROP_ACCESS_ID)
        if not access_id:
            return

        with self.__lock:
            for peer in self._peers.values():
                try:
                    access = peer.get_access(access_id)
                except KeyError:
                    # No access of this kind
                    pass
                else:
                    if isinstance(access, beans.RawAccess):
                        # We need to convert a raw access bean
                        parsed = svc.load_access(access.dump())
                        peer.set_access(access_id, parsed)

    @UnbindField('_directories')
    def _unbind_directory(self, _, svc, svc_ref):
        """
        A transport directory has gone away
        """
        access_id = svc_ref.get_property(herald.PROP_ACCESS_ID)
        if not access_id:
            return

        with self.__lock:
            for peer in self._peers.values():
                try:
                    # Get the current access information
                    access = peer.get_access(access_id)
                except KeyError:
                    # No access of this kind
                    pass
                else:
                    # Convert to a RawAccess bean
                    peer.set_access(access_id,
                                    beans.RawAccess(access_id, access.dump()))

    @BindField('_listeners', if_valid=True)
    def _bind_listener(self, _, svc, svc_ref):
        """
        A directory listener has been bound
        """
        for peer in list(self._peers.values()):
            svc.peer_registered(peer)

    @BindField('_group_listeners', if_valid=True)
    def _bind_group_listener(self, _, svc, svc_ref):
        """
        A directory group listener has been bound
        """
        for group in self._groups:
            svc.group_set(group)

    def __notify_group_set(self, group):
        """
        Notify listeners about a new group of peers

        :param group: Name of the group
        """
        if self._group_listeners:
            for listener in self._group_listeners[:]:
                try:
                    # pylint: disable=W0703
                    listener.group_set(group)
                except Exception as ex:
                    _logger.exception("Error notifying listener: %s", ex)

    def __notify_group_unset(self, group):
        """
        Notify listeners about the removal of a group

        :param group: Name of the group
        """
        if self._group_listeners:
            for listener in self._group_listeners[:]:
                try:
                    # pylint: disable=W0703
                    listener.group_unset(group)
                except Exception as ex:
                    _logger.exception("Error notifying listener: %s", ex)

    def __notify_peer_registered(self, peer):
        """
        Notify listeners about a new peer

        :param peer: Bean of the new peer
        """
        if self._listeners:
            for listener in self._listeners[:]:
                try:
                    # pylint: disable=W0703
                    listener.peer_registered(peer)
                except Exception as ex:
                    _logger.exception("Error notifying listener: %s", ex)

    def __notify_peer_unregistered(self, peer):
        """
        Notify listeners about the loss of peer

        :param peer: Bean of the loss of peer
        """
        if self._listeners:
            for listener in self._listeners[:]:
                try:
                    # pylint: disable=W0703
                    listener.peer_unregistered(peer)
                except Exception as ex:
                    _logger.exception("Error notifying listener: %s", ex)

    def __notify_peer_updated(self, peer, access_id, data, previous=None):
        """
        Notifies listeners about the modification of a peer access

        :param peer: Bean of the modified peer
        :param access_id: ID of the modified access
        :param data: New access data (None of unset)
        :param previous: Previous access data (None for set)
        """
        if self._listeners:
            for listener in self._listeners[:]:
                try:
                    # pylint: disable=W0703
                    listener.peer_updated(peer, access_id, data, previous)
                except Exception as ex:
                    _logger.exception("Error notifying listener: %s", ex)

    @property
    def local_uid(self):
        """
        Returns the local peer UID
        """
        return self._local.uid

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
        try:
            return self._names[name].copy()
        except KeyError:
            return [self._peers[name].uid]

    def get_peers_for_name(self, name):
        """
        Returns the Peer beans of the peers having the given name

        :param name: The name used by some peers
        :return: A list of Peer beans
        :raise KeyError: No peer has this name
        """
        try:
            return [self._peers[uid] for uid in self._names[name]]
        except KeyError:
            return [self._peers[name]]

    def get_peers_for_group(self, group):
        """
        Returns the Peer beans of the peers belonging to the given group

        :param group: The name of a group
        :return: A list of Peer beans
        :raise KeyError: Unknown group
        """
        if group == 'all':
            # Special group: retrieve all peers
            return list(self._peers.values())

        return self._groups[group].copy()

    def get_peers_for_node(self, node_uid):
        """
        Returns the Peer beans of the peers associated to the given node UID

        :param node_uid: The UID of a node
        :return: A list of Peer beans
        """
        return [peer for peer in self._peers.values()
                if peer.node_uid == node_uid]

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

            # Notify listeners only if the peer is already/still registered
            if peer.uid in self._peers:
                # Notify directory listeners
                self.__notify_peer_updated(peer, access_id, data)

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

            # Notify directory listeners
            self.__notify_peer_updated(peer, access_id, None, data)

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
                try:
                    # Do not reload already known peer
                    self.register(description)
                except ValueError as ex:
                    _logger.warning("Error loading peer dump: %s", ex)

    def register(self, description):
        """
        Registers a peer

        :param description: Description of the peer, in the format of dump()
        :return: The registered Peer bean
        :raise ValueError: Invalid peer UID
        """
        notification = self.register_delayed(description)
        notification.notify()
        return notification.peer

    def register_delayed(self, description):
        """
        Registers a peer

        :param description: Description of the peer, in the format of dump()
        :return: A DelayedNotification bean
        :raise ValueError: Invalid peer UID
        """
        with self.__lock:
            uid = description['uid']
            if uid == self._local.uid:
                # Ignore local peer
                return beans.DelayedNotification(None, None)

            try:
                app_id = description['app_id']
            except KeyError:
                app_id = herald.DEFAULT_APPLICATION_ID

            if app_id != self._local.app_id:
                # Ignore foreign peers
                _logger.debug("Refused registration of %s from application %s",
                              uid, app_id)
                return beans.DelayedNotification(None, None)

            try:
                # Check if the peer is known
                peer = self._peers[uid]
                peer_update = True
            except KeyError:
                # Make a new bean
                peer_update = False
                peer = beans.Peer(uid, description['node_uid'], app_id,
                                  description['groups'], self)

                # Setup writable properties
                for name in ('name', 'node_name'):
                    setattr(peer, name, description[name])

            # In any case, parse and store (new/updated) accesses
            for access_id, data in description['accesses'].items():
                try:
                    data = self._directories[access_id].load_access(data)
                except KeyError:
                    # Access not available for parsing: keep a RawAccess bean
                    data = beans.RawAccess(access_id, data)

                # Store the parsed data: listeners will be notified IF the peer
                # was already stored
                peer.set_access(access_id, data)

            if not peer_update:
                # Store the peer after accesses have been set
                # (avoids to notify about update before registration)
                self._peers[uid] = peer

                # Store the peer
                self._names.setdefault(peer.name, set()).add(peer.uid)

                # Set up groups
                new_groups = set()
                for group in peer.groups:
                    try:
                        # Get the group
                        peers = self._groups[group]
                    except KeyError:
                        # Group must be created: notify about it
                        peers = self._groups[group] = set()
                        new_groups.add(group)

                    peers.add(peer)

                # Notify about new groups
                for group in new_groups:
                    self.__notify_group_set(group)

                return beans.DelayedNotification(peer,
                                                 self.__notify_peer_registered)
            else:
                return beans.DelayedNotification(peer, None)

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
                    uids.remove(uid)
                    if not uids:
                        del self._names[peer.name]
                except KeyError:
                    # Name wasn't registered...
                    pass

                for group in peer.groups:
                    try:
                        peers = self._groups[group]
                        peers.remove(peer)
                        if not peers:
                            # Remove the group and notify listeners
                            del self._groups[group]
                            self.__notify_group_unset(group)

                    except KeyError:
                        # Peer wasn't in that group
                        pass

        # Notify listeners
        self.__notify_peer_unregistered(peer)
        return peer
