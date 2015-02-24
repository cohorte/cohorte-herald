#!/usr/bin/python
# -- Content-Encoding: UTF-8 --
"""
Tunnel output: client socket

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
from herald.tunnel.config import OutputSocketConfiguration
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
import select
import socket
import threading
import time

# ------------------------------------------------------------------------------

BUFFER_SIZE = 4096

logger = logging.getLogger(__name__)

# ------------------------------------------------------------------------------


class SocketOutputTunnel(object):
    """
    Handles socket at the end of the tunnel
    """
    def __init__(self, herald_svc, in_peer, tunnel_uid, configuration):
        """
        Sets up the tunnel

        :param herald_svc: The Herald core service
        :param in_peer: Tunnel source peer
        :param tunnel_uid: ID of the tunnel
        :param configuration: Tunnel configuration bean
        """
        self.__herald = herald_svc
        self.__peer = in_peer
        self.__tunnel_uid = tunnel_uid
        self.__config = configuration

        # Stop event
        self.__stop_event = threading.Event()

        # Link ID -> socket
        self.__links = {}

        # Socket -> Link ID
        self.__sockets = {}

    @property
    def configuration(self):
        """
        The configuration of the tunnel
        """
        return self.__config

    @property
    def peer(self):
        """
        The targeted peer
        """
        return self.__peer

    @property
    def tunnel_uid(self):
        """
        Tunnel UID
        """
        return self.__tunnel_uid

    def start(self):
        """
        Starts the tunnel
        """
        thread = threading.Thread(target=self.__read_loop,
                                  name="Herald-Tunnel-Socket-Output")
        thread.daemon = True
        thread.start()

    def __read_loop(self):
        """
        Main read loop
        """
        while not self.__stop_event.is_set():
            self.__read_once()

    def __read_once(self):
        """
        Read loop step
        """
        # Wait for data
        read_socks = list(self.__links.values())
        if not read_socks:
            time.sleep(.1)
            return

        input_ready, _, _ = select.select(read_socks, [], [], .5)
        for in_sock in input_ready:
            try:
                link_id = self.__sockets[in_sock]
            except KeyError:
                # Socket has been removed from the list of sockets
                pass
            else:
                try:
                    data = in_sock.recv(BUFFER_SIZE)
                except socket.error:
                    self._on_close(link_id)
                else:
                    if not data:
                        self._on_close(link_id)
                    else:
                        self._on_recv(link_id, data)

    def _on_close(self, link_id):
        """
        A socket has been closed: send message
        """
        msg = beans.Message(htunnel.SUBJECT_CLOSE_INPUT_LINK,
                            {"tunnel": self.__tunnel_uid, "link_id": link_id})
        self.__herald.fire(self.__peer, msg)

    def _on_recv(self, link_id, data):
        """
        A socket has been closed: send message
        """
        msg = beans.Message(htunnel.SUBJECT_DATA_FROM_OUTPUT,
                            {"tunnel": self.__tunnel_uid, "link_id": link_id,
                             "data": to_str(base64.b64encode(data))})
        self.__herald.fire(self.__peer, msg)

    def create_link(self, link_id):
        """
        Creates a socket

        :param link_id: ID of the link
        :raise socket.error: Error creating the socket
        """
        # Create socket and connect
        sock = socket.socket(self.__config.sock_family,
                             self.__config.sock_type)
        sock.connect((self.__config.address, self.__config.port))

        # Store socket
        self.__links[link_id] = sock
        self.__sockets[sock] = link_id

    def close_link(self, link_id):
        """
        Closes a socket

        :raise KeyError: Unknown link
        """
        sock = self.__links.pop(link_id)
        del self.__sockets[sock]
        try:
            sock.shutdown(socket.SHUT_RDWR)
        except IOError:
            pass
        finally:
            sock.close()

    def send(self, link_id, data):
        """
        Sends data through a link
        """
        sock = self.__links[link_id]
        sock.send(data)

    def close(self):
        """
        Close the tunnel
        """
        # Stop event
        self.__stop_event.set()

        # Close all sockets
        for sock in list(self.__links):
            try:
                sock.shutdown(socket.SHUT_RDWR)
            except IOError:
                pass
            finally:
                sock.close()

        self.__links.clear()
        self.__sockets.clear()

# ------------------------------------------------------------------------------


@ComponentFactory('herald-tunnel-output-socket-factory')
@Requires('_herald', herald.SERVICE_HERALD)
@Provides(htunnel.SERVICE_TUNNEL_OUTPUT_CREATOR)
@Property('_kind', 'kind', 'socket')
@Instantiate('herald-tunnel-output-socket')
class SocketTunnelOutputHandler(object):
    """
    Creates socket tunnel output
    """
    def __init__(self):
        """
        Sets up members
        """
        self._herald = None
        self._kind = 'socket'

    def create_tunnel(self, tunnel_uid, in_peer, out_config):
        """
        Creates a tunnel

        :param tunnel_uid: ID of the tunnel
        :param in_peer: Tunnel source peer
        :param out_config: Output configuration dictionary
        :return: The configured tunnel
        """
        return SocketOutputTunnel(self._herald, in_peer, tunnel_uid,
                                  self._parse(out_config))

    @staticmethod
    def _parse(out_config):
        """
        Converts the given configuration dictionary to a bean

        :param out_config: Configuration dictionary
        :return: Configuration bean
        """
        return OutputSocketConfiguration(
            out_config['address'], out_config['port'], out_config['sock_type'])
