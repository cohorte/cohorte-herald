#!/usr/bin/python
# -- Content-Encoding: UTF-8 --
"""
Herald HTTP local discovery, based on a forker directory dump

:author: Bassem Debbabi
:copyright: Copyright 2016, isandlaTech
:license: Apache License 2.0
:version: 0.0.5
:status: Alpha

..

    Copyright 2016 isandlaTech

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
__version_info__ = (0, 0, 5)
__version__ = ".".join(str(x) for x in __version_info__)

# Documentation strings format
__docformat__ = "restructuredtext en"

# ------------------------------------------------------------------------------

# Herald
from herald.transports.http import ACCESS_ID, SERVICE_HTTP_TRANSPORT, SERVICE_HTTP_RECEIVER, \
    FACTORY_DISCOVERY_MULTICAST, PROP_MULTICAST_GROUP, PROP_MULTICAST_PORT
import herald
import herald.beans as beans
import herald.utils as utils
import herald.transports.peer_contact as peer_contact
from . import FACTORY_DISCOVERY_LOCAL

# Pelix/iPOPO
from pelix.ipopo.decorators import ComponentFactory, Requires, Validate, Provides, \
    Invalidate, Property, RequiresBest
from pelix.utilities import to_bytes, to_unicode

# Cohorte
import cohorte
import cohorte.forker
import cohorte.monitor

# Standard library
import logging
import os
import select
import socket
import struct
import threading
import time

# ------------------------------------------------------------------------------

# Heart beat packet type
PACKET_TYPE_HEARTBEAT = 1

# Last beat packet type
PACKET_TYPE_LASTBEAT = 2

PROBE_CHANNEL_MULTICAST = "http_multicast"
""" Name of the multicast discovery probe channel """

_SUBJECT_PREFIX = "herald/local/discovery"
""" Common prefix to Herald Local Discovery  """

_SUBJECT_MATCH_ALL = "{0}/*".format(_SUBJECT_PREFIX)
""" Filter to match agent signals """

SUBJECT_NOTIFY_NEIGHBOR_LOST = "{0}/notify_neighbor_list".format(_SUBJECT_PREFIX)
"""  """

SUBJECT_GET_NEIGHBORS_LIST = "{0}/get_neighbors_list".format(_SUBJECT_PREFIX)
"""  """


_logger = logging.getLogger(__name__)

# ------------------------------------------------------------------------------


@ComponentFactory(FACTORY_DISCOVERY_LOCAL)
@Provides(herald.SERVICE_DIRECTORY_LISTENER)
@Provides(herald.SERVICE_LISTENER)
@RequiresBest('_probe', herald.SERVICE_PROBE)
@Requires('_directory', herald.SERVICE_DIRECTORY)
#@Requires('_receiver', SERVICE_HTTP_RECEIVER)
@Requires('_transport', SERVICE_HTTP_TRANSPORT)
@Requires('_herald', herald.SERVICE_HERALD)
@Property('_filters', herald.PROP_FILTERS, 
        [cohorte.monitor.SIGNAL_ISOLATE_LOST, SUBJECT_GET_NEIGHBORS_LIST])
class LocalDiscovery(object):
    """
    Discovery of Herald peers based on multicast
    """
    def __init__(self):
        """
        Sets up the component
        """
        # Injected services
        self._herald = None
        self._directory = None
        #self._receiver = None
        self._transport = None
        self._probe = None
        self._herald = None
        # Local peer bean
        self._local_peer = None
        # Threads
        self._discover_forker_thread = None 
        self._discover_neighbors_thread = None 
        #self._lst_lock = threading.Lock()
        # Bundle context
        self._context = None
        # forker information (TODO to be retrieved from broker)
        self._forker_host = "127.0.0.1"
        self._forker_port = 9000
        self._forker_path = "herald"
        self._forker = None
    
    def herald_message(self, herald_svc, message):
        """
        Handles herald message

        :param herald_svc: The Herald service
        :param message: The received message bean
        """
        #_logger.info("##### local.discovery : herald_message %s . content=%s", message, message.content)
        subject = message.subject
        reply = None
        if subject == cohorte.monitor.SIGNAL_ISOLATE_LOST:
            # local neighbor Peer is going away                                
            try:
                peer = self._directory.get_peer(message.content)
                if peer.node_uid == self._local_peer.node_uid:                    
                    peer.unset_access(ACCESS_ID)
            except KeyError:
                # Unknown peer
                pass
        elif subject == SUBJECT_GET_NEIGHBORS_LIST:            
            neighbors = self._directory.get_peers_for_node(self._local_peer.node_uid)            
            reply = {peer.uid: peer.dump() for peer in neighbors if peer.uid != message.content}                                     
            herald_svc.reply(message, reply)            


    @Validate
    def _validate(self, context):
        """
        Component validated
        """
        # store framework objects
        self._context = context
        # init local Peer bean        
        self._local_peer = self._directory.get_local_peer()
                
        # if this Peer is not the forker, we should send a contact message 
        # to its forker
        broker_url = context.get_property(cohorte.PROP_CONFIG_BROKER)
        if broker_url:
            # TODO should ensure that herald http transport is already up ?                       
            self._discover_forker_thread = threading.Thread(target=self.__discover_forker,
                                              name="Herald-Local-DiscoverForker")
            self._discover_forker_thread.start()
       

    @Invalidate
    def _invalidate(self, _):
        """
        Component invalidated
        """
        # Wait for the threads to stop        
        if self._discover_forker_thread is not None:
            self._discover_forker_thread.join(.5)
        self._discover_forker_thread = None

        if self._discover_neighbors_thread is not None:
            self._discover_neighbors_thread.join(.5)
        self._discover_neighbors_thread = None


    def __discover_peer(self, host, port, path):
        """
        Discover a local Peer by sending to him the contact message
        """
        if path.startswith('/'):
            # Remove the starting /, as it is added while forging the URL
            path = path[1:]

        # Normalize the address of the sender
        host = utils.normalize_ip(host)

        # Prepare the "extra" information, like for a reply
        extra = {'host': host, 'port': port, 'path': path}
        local_dump = self._directory.get_local_peer().dump()
        try:
            self._transport.fire(
                None,
                beans.Message(peer_contact.SUBJECT_DISCOVERY_STEP_1,
                              local_dump), extra)
        except Exception as ex:
            _logger.exception("Error contacting peer: %s", ex)

    def __discover_forker(self):
        """
        Discover the forker of this local Peer by sending to him 
        the contact message
        """        
        host = self._forker_host
        port = self._forker_port
        path = self._forker_path

        if path.startswith('/'):
            # Remove the starting /, as it is added while forging the URL
            path = path[1:]

        # Normalize the address of the sender
        host = utils.normalize_ip(host)

        # Prepare the "extra" information, like for a reply
        extra = {'host': host, 'port': port, 'path': path}
        local_dump = self._directory.get_local_peer().dump()
        try:
            self._transport.fire(
                None,
                beans.Message(peer_contact.SUBJECT_DISCOVERY_STEP_1,
                              local_dump), extra)
        except Exception as ex:
            _logger.exception("Error contacting peer: %s", ex)
        
        
    def __discover_neighbors(self):
        """
        Discover local neighbor Peers.
        The list of the neighbor peers is retrieved from the forker.
        We should ensure that the forker if properly added to the local directory
        before sending him this contact message.
        """
        try:
            reply = self._herald.send(
                self._forker.uid,
                beans.Message(SUBJECT_GET_NEIGHBORS_LIST, self._local_peer.uid))
            if reply is not None:                
                for peer_uid in reply.content:
                    self.__discover_neighbor(reply.content[peer_uid])                            
        except Exception as ex:
            _logger.exception("Error contacting forker peer to retrieve local neighbor peers: %s", ex)


    def __discover_neighbor(self, peer_dump):
        """
        Discover local neighbor Peer
        """
        host = peer_dump['accesses']['http'][0]
        port = peer_dump['accesses']['http'][1]
        path = peer_dump['accesses']['http'][2]
        
        if path.startswith('/'):
            # Remove the starting /, as it is added while forging the URL
            path = path[1:]

        # Normalize the address of the sender
        host = utils.normalize_ip(host)

        # Prepare the "extra" information, like for a reply
        extra = {'host': host, 'port': port, 'path': path}
        local_dump = self._directory.get_local_peer().dump()
        try:
            self._transport.fire(
                None,
                beans.Message(peer_contact.SUBJECT_DISCOVERY_STEP_1,
                              local_dump), extra)
        except Exception as ex:
            _logger.exception("Error contacting peer: %s", ex)
        

    """
    Directory Listener callbacks --------------------------------------------------------
    """

    def peer_registered(self, peer):
        if peer is not None:                    
            if self._local_peer.name != cohorte.FORKER_NAME:
                # apply only in peers not forker
                if peer.node_uid == self._local_peer.node_uid:
                    # monitor only local peers (same node)
                    if peer.name == cohorte.FORKER_NAME:
                        # forker registred                        
                        self._forker = peer
                        self._discover_neighbors_thread = threading.Thread(target=self.__discover_neighbors,
                                              name="Herald-Local-DiscoverNeighbors")
                        self._discover_neighbors_thread.start()


    def peer_updated(self, peer, access_id, data, previous):
        pass

    def peer_unregistered(self, peer):
        pass

    