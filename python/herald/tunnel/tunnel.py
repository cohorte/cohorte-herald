#!/usr/bin/python
# -- Content-Encoding: UTF-8 --
"""
Tunnel service implementation

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
import herald.tunnel
import herald.beans as beans

from .server import SocketTunnelIn

# Pelix
from pelix.ipopo.decorators import ComponentFactory, Requires, Provides, \
    Property, RequiresMap, Instantiate, Invalidate

# Standard library
import base64
import binascii
import logging
import threading
import uuid

# ------------------------------------------------------------------------------

logger = logging.getLogger(__name__)

SUBJECT_CREATE_TUNNEL = "herald/tunnel/create_tunnel"

# ------------------------------------------------------------------------------


@ComponentFactory('herald-tunnel-factory')
@Provides((herald.tunnel.SERVICE_TUNNEL, herald.SERVICE_LISTENER))
@Requires('_directory', herald.SERVICE_DIRECTORY)
@Requires('_herald', herald.SERVICE_HERALD)
@RequiresMap('_tunnel_creator', herald.tunnel.SERVICE_TUNNEL_CREATOR, 'kind',
             optional=True)
@Property('_filters', herald.PROP_FILTERS, ['herald/tunnel/*'])
@Instantiate('herald-tunnel')
class HeraldTunnel(object):
    """
    Implementation of the tunnels provider
    """
    def __init__(self):
        """
        Sets up members
        """
        # Injected services
        self._directory = None
        self._herald = None
        self._tunnel_creator = None

        # Active input tunnels (UID -> Tunnel)
        self.__in_tunnels = {}

        # Configuration of input tunnels
        # (UID -> (in_config, out_peer, out_config)
        self.__in_configs = {}

        # Active output tunnel (UID -> TunnelOut)
        self.__out_tunnels = {}

        # Configuration of output tunnels (UID -> in_peer, out_config)
        self.__out_configs = {}

    @Invalidate
    def invalidate(self, _):
        """
        Component invalidate
        """
        # Close input tunnels
        for tunnel_uid in list(self.__in_tunnels.keys()):
            self.close_tunnel(tunnel_uid)

        # Notify the remote tunnels
        for tunnel in list(self.__out_tunnels.values()):
            msg = beans.Message("herald/tunnel/close_tunnel",
                                {'tunnel': tunnel.tunnel_uid})
            self._herald.fire(tunnel.peer, msg)

    def herald_message(self, herald_svc, message):
        """
        An Herald message has been received
        """
        action = message.subject.split('/')[-1]
        content = message.content
        result = None

        if action == "create_tunnel":
            result = self._create_tunnel(content['tunnel'], message.sender,
                                         content['out_config'])
        elif action == "close_tunnel":
            self._close_tunnel(content['tunnel'])
        elif action == "create_link":
            result = self._create_link(content['tunnel'], content['link_id'])
        elif action == "close_link":
            result = self._close_link(content['tunnel'], content['link_id'])
        elif action == "data":
            self._handle_data(content['tunnel'], content['link_id'],
                              content['data'])
        elif action == "close-end":
            self.__in_tunnels[content['tunnel']].close(content['link_id'])
        elif action == "data-end":
            self.__in_tunnels[content['tunnel']].send(
                content['link_id'], content['data'])
        elif action == "close_tunnel-end":
            self.close_tunnel(content['tunnel'])
        else:
            result = {"success": False,
                      "message": "Unknown command: {0}".format(action)}

        if result:
            herald_svc.reply(message, result)

    def _create_tunnel(self, tunnel_uid, sender, out_config):
        """
        Creates the end of a tunnel

        :param tunnel_uid: ID of the tunnel
        :param sender: UID of the sender peer
        :param out_config: Configuration of this end
        :return: Result dictionary
        """
        try:
            kind = out_config['kind']
        except KeyError:
            return {"success": False,
                    "message": "No kind of tunnel given"}

        try:
            tunnel_out = self._tunnel_creator[kind] \
                .create_tunnel(tunnel_uid, sender, out_config)
            tunnel_out.start()
        except KeyError as ex:
            return {"success": False,
                    "message": "Unknown kind of tunnel: {0}".format(ex)}
        except Exception as ex:
            return {"success": False,
                    "message": "Error creating tunnel: {0}".format(ex)}
        else:
            self.__out_tunnels[tunnel_uid] = tunnel_out
            self.__out_configs[tunnel_uid] = (sender, tunnel_out.configuration)
            return {"success": True, "message": ""}

    def _close_tunnel(self, tunnel_uid):
        """
        Closes the tunnel with the given ID

        :param tunnel_uid: ID of the tunnel
        """
        try:
            out_tunnel = self.__out_tunnels.pop(tunnel_uid)
            del self.__out_configs[tunnel_uid]
            out_tunnel.close()
        except Exception as ex:
            logger.exception("Error closing tunnel: %s", ex)

    def _create_link(self, tunnel_uid, link_id):
        """
        Creates a new connection

        :param tunnel_uid: ID of the tunnel
        :param link_id: ID of the link
        :return: Result dictionary
        """
        try:
            out_tunnel = self.__out_tunnels[tunnel_uid]
            out_tunnel.create_link(link_id)
        except KeyError:
            return {"success": False,
                    "message": "Unknown tunnel: {0}".format(tunnel_uid)}
        except Exception as ex:
            return {"success": False,
                    "message": "Error creating link: {0}".format(ex)}
        else:
            return {"success": True, "message": ""}

    def _close_link(self, tunnel_uid, link_id):
        """
        Closes a new connection

        :param tunnel_uid: ID of the tunnel
        :param link_id: ID of the link
        :return: Result dictionary
        """
        try:
            out_tunnel = self.__out_tunnels[tunnel_uid]
            out_tunnel.close_link(link_id)
        except KeyError:
            return {"success": False,
                    "message": "Unknown tunnel: {0}".format(tunnel_uid)}
        except Exception as ex:
            return {"success": False,
                    "message": "Error closing link: {0}".format(ex)}
        else:
            return {"success": True, "message": ""}

    def _handle_data(self, tunnel_id, link_id, msg_data):
        """
        Sends data through the link

        :param tunnel_id: ID of the tunnel
        :param link_id: ID of the link
        :param msg_data: Data, encoded in Base64
        :return: None
        """
        try:
            out_tunnel = self.__out_tunnels[tunnel_id]
            data = base64.b64decode(msg_data)
            out_tunnel.send(link_id, data)
        except KeyError:
            return {"success": False,
                    "message": "Unknown tunnel: {0}".format(tunnel_id)}
        except binascii.Error as ex:
            return {"success": False,
                    "message": "Invalid data: {0}".format(ex)}
        except Exception as ex:
            return {"success": False,
                    "message": "Error closing link: {0}".format(ex)}
        else:
            return {"success": True, "message": ""}

    def open_tunnel(self, in_config, out_peer, out_config):
        """
        Opens a tunnel to join the remote peer

        :param in_config: Tunnel input configuration
        :param out_peer: Output peer UID
        :param out_config: Tunnel output configuration
        :return: The UID of the tunnel or None
        """
        # Generate tunnel UID
        tunnel_uid = str(uuid.uuid4()).replace('-', '').upper()

        logger.info("Opening input tunnel %s...", tunnel_uid)

        # Create tunnel entry side
        tunnel_in = SocketTunnelIn(self._herald)
        tunnel_in.setup(in_config.address, in_config.port, in_config.sock_type)

        try:
            # Create tunnel output side
            message = beans.Message(
                SUBJECT_CREATE_TUNNEL,
                {"tunnel": tunnel_uid, "out_config": out_config.to_map()})

            recv_msg = self._herald.send(out_peer, message)
            result = recv_msg.content
            if not result["success"]:
                logger.error("Error on remote side: %s", result["message"])
                tunnel_in.close(False)
                return
        except HeraldException as ex:
            logger.error("Error contacting the remote peer: %s", ex)
            tunnel_in.close(False)
            return

        # Link tunnel_in to the output side
        tunnel_in.link(tunnel_uid, out_peer)

        # Store the tunnel
        self.__in_tunnels[tunnel_uid] = tunnel_in
        self.__in_configs[tunnel_uid] = (in_config, out_peer, out_config)

        # Start the tunnel
        thread = threading.Thread(target=tunnel_in.read_loop,
                                  name="Herald-Tunnel")
        thread.daemon = True
        thread.start()

        logger.info("Opened input tunnel: %s", tunnel_uid)
        return tunnel_uid

    def close_tunnel(self, tunnel_uid):
        """
        Closes the tunnel

        :param tunnel_uid: UID of the tunnel to close
        """
        # Close the whole tunnel
        tunnel_in = self.__in_tunnels.pop(tunnel_uid)
        tunnel_in.close(True)
        del self.__in_configs[tunnel_uid]
        logger.info("Closing input tunnel: %s", tunnel_uid)

    def get_input_info(self, tunnel_uid=None):
        """
        Get the list of input tunnel descriptions

        :param tunnel_uid: UID filter
        :return: A list of (uid, in_config, out_peer, out_config)
        :raise KeyError: Unknown UID
        """
        if tunnel_uid:
            return tunnel_uid, self.__in_configs[tunnel_uid]
        else:
            return tuple([uid] + list(values)
                         for uid, values in self.__in_configs.items())

    def get_output_info(self):
        """
        Get the list of output tunnel descriptions

        :return: A list of (uid, in_peer, out_config)
        """
        return tuple([uid] + list(values)
                     for uid, values in self.__out_configs.items())
