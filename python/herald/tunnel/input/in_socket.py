#!/usr/bin/python
# -- Content-Encoding: UTF-8 --
"""
Tunnel input: socket server

:author: Thomas Calmant
:copyright: Copyright 2015, isandlaTech
:license: Apache License 2.0
:version: 0.0.1
:status: Alpha

..

    Copyright 2015 isandlaTech

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
__version_info__ = (0, 0, 1)
__version__ = ".".join(str(x) for x in __version_info__)

# Documentation strings format
__docformat__ = "restructuredtext en"

# ------------------------------------------------------------------------------

# Herald
from herald.exceptions import HeraldException
import herald
import herald.beans as beans
import herald.tunnel as htunnel

# Pelix
from pelix.ipopo.decorators import ComponentFactory, Provides, Property, \
    Requires, Instantiate
from pelix.utilities import to_str

# Standard library
import base64
import logging
import socket
import select
import threading

# ------------------------------------------------------------------------------

logger = logging.getLogger(__name__)

BUFFER_SIZE = 4096
""" Read buffer size """

# ------------------------------------------------------------------------------


class SocketInputTCP(object):
    """
    Socket TCP entry side of the tunnel
    """
    def __init__(self, herald_svc, tunnel_uid, out_peer):
        """
        Sets up members

        :param herald_svc: The Herald core service
        """
        # The Herald core service
        self.__herald = herald_svc

        # The targeted peer
        self.__peer = out_peer

        # Tunnel UID
        self.__tunnel_uid = tunnel_uid

        # Server sockets
        self.__server_socks = []

        # Sockets to listen to (clients)
        self.__clients_socks = set()

        # Next link ID
        self.__next_id = 0

        # ID -> Socket
        self.__link_sock = {}

        # Socket -> ID
        self.__sock_link = {}

        # Thread safety (just in case...)
        self.__lock = threading.Lock()

        # Run flag
        self.__running = True

    def setup(self, address, port):
        """
        Setup the tunnel entry
        :param address: Binding address
        :param port: Binding port
        :raise socket.gaierror: Error getting server address info
        """
        # Get the possible server addresses and families
        # => can raise a socket.gaierror
        addr_info = socket.getaddrinfo(address, port, 0, socket.SOCK_STREAM)
        server_sockets = self.__server_socks

        for info in addr_info:
            # Unpack address info
            family, socktype, proto, _, sockaddr = info

            try:
                # Create and bind socket
                sock = socket.socket(family, socktype, proto)
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                sock.bind(sockaddr)
                sock.listen(10)
            except socket.error as ex:
                logger.error("Error creating socket: %s", ex)
            else:
                # Socket has been bound correctly
                server_sockets.append(sock)

        if not server_sockets:
            raise socket.error("No server socket have been bound")
        return True

    def start(self):
        """
        Starts the tunnel
        """
        thread = threading.Thread(target=self.read_loop,
                                  name="Herald-Tunnel-SocketTCPInput")
        thread.daemon = True
        thread.start()

    def close(self, send_close=True):
        """
        Close all the sockets and cleans up references.

        :param send_close: Sends the close message to the remote peer
        """
        self.__running = False

        # Close server sockets
        for sock in self.__server_socks:
            try:
                sock.shutdown(socket.SHUT_RDWR)
            except IOError:
                pass
            finally:
                sock.close()
        del self.__server_socks[:]

        # Close client sockets
        for sock in list(self.__clients_socks):
            self._on_close(sock)
        self.__clients_socks.clear()

        if send_close and self.__peer is not None:
            msg = beans.Message(htunnel.SUBJECT_CLOSE_OUTPUT_TUNNEL,
                                {"tunnel": self.__tunnel_uid})
            self.__herald.fire(self.__peer, msg)

        # Clean up
        self.__tunnel_uid = None
        self.__peer = None

    def send(self, link_id, data):
        """
        Write data back to the client

        :param link_id: ID of the link
        :param data: Base64 encoded data
        """
        try:
            sock = self.__link_sock[link_id]
        except KeyError:
            logger.error("No socket associated to link %s", link_id)
        else:
            sock.send(base64.b64decode(data))

    def read_loop(self):
        """
        Main read loop
        """
        while self.__running:
            self.read_once()

    def read_once(self):
        """
        Read step
        """
        # List of the sockets to read
        with self.__lock:
            read_socks = self.__server_socks[:]
            read_socks.extend(self.__clients_socks)

        # Wait for data
        input_ready, _, _ = select.select(read_socks, [], [], 1.0)

        for in_sock in input_ready:
            if in_sock in self.__server_socks:
                self._on_accept(in_sock)
            else:
                try:
                    data = in_sock.recv(BUFFER_SIZE)
                except socket.error as ex:
                    logger.error("Error reading socket: %s", ex)
                    self._on_close(in_sock)
                else:
                    if not data:
                        self._on_close(in_sock)
                    else:
                        self._on_recv(in_sock, data)

    def _on_accept(self, server_sock):
        """
        Accepts a client from a server socket

        :param server_sock: Socket server waiting to accept a client
        """
        try:
            # Accept client
            clt_sock, clt_addr = server_sock.accept()
        except IOError as ex:
            logger.error("Error accepting client: %s", ex)
            return

        with self.__lock:
            # Get next ID
            link_id = self.__next_id
            self.__next_id += 1

        # Create link on remote peer
        msg = beans.Message(htunnel.SUBJECT_CREATE_OUTPUT_LINK,
                            {"tunnel": self.__tunnel_uid, "link_id": link_id})
        try:
            recv_msg = self.__herald.send(self.__peer, msg)
            result = recv_msg.content

            # Close socket on remote error
            if not result['success']:
                logger.error("Error creating remote link: %s",
                             result['message'])
                try:
                    clt_sock.shutdown(socket.SHUT_RDWR)
                except IOError:
                    pass
                finally:
                    clt_sock.close()
                return
        except HeraldException as ex:
            # Close socket on error
            logger.error("Error creating remote link: %s", ex)
            try:
                clt_sock.shutdown(socket.SHUT_RDWR)
            except IOError:
                pass
            else:
                clt_sock.close()
            return

        with self.__lock:
            # Keep track of the client
            self.__link_sock[link_id] = clt_sock
            self.__sock_link[clt_sock] = link_id

            # Listen to the client socket
            self.__clients_socks.add(clt_sock)

    def _on_close(self, clt_sock):
        """
        A client socket must be or has been closed

        :param clt_sock: The client socket
        """
        with self.__lock:
            try:
                # Remove socket from the listened ones
                self.__clients_socks.remove(clt_sock)
            except KeyError:
                # Unknown socket: ignore
                return

            # Remove it from dictionaries
            link_id = self.__sock_link.pop(clt_sock)
            del self.__link_sock[link_id]

        # Close the socket
        try:
            clt_sock.shutdown(socket.SHUT_RDWR)
        except IOError:
            pass
        finally:
            clt_sock.close()

        # Close link in the remote peer
        msg = beans.Message(htunnel.SUBJECT_CLOSE_OUTPUT_LINK,
                            {"tunnel": self.__tunnel_uid, "link_id": link_id})
        try:
            self.__herald.fire(self.__peer, msg)
        except HeraldException as ex:
            logger.error("Error closing link: %s", ex)

    def _on_recv(self, clt_sock, data):
        """
        Some data have been read from a client socket

        :param clt_sock: Client socket
        :param data: Data read from client
        """
        try:
            link_id = self.__sock_link[clt_sock]
        except KeyError:
            # Unknown client socket
            logger.warning("Unknown client socket")
        else:
            msg = beans.Message(
                htunnel.SUBJECT_DATA_FROM_INPUT,
                {"tunnel": self.__tunnel_uid, "link_id": link_id,
                 "data": to_str(base64.b64encode(data))})
            try:
                # Send data to the remote peer
                self.__herald.fire(self.__peer, msg)
            except HeraldException as ex:
                logger.error("Error sending data back to link: %s", ex)

# ------------------------------------------------------------------------------


class SocketInputUDP(object):
    """
    Socket UDP entry of a tunnel
    """
    def __init__(self, herald_svc, tunnel_uid, out_peer):
        """
        Sets up members

        :param herald_svc: The Herald core service
        """
        # The Herald core service
        self.__herald = herald_svc

        # The targeted peer
        self.__peer = out_peer

        # Tunnel UID
        self.__tunnel_uid = tunnel_uid

        # Server sockets
        self.__server_socks = []

        # Thread safety (just in case...)
        self.__lock = threading.Lock()

        # Run flag
        self.__running = True

    def setup(self, address, port):
        """
        Setup the tunnel entry
        :param address: Binding address
        :param port: Binding port
        :raise socket.gaierror: Error getting server address info
        """
        # Get the possible server addresses and families
        # => can raise a socket.gaierror
        addr_info = socket.getaddrinfo(address, port, 0, socket.SOCK_DGRAM)
        server_sockets = self.__server_socks

        for info in addr_info:
            # Unpack address info
            family, socktype, proto, _, sockaddr = info

            try:
                # Create and bind socket
                sock = socket.socket(family, socktype, proto)
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                sock.bind(sockaddr)
            except socket.error as ex:
                logger.error("Error creating socket: %s", ex)
            else:
                # Socket has been bound correctly
                server_sockets.append(sock)

        if not server_sockets:
            raise socket.error("No server socket have been bound")
        return True

    def start(self):
        """
        Starts the tunnel
        """
        thread = threading.Thread(target=self.read_loop,
                                  name="Herald-Tunnel-SocketUDPInput")
        thread.daemon = True
        thread.start()

    def close(self, send_close=True):
        """
        Close all the sockets and cleans up references.

        :param send_close: Sends the close message to the remote peer
        """
        self.__running = False

        # Close server sockets
        for sock in self.__server_socks:
            try:
                sock.shutdown(socket.SHUT_RDWR)
            except IOError:
                pass
            finally:
                sock.close()
        del self.__server_socks[:]

        if send_close and self.__peer is not None:
            msg = beans.Message(htunnel.SUBJECT_CLOSE_OUTPUT_TUNNEL,
                                {"tunnel": self.__tunnel_uid})
            self.__herald.fire(self.__peer, msg)

        # Clean up
        self.__tunnel_uid = None
        self.__peer = None

    @staticmethod
    def _make_link_id(server_idx, clt_addr):
        """
        Generates a link ID string containing the server index and the client
        address

        :param server_idx: Index of the server
        :param clt_addr: Address and port of the client (tuple)
        :return: An ID string
        """
        return "{0};{1};{2}".format(server_idx, clt_addr[0], clt_addr[1])

    @staticmethod
    def _parse_link_id(link_id):
        """
        Returns the index of the server to use and the client address and port
        to send a reply to, according to the link ID

        :param link_id: A link ID
        :return: A tuple: (server_idx, (client host, client port))
        :raise ValueError: Invalid link ID format
        """
        values = link_id.split(";")
        try:
            return values[0], (values[1], int(values[2]))
        except IndexError:
            raise ValueError("Invalid link ID: not enough fields")
        except TypeError:
            raise ValueError("Invalid port number in link ID")

    def send(self, link_id, data):
        """
        Write data back to the client

        :param link_id: ID of the link
        :param data: Base64 encoded data
        """
        srv_idx, clt_addr = self._parse_link_id(link_id)
        try:
            self.__server_socks[srv_idx] \
                .sendto(base64.b64decode(data), clt_addr)
        except KeyError:
            logger.error("Unknown UDP server index: %s", srv_idx)
        except socket.error as ex:
            logger.exception("Error sending packet back to client: %s", ex)

    def read_loop(self):
        """
        Main read loop
        """
        while self.__running:
            self.read_once()

    def read_once(self):
        """
        Read step
        """
        # List of the sockets to read
        with self.__lock:
            read_socks = self.__server_socks[:]

        # Wait for data
        input_ready, _, _ = select.select(read_socks, [], [], 1.0)

        for in_sock in input_ready:
            try:
                # Read data and get client address
                data, clt_addr = in_sock.recvfrom(BUFFER_SIZE)
            except socket.error as ex:
                logger.error("Error reading socket: %s", ex)
            else:
                try:
                    srv_idx = read_socks.index(in_sock)
                except ValueError:
                    logger.error("Invalid UDP server socket: %s", in_sock)
                else:
                    self._on_recv(srv_idx, clt_addr, data)

    def _on_recv(self, srv_idx, clt_addr, data):
        """
        Some data have been read from a client socket

        :param srv_idx: Server position in the servers list
        :param clt_sock: Address of the client
        :param data: Data read from client
        """
        msg = beans.Message(
            htunnel.SUBJECT_DATA_FROM_INPUT,
            {"tunnel": self.__tunnel_uid,
             "link_id": self._make_link_id(srv_idx, clt_addr),
             "data": to_str(base64.b64encode(data))})
        try:
            # Send data to the remote peer
            self.__herald.fire(self.__peer, msg)
        except HeraldException as ex:
            logger.error("Error sending data back to link: %s", ex)

# ------------------------------------------------------------------------------


@ComponentFactory('herald-tunnel-input-socket-factory')
@Requires('_herald', herald.SERVICE_HERALD)
@Provides(htunnel.SERVICE_TUNNEL_INPUT_CREATOR)
@Property('_kind', 'kind', 'socket')
@Instantiate('herald-tunnel-input-socket')
class SocketTunnelInputHandler(object):
    """
    Creates socket TCP tunnel output
    """
    def __init__(self):
        """
        Sets up members
        """
        self._herald = None
        self._kind = 'socket'

    def create_tunnel(self, tunnel_uid, in_config, out_peer):
        """
        Creates a tunnel

        :param tunnel_uid: ID of the tunnel
        :param in_config: Input configuration bean
        :param out_peer: Output peer
        :return: The configured tunnel
        """
        sock_type = in_config.sock_type

        if sock_type == socket.SOCK_STREAM:
            tunnel = SocketInputTCP(self._herald, tunnel_uid, out_peer)
        elif sock_type == socket.SOCK_DGRAM:
            tunnel = SocketInputUDP(self._herald, tunnel_uid, out_peer)
        else:
            raise ValueError("Unhandled kind of socket: %s", sock_type)

        tunnel.setup(in_config.address, in_config.port)
        return tunnel
