#!/usr/bin/python
# -- Content-Encoding: UTF-8 --
"""
Tunnel output manager

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
from pelix.ipopo.decorators import ComponentFactory, Requires, Provides, \
    Property, RequiresMap, Instantiate, Invalidate

# Standard library
import base64
import binascii
import logging

# ------------------------------------------------------------------------------

logger = logging.getLogger(__name__)

# ------------------------------------------------------------------------------


@ComponentFactory('herald-tunnel-output-factory')
@Provides((htunnel.SERVICE_TUNNEL_OUTPUT, herald.SERVICE_LISTENER))
@Requires('_directory', herald.SERVICE_DIRECTORY)
@Requires('_herald', herald.SERVICE_HERALD)
@RequiresMap('_tunnel_creator', htunnel.SERVICE_TUNNEL_OUTPUT_CREATOR,
             'kind', optional=True)
@Property('_filters', herald.PROP_FILTERS, [htunnel.MATCH_OUTPUT_SUBJECTS])
@Instantiate('herald-tunnel-output')
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

        # Active output tunnel (UID -> TunnelOut)
        self.__out_tunnels = {}

        # Configuration of output tunnels (UID -> in_peer, out_config)
        self.__out_configs = {}

    @Invalidate
    def invalidate(self, _):
        """
        Component invalidate
        """
        # Notify the input tunnels
        for tunnel in list(self.__out_tunnels.values()):
            msg = beans.Message(htunnel.SUBJECT_CLOSE_INPUT_TUNNEL,
                                {'tunnel': tunnel.tunnel_uid})
            try:
                self._herald.fire(tunnel.peer, msg)
            except (HeraldException, KeyError) as ex:
                logger.error("Couldn't close tunnel input: %s", ex)

    def herald_message(self, herald_svc, message):
        """
        An Herald message has been received
        """
        subject = message.subject
        content = message.content
        result = None

        if subject == htunnel.SUBJECT_CREATE_OUTPUT_TUNNEL:
            result = self._create_tunnel(content['tunnel'], message.sender,
                                         content['out_config'])
        elif subject == htunnel.SUBJECT_CLOSE_OUTPUT_TUNNEL:
            self._close_tunnel(content['tunnel'])
        elif subject == htunnel.SUBJECT_CREATE_OUTPUT_LINK:
            result = self._create_link(content['tunnel'], content['link_id'])
        elif subject == htunnel.SUBJECT_CLOSE_OUTPUT_LINK:
            result = self._close_link(content['tunnel'], content['link_id'])
        elif subject == htunnel.SUBJECT_DATA_FROM_INPUT:
            self._handle_data(content['tunnel'], content['link_id'],
                              content['data'])
        else:
            result = {"success": False,
                      "message": "Unknown command: '{0}'".format(subject)}

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

    def get_output_info(self):
        """
        Get the list of output tunnel descriptions

        :return: A list of (uid, in_peer, out_config)
        """
        return tuple([uid] + list(values)
                     for uid, values in self.__out_configs.items())
