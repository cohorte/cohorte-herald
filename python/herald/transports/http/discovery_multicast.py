#!/usr/bin/python
# -- Content-Encoding: UTF-8 --
"""
Herald HTTP transport discovery, based on a homemade multicast protocol

:author: Thomas Calmant
:copyright: Copyright 2014, isandlaTech
:license: Apache License 2.0
:version: 1.0.1
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

# Bundle version
import herald.version
__version__=herald.version.__version__

# ------------------------------------------------------------------------------

# Herald
from . import ACCESS_ID, SERVICE_HTTP_TRANSPORT, SERVICE_HTTP_RECEIVER, \
    FACTORY_DISCOVERY_MULTICAST, PROP_MULTICAST_GROUP, PROP_MULTICAST_PORT, \
    PROP_DISCOVER_LOCAL_PEERS
import herald
import herald.beans as beans
import herald.utils as utils
import herald.transports.peer_contact as peer_contact

# Pelix/iPOPO
from pelix.ipopo.decorators import ComponentFactory, Requires, Validate, \
    Invalidate, Property, RequiresBest
from pelix.utilities import to_bytes, to_unicode

# Standard library
import logging
import os
import select
import socket
import struct
import threading
import time

# ------------------------------------------------------------------------------

# Version of packet format
# 3: used in Cohorte starting from version 1.2
PACKET_FORMAT_VERSION = 3

# Heart beat packet type
PACKET_TYPE_HEARTBEAT = 1

# Last beat packet type
PACKET_TYPE_LASTBEAT = 2

PROBE_CHANNEL_MULTICAST = "http_multicast"
""" Name of the multicast discovery probe channel """

_logger = logging.getLogger(__name__)

# ------------------------------------------------------------------------------

if os.name == "nt":
    # Windows Specific code
    def pton(family, address):
        """
        Calls inet_pton

        :param family: Socket family
        :param address: A string address
        :return: The binary form of the given address
        """
        if family == socket.AF_INET:
            return socket.inet_aton(address)

        elif family == socket.AF_INET6:
            # Do it using WinSocks
            import ctypes
            winsock = ctypes.windll.ws2_32

            # Prepare structure
            class sockaddr_in6(ctypes.Structure):
                """
                Definition of the C structure sockaddr_in6
                """
                # pylint: disable=C0103
                _fields_ = [("sin6_family", ctypes.c_short),
                            ("sin6_port", ctypes.c_ushort),
                            ("sin6_flowinfo", ctypes.c_ulong),
                            ("sin6_addr", ctypes.c_ubyte * 16),
                            ("sin6_scope_id", ctypes.c_ulong)]

            # Prepare pointers
            addr_ptr = ctypes.c_char_p(to_bytes(address))

            out_address = sockaddr_in6()
            size = len(sockaddr_in6)
            size_ptr = ctypes.pointer(size)

            # Second call
            winsock.WSAStringToAddressA(addr_ptr, family, 0,
                                        out_address, size_ptr)

            # Convert the array...
            bin_addr = 0
            for part in out_address.sin6_addr:
                bin_addr = bin_addr * 16 + part

            return bin_addr

        else:
            raise ValueError("Unhandled socket family: {0}".format(family))

else:
    # Other systems
    def pton(family, address):
        """
        Calls inet_pton

        :param family: Socket family
        :param address: A string address
        :return: The binary form of the given address
        """
        return socket.inet_pton(family, address)


def make_mreq(family, address):
    """
    Makes a mreq structure object for the given address and socket family.

    :param family: A socket family (AF_INET or AF_INET6)
    :param address: A multicast address (group)
    :raise ValueError: Invalid family or address
    """
    if not address:
        raise ValueError("Empty address")

    # Convert the address to a binary form
    group_bin = pton(family, address)

    if family == socket.AF_INET:
        # IPv4
        # struct ip_mreq
        # {
        #     struct in_addr imr_multiaddr; /* IP multicast address of group */
        #     struct in_addr imr_interface; /* local IP address of interface */
        # };
        # "=I" : Native order, standard size unsigned int
        return group_bin + struct.pack("=I", socket.INADDR_ANY)

    elif family == socket.AF_INET6:
        # IPv6
        # struct ipv6_mreq {
        #    struct in6_addr ipv6mr_multiaddr;
        #    unsigned int    ipv6mr_interface;
        # };
        # "@I" : Native order, native size unsigned int
        return group_bin + struct.pack("@I", 0)

    raise ValueError("Unknown family {0}".format(family))


def create_multicast_socket(address, port, join=True):
    """
    Creates a multicast socket according to the given address and port.
    Handles both IPv4 and IPv6 addresses.

    :param address: Multicast address/group
    :param port: Socket port
    :param join: If False, the socket is not bound and does not join the
                 multicast group (creates a simple UDP socket)
    :return: A tuple (socket, listening address)
    :raise ValueError: Invalid address or port
    """
    # Get the information about a datagram (UDP) socket, of any family
    try:
        addrs_info = socket.getaddrinfo(address, port, socket.AF_UNSPEC,
                                        socket.SOCK_DGRAM)
    except socket.gaierror:
        raise ValueError("Error retrieving address information ({0}, {1})"
                         .format(address, port))

    if len(addrs_info) > 1:
        _logger.debug("More than one address information found. "
                      "Using the first one.")

    # Get the first entry : (family, socktype, proto, canonname, sockaddr)
    addr_info = addrs_info[0]

    # Only accept IPv4/v6 addresses
    if addr_info[0] not in (socket.AF_INET, socket.AF_INET6):
        # Unhandled address family
        raise ValueError("Unhandled socket family : %d" % (addr_info[0]))

    # Prepare the socket
    sock = socket.socket(addr_info[0], socket.SOCK_DGRAM)

    if join:
        # Reuse address
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            # Special case for MacOS
            # pylint: disable=no-member
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        except AttributeError:
            pass

        # Bind the socket
        if sock.family == socket.AF_INET:
            # IPv4 binding
            sock.bind(('0.0.0.0', port))
        else:
            # IPv6 Binding
            sock.bind(('::', port))

        # Prepare the mreq structure to join the group
        # addrinfo[4] = (addr,port)
        mreq = make_mreq(sock.family, addr_info[4][0])

        # Join the group
        if sock.family == socket.AF_INET:
            # IPv4
            sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)

            # Allow multicast packets to get back on this host
            sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_LOOP, 1)
        else:
            # IPv6
            sock.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_JOIN_GROUP, mreq)

            # Allow multicast packets to get back on this host
            sock.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_MULTICAST_LOOP, 1)

    return sock, addr_info[4][0]


def close_multicast_socket(sock, address):
    """
    Cleans up the given multicast socket.
    Unregisters it of the multicast group.

    Parameters should be the result of create_multicast_socket

    :param sock: A multicast socket
    :param address: The multicast address used by the socket
    """
    if sock is None:
        return

    if address:
        # Prepare the mreq structure to join the group
        mreq = make_mreq(sock.family, address)

        # Quit group
        if sock.family == socket.AF_INET:
            # IPv4
            sock.setsockopt(socket.IPPROTO_IP, socket.IP_DROP_MEMBERSHIP, mreq)

        elif sock.family == socket.AF_INET6:
            # IPv6
            sock.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_LEAVE_GROUP, mreq)

    # Close the socket
    sock.close()

# ------------------------------------------------------------------------------


def make_heartbeat(port, path, peer_uid, node_uid, app_id):
    """
    Prepares the heart beat UDP packet

    Format : Little endian
    * Kind of beat (1 byte)
    * Herald HTTP server port (2 bytes)
    * Herald HTTP servlet path length (2 bytes)
    * Herald HTTP servlet path (variable, UTF-8)
    * Peer UID length (2 bytes)
    * Peer UID (variable, UTF-8)
    * Node UID length (2 bytes)
    * Node UID (variable, UTF-8)
    * Application ID length (2 bytes)
    * Application ID (variable, UTF-8)

    :param port: The port to access the Herald HTTP server
    :param path: The path to the Herald HTTP servlet
    :param peer_uid: The UID of the peer
    :param node_uid: The UID of the node
    :param app_id: Application ID
    :return: The heart beat packet content (byte array)
    """
    # Type and port...
    packet = struct.pack("<BBH", PACKET_FORMAT_VERSION, PACKET_TYPE_HEARTBEAT, port)
    for string in (path, peer_uid, node_uid, app_id):
        # Strings...
        string_bytes = to_bytes(string)
        packet += struct.pack("<H", len(string_bytes))
        packet += string_bytes

    return packet


def make_lastbeat(peer_uid, app_id):
    """
    Prepares the last beat UDP packet (when the peer is going away)

    Format : Little endian
    * Kind of beat (1 byte)
    * Peer UID length (2 bytes)
    * Peer UID (variable, UTF-8)
    * Application ID length (2 bytes)
    * Application ID (variable, UTF-8)

    :param peer_uid: Peer UID
    :param app_id: Application ID
    :return: The last beat packet content (byte array)
    """
    packet = struct.pack("<BB", PACKET_FORMAT_VERSION, PACKET_TYPE_LASTBEAT)
    for string in (peer_uid, app_id):
        string_bytes = to_bytes(string)
        packet += struct.pack("<H", len(string_bytes))
        packet += string_bytes

    return packet

# ------------------------------------------------------------------------------


class MulticastReceiver(object):
    """
    A multicast datagram receiver
    """
    def __init__(self, group, port, callback):
        """
        Sets up the receiver

        The given callback must have the following signature:
        ``callback(host, port, path, peer_uid)``.

        :param group: Multicast group to listen
        :param port: Multicast port
        :param callback: Method to call back once a packet is received
        """
        # Parameters
        self._group = group
        self._port = port
        self._callback = callback

        # Reception loop
        self._stop_event = threading.Event()
        self._thread = None

        # Socket
        self._socket = None

    def start(self):
        """
        Starts listening to the socket

        :return: True if the socket has been created
        """
        # Create the multicast socket (update the group)
        self._socket, self._group = create_multicast_socket(self._group,
                                                            self._port)

        # Start the listening thread
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self.__read,
            name="MulticastReceiver-{0}".format(self._port))
        self._thread.start()

    def stop(self):
        """
        Stops listening to the socket
        """
        # Stop the loop
        self._stop_event.set()

        # Join the thread
        self._thread.join()
        self._thread = None

        # Close the socket
        close_multicast_socket(self._socket, self._group)

    def _handle_heartbeat(self, sender, data):
        """
        Handles a raw heart beat

        :param sender: Sender (address, port) tuple
        :param data: Raw packet data
        """
        # Format of packet
        parsed, data = self._unpack("<B", data)
        format = parsed[0]
        if format == PACKET_FORMAT_VERSION:
            # Kind of beat
            parsed, data = self._unpack("<B", data)
            kind = parsed[0]
            if kind == PACKET_TYPE_HEARTBEAT:
                # Extract content
                parsed, data = self._unpack("<H", data)
                port = parsed[0]
                path, data = self._unpack_string(data)
                uid, data = self._unpack_string(data)
                node_uid, data = self._unpack_string(data)
                try:
                    app_id, data = self._unpack_string(data)
                except struct.error:
                    # Compatibility with previous version
                    app_id = herald.DEFAULT_APPLICATION_ID

            elif kind == PACKET_TYPE_LASTBEAT:
                # Peer is going away
                uid, data = self._unpack_string(data)
                app_id, data = self._unpack_string(data)
                port = -1
                path = None
                node_uid = None

            else:
                _logger.warning("Unknown kind of packet: %d", kind)
                return

            try:
                self._callback(kind, uid, node_uid, app_id, sender[0], port, path)
            except Exception as ex:
                _logger.exception("Error handling heart beat: %s", ex)

        #else:
            #_logger.warning("Unsupported packet format version: %d", format)


    def _unpack(self, fmt, data):
        """
        Calls struct.unpack().

        Returns a tuple containing the result tuple and the subset of data
        containing the unread content.

        :param fmt: The format of data
        :param data: Data to unpack
        :return: A tuple (result tuple, unread_data)
        """
        size = struct.calcsize(fmt)
        read, unread = data[:size], data[size:]
        return struct.unpack(fmt, read), unread

    def _unpack_string(self, data):
        """
        Unpacks the next string from the given data

        :param data: A datagram, starting at a string size
        :return: A (string, unread_data) tuple
        """
        # Get the size of the string
        result, data = self._unpack("<H", data)
        size = result[0]

        # Read it
        string_bytes = data[:size]

        # Convert it
        return to_unicode(string_bytes), data[size:]

    def __read(self):
        """
        Reads packets from the socket
        """
        # Set the socket as non-blocking
        self._socket.setblocking(0)

        while not self._stop_event.is_set():
            # Watch for content
            ready = select.select([self._socket], [], [], 1)
            if ready[0]:
                # Socket is ready
                data, sender = self._socket.recvfrom(1024)
                try:
                    self._handle_heartbeat(sender, data)
                except Exception as ex:
                    _logger.exception("Error handling the heart beat: %s", ex)

# ------------------------------------------------------------------------------


@ComponentFactory(FACTORY_DISCOVERY_MULTICAST)
@RequiresBest('_probe', herald.SERVICE_PROBE)
@Requires('_directory', herald.SERVICE_DIRECTORY)
@Requires('_receiver', SERVICE_HTTP_RECEIVER)
@Requires('_transport', SERVICE_HTTP_TRANSPORT)
@Property('_group', PROP_MULTICAST_GROUP, '239.0.0.1')
@Property('_port', PROP_MULTICAST_PORT, 42000)
@Property('_peer_ttl', 'peer.ttl', 30)
@Property('_discover_local_peers', PROP_DISCOVER_LOCAL_PEERS, True)
class MulticastHeartbeat(object):
    """
    Discovery of Herald peers based on multicast
    """
    def __init__(self):
        """
        Sets up the component
        """
        # Injected services
        self._directory = None
        self._receiver = None
        self._transport = None
        self._probe = None

        # Local peer bean
        self._local_peer = None

        # Properties
        self._group = "239.0.0.1"
        self._port = 42000
        self._peer_ttl = 30
        self._discover_local_peers = True

        # Multicast receiver
        self._multicast_recv = None

        # Multicast sender
        self._multicast_send = None
        self._multicast_target = None

        # Threads
        self._stop_event = threading.Event()
        self._lst_thread = None
        self._heart_thread = None

        # peer UID -> Last Time Seen
        self._peer_lst = {}
        self._lst_lock = threading.Lock()

    @Validate
    def _validate(self, _):
        """
        Component validated
        """
        self._port = int(self._port)
        self._peer_ttl = int(self._peer_ttl)
        self._local_peer = self._directory.get_local_peer()
        self._stop_event.clear()

        # Start the multicast listener
        self._multicast_recv = MulticastReceiver(self._group, self._port,
                                                 self.handle_heartbeat)
        self._multicast_recv.start()

        # Create the multicast sender socket
        self._multicast_send, address = create_multicast_socket(self._group,
                                                                self._port,
                                                                False)
        self._multicast_target = (address, self._port)

        # Start the heart & TTL threads
        self._heart_thread = threading.Thread(target=self.__heart_loop,
                                              name="Herald-HTTP-HeartBeat")
        self._lst_thread = threading.Thread(target=self.__lst_loop,
                                            name="Herald-HTTP-LST")
        self._heart_thread.start()
        self._lst_thread.start()

    @Invalidate
    def _invalidate(self, _):
        """
        Component invalidated
        """
        # Stop everything
        self._stop_event.set()
        self._multicast_recv.stop()
        self._multicast_recv = None

        # Wait for the threads to stop
        self._heart_thread.join(.5)
        self._lst_thread.join(.5)
        self._lst_thread = None

        # Send a last beat: "leaving"
        beat = make_lastbeat(self._local_peer.uid, self._local_peer.app_id)
        self._multicast_send.sendto(beat, 0, self._multicast_target)

        # Clear the multicast sender
        self._multicast_send.close()
        self._multicast_send = None
        self._multicast_target = None

        # Clear storage
        self._peer_lst.clear()

    def handle_heartbeat(self, kind, peer_uid, node_uid, app_id, host, port, path):
        """
        Handles a parsed heart beat

        :param kind: Kind of heart beat
        :param peer_uid: UID of the discovered peer
        :param node_uid: UID of the node of the peer
        :param app_id: Application ID of the discovered peer
        :param host: Address which sent the heart beat
        :param port: Port of the Herald HTTP server
        :param path: Path to the Herald HTTP servlet
        """
        if peer_uid == self._local_peer.uid \
                or app_id != self._local_peer.app_id:
            # Ignore this heart beat (sent by us or another application)
            return

        if kind == PACKET_TYPE_LASTBEAT:
            with self._lst_lock:
                try:
                    del self._peer_lst[peer_uid]
                except KeyError:
                    # We weren't aware of that peer
                    pass

            self._probe.store(
                PROBE_CHANNEL_MULTICAST,
                {"uid": peer_uid, "timestamp": time.time(),
                 "event": "lastbeat"})

            try:
                # Peer is going away
                peer = self._directory.get_peer(peer_uid)
                peer.unset_access(ACCESS_ID)
            except KeyError:
                # Unknown peer
                pass

        elif kind == PACKET_TYPE_HEARTBEAT:
            if not self._discover_local_peers:
                if node_uid == self._local_peer.node_uid:
                    # ignore peers located on the same node
                    return
            with self._lst_lock:
                # Update the peer LST
                self._peer_lst[peer_uid] = time.time()

            if peer_uid not in self._directory:
                # The peer isn't known, register it
                self._probe.store(
                    PROBE_CHANNEL_MULTICAST,
                    {"uid": peer_uid, "timestamp": time.time(),
                     "event": "discovered"})

                self.__discover_peer(host, port, path)

    def __discover_peer(self, host, port, path):
        """
        Grabs the description of a peer using the Herald servlet

        :param host: Address which sent the heart beat
        :param port: Port of the Herald HTTP server
        :param path: Path to the Herald HTTP servlet
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

    def __heart_loop(self):
        """
        Loop sending heart beats every 20 seconds
        """
        # Get local information
        access = self._receiver.get_access_info()

        # Prepare the packet
        beat = make_heartbeat(access[1], access[2], self._local_peer.uid,
                              self._local_peer.node_uid, self._local_peer.app_id)
        while not self._stop_event.is_set():
            try:
                # Send the heart beat using the multicast socket
                self._multicast_send.sendto(beat, 0, self._multicast_target)
            except Exception as ex:
                _logger.warn("Cannot send multicast discovery message! error: %s", ex)
            # Wait 20 seconds before next loop
            self._stop_event.wait(20)

    def __lst_loop(self):
        """
        Loop that validates the LST of all peers and removes those who took
        to long to respond
        """
        while not self._stop_event.is_set():
            with self._lst_lock:
                loop_start = time.time()
                to_delete = set()

                for uid, last_seen in self._peer_lst.items():
                    if not last_seen:
                        # No LST for this peer
                        _logger.debug("Invalid LST for %s", uid)

                    elif (loop_start - last_seen) > self._peer_ttl:
                        # TTL reached
                        to_delete.add(uid)
                        _logger.debug("Peer %s reached TTL.", uid)

                        self._probe.store(
                            PROBE_CHANNEL_MULTICAST,
                            {"uid": uid, "timestamp": time.time(),
                             "event": "timeout"})

                for uid in to_delete:
                    # Unregister those peers
                    del self._peer_lst[uid]
                    self._directory.unregister(uid)

            # Wait a second or the event before next loop
            self._stop_event.wait(1)