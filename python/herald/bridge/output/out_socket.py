#!/usr/bin/python
# -- Content-Encoding: UTF-8 --
"""
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

# Standard library
import logging
import select
import socket
import threading
import time

# ------------------------------------------------------------------------------

# Module version
__version_info__ = (0, 0, 1)
__version__ = ".".join(str(x) for x in __version_info__)

# Documentation strings format
__docformat__ = "restructuredtext en"

# ------------------------------------------------------------------------------

logger = logging.getLogger(__name__)

BUFFER_SIZE = 4096
""" Read buffer size """

# ------------------------------------------------------------------------------


class BridgeOutSocketTCP(object):
    """
    Bridge TCP socket output
    """
    def __init__(self):
        """
        Sets up members
        """
        # Bridge input
        self.__bridge_in = None

        # Output address
        self.__output_address = None
        self.__sock_family = None
        self.__sock_type = None

        # Stop event
        self.__stop_event = threading.Event()

        # Link ID -> socket
        self.__links = {}

        # Socket -> Link ID
        self.__sockets = {}

    def bind_bridge_input(self, bridge_in):
        """
        Sets bridge input
        """
        self.__bridge_in = bridge_in

    def setup(self, address, port):
        """
        Configure the client socket
        """
        # Compute target address information
        addr_info = socket.getaddrinfo(address, port, 0, socket.SOCK_STREAM)
        info = addr_info[0]

        self.__sock_family = info[0]
        self.__sock_type = info[1]
        self.__output_address = info[4]

    def create_link(self, link_id):
        """
        Creates a socket

        :param link_id: ID of the link
        :raise socket.error: Error creating the socket
        """
        # Create socket and connect
        sock = socket.socket(self.__sock_family, self.__sock_type)
        sock.connect(self.__output_address)

        logger.debug("TCP Socket -> %s (%s)", self.__output_address, link_id)

        # Store socket
        self.__links[link_id] = sock
        self.__sockets[sock] = link_id

    def close_link(self, link_id):
        """
        Closes a socket

        :raise KeyError: Unknown link
        """
        logger.debug("Closing TCP Socket link /> %s", link_id)
        try:
            sock = self.__links.pop(link_id)
            del self.__sockets[sock]
        except KeyError:
            logger.debug("Unknown link ID")
        else:
            try:
                sock.shutdown(socket.SHUT_RDWR)
            except IOError:
                pass
            finally:
                sock.close()

    def start(self):
        """
        Starts the tunnel
        """
        thread = threading.Thread(target=self.read_loop,
                                  name="Herald-Bridge-SocketTCPOutput")
        thread.daemon = True
        thread.start()

    def close(self):
        """
        Close the tunnel
        """
        # Stop event
        self.__stop_event.set()

        # Notify the input
        for link_id in list(self.__links):
            self.__bridge_in.link_closed(link_id)

        # Close all sockets
        for sock in list(self.__sockets):
            try:
                sock.shutdown(socket.SHUT_RDWR)
            except IOError:
                pass
            finally:
                sock.close()

        self.__links.clear()
        self.__sockets.clear()

    def send(self, link_id, data):
        """
        Send data over the socket

        :param link_id: ID of the link
        :param data: Data to send (bytes)
        :raise KeyError: Unknown link ID
        """
        try:
            sock = self.__links[link_id]
            sock.send(data)
        except socket.error as ex:
            logger.exception("Error writing to socket: %s", ex)

    def read_loop(self):
        """
        Reading loop
        """
        while not self.__stop_event.is_set():
            self.__read_once()

    def __read_once(self):
        """
        Reads one frame from serial input
        """
        # Wait for data
        read_socks = list(self.__links.values())
        if not read_socks:
            time.sleep(.01)
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
        A socket has been closed
        """
        # Notify the bridge
        self.__bridge_in.link_closed(link_id)

        # Clean up
        clt_sock = self.__links.pop(link_id)
        del self.__sockets[clt_sock]

    def _on_recv(self, link_id, data):
        """
        Some data has been received
        """
        self.__bridge_in.link_data(link_id, data)
