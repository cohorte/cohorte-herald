#!/usr/bin/python
# -- Content-Encoding: UTF-8 --
"""
Tunnel input manager

:author: Thomas Calmant
:copyright: Copyright 2015, isandlaTech
:license: Apache License 2.0
:version: 0.0.4
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
__version_info__ = (0, 0, 4)
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
from pelix.ipopo.decorators import ComponentFactory, Requires, Provides, \
    Property, RequiresMap, Instantiate, Invalidate

# Standard library
import logging
import uuid

# ------------------------------------------------------------------------------

logger = logging.getLogger(__name__)

# ------------------------------------------------------------------------------


@ComponentFactory('herald-tunnel-input-factory')
@Provides((htunnel.SERVICE_TUNNEL, herald.SERVICE_LISTENER,
           herald.SERVICE_DIRECTORY_LISTENER))
@Requires('_directory', herald.SERVICE_DIRECTORY)
@Requires('_herald', herald.SERVICE_HERALD)
@RequiresMap('_tunnel_creator', htunnel.SERVICE_TUNNEL_INPUT_CREATOR,
             'kind', optional=True)
@Property('_filters', herald.PROP_FILTERS, [htunnel.MATCH_INPUT_SUBJECTS])
@Instantiate('herald-tunnel-input')
class HeraldTunnelInput(object):
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

    @Invalidate
    def invalidate(self, _):
        """
        Component invalidate
        """
        # Close the end of the tunnels
        for tunnel_uid in list(self.__in_tunnels.keys()):
            self.close_tunnel(tunnel_uid)

    def herald_message(self, herald_svc, message):
        """
        An Herald message has been received
        """
        subject = message.subject
        content = message.content
        result = None

        if subject == htunnel.SUBJECT_DATA_FROM_OUTPUT:
            self.__in_tunnels[content['tunnel']].send(
                content['link_id'], content['data'])
        elif subject == htunnel.SUBJECT_CLOSE_INPUT_LINK:
            self.__in_tunnels[content['tunnel']].close(content['link_id'])
        elif subject == htunnel.SUBJECT_CLOSE_INPUT_TUNNEL:
            self.close_tunnel(content['tunnel'])
        else:
            result = {"success": False,
                      "message": "Unknown command: {0}".format(subject)}

        if result:
            herald_svc.reply(message, result)

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

        # Create tunnel entry side
        try:
            tunnel_in = self._tunnel_creator[in_config.kind] \
                .create_tunnel(tunnel_uid, in_config, out_peer)
        except KeyError:
            logger.error("Unknown kind of tunnel input: %s", in_config.kind)
            return

        try:
            # Create tunnel output side
            message = beans.Message(
                htunnel.SUBJECT_CREATE_OUTPUT_TUNNEL,
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

        # Store the tunnel
        self.__in_tunnels[tunnel_uid] = tunnel_in
        self.__in_configs[tunnel_uid] = (in_config, out_peer, out_config)

        # Start the tunnel
        tunnel_in.start()

        logger.info("Opened input tunnel: %s", tunnel_uid)
        return tunnel_uid

    def close_tunnel(self, tunnel_uid):
        """
        Closes the tunnel

        :param tunnel_uid: UID of the tunnel to close
        """
        # Close the whole tunnel
        del self.__in_configs[tunnel_uid]
        tunnel_in = self.__in_tunnels.pop(tunnel_uid)
        tunnel_in.close(True)
        logger.info("Closed input tunnel: %s", tunnel_uid)

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

    @staticmethod
    def peer_registered(peer):
        """
        A new peer has been registered in Herald: send it a contact information
        """
        pass

    @staticmethod
    def peer_updated(peer, access_id, data, previous):
        """
        An access to a peer have been updated: ignore
        """
        pass

    def peer_unregistered(self, peer):
        """
        All accesses to a peer have been lost: forget about it

        :param peer: The lost peer
        """
        # Close tunnel, without notifying the output part (as it disappeared)
        to_close = [uid for uid, config in self.__in_configs.items()
                    if config[1] == peer.uid]

        if to_close:
            logger.info("Closing input tunnels to the unregistration of "
                        "%s: %s", peer, ', '.join(to_close))

            # Close tunnels
            for tunnel_uid in to_close:
                try:
                    del self.__in_configs[tunnel_uid]
                    tunnel_in = self.__in_tunnels.pop(tunnel_uid)
                    tunnel_in.close(False)
                except KeyError:
                    # Maybe we got a late closing message
                    pass
