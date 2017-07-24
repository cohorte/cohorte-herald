#!/usr/bin/env python
# -- Content-Encoding: UTF-8 --
"""
Runs an Herald HTTP framework

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

# Module version
__version_info__ = (1, 0, 1)
__version__ = ".".join(str(x) for x in __version_info__)

# Documentation strings format
__docformat__ = "restructuredtext en"

# ------------------------------------------------------------------------------

# Herald constants
import herald.transports.http

# Pelix
from pelix.ipopo.constants import use_waiting_list
import pelix.framework
import pelix.http

# Standard library
import argparse
import logging

# ------------------------------------------------------------------------------


def main(http_port, peer_name, node_name, app_id):
    """
    Runs the framework

    :param http_port: HTTP port to listen to
    :param peer_name: Name of the peer
    :param node_name: Name (also, UID) of the node hosting the peer
    :param app_id: Application ID
    """
    # Create the framework
    framework = pelix.framework.create_framework(
        ('pelix.ipopo.core',
         'pelix.ipopo.waiting',
         'pelix.shell.core',
         'pelix.shell.ipopo',
         'pelix.shell.console',
         'pelix.http.basic',

         # Herald core
         'herald.core',
         'herald.directory',
         'herald.shell',

         # Herald HTTP
         'herald.transports.http.directory',
         'herald.transports.http.discovery_multicast',
         'herald.transports.http.servlet',
         'herald.transports.http.transport',

         # RPC
         'pelix.remote.dispatcher',
         'pelix.remote.registry',
         'herald.remote.discovery',
         'herald.remote.herald_xmlrpc',),
        {herald.FWPROP_NODE_UID: node_name,
         herald.FWPROP_NODE_NAME: node_name,
         herald.FWPROP_PEER_NAME: peer_name,
         herald.FWPROP_APPLICATION_ID: app_id})

    # Start everything
    framework.start()
    context = framework.get_bundle_context()

    # Instantiate components
    with use_waiting_list(context) as ipopo:
        # ... HTTP server
        ipopo.add(pelix.http.FACTORY_HTTP_BASIC, "http-server",
                  {pelix.http.HTTP_SERVICE_PORT: http_port})

        # ... HTTP reception servlet
        ipopo.add(herald.transports.http.FACTORY_SERVLET,
                  "herald-http-servlet")

        # ... HTTP multicast discovery
        ipopo.add(herald.transports.http.FACTORY_DISCOVERY_MULTICAST,
                  "herald-http-discovery-multicast")

    # Start the framework and wait for it to stop
    framework.wait_for_stop()

# ------------------------------------------------------------------------------

if __name__ == "__main__":
    # Parse arguments
    parser = argparse.ArgumentParser(description="Pelix Herald demo")

    # HTTP server
    group = parser.add_argument_group("HTTP Configuration",
                                      "Configuration of the HTTP transport")
    group.add_argument("-p", "--port", action="store", type=int, default=0,
                       dest="http_port", help="Port of the HTTP server")

    # Peer info
    group = parser.add_argument_group("Peer Configuration",
                                      "Identity of the Peer")
    group.add_argument("-n", "--name", action="store", default=None,
                       dest="name", help="Peer name")
    group.add_argument("--node", action="store", default=None,
                       dest="node", help="Node name")
    group.add_argument("-a", "--app", action="store",
                       default=herald.DEFAULT_APPLICATION_ID,
                       dest="app_id", help="Application ID")

    # Parse arguments
    args = parser.parse_args()

    # Configure the logging package
    logging.basicConfig(level=logging.INFO)
    logging.getLogger('herald').setLevel(logging.DEBUG)
    logging.getLogger('requests').setLevel(logging.WARNING)

    # Run the framework
    main(args.http_port, args.name, args.node, args.app_id)
