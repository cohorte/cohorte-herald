#!/usr/bin/env python
# -- Content-Encoding: UTF-8 --
"""
Runs an Herald XMPP framework

:author: Thomas Calmant
:copyright: Copyright 2014, isandlaTech
:license: Apache License 2.0
:version: 0.0.1
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
__version_info__ = (0, 0, 1)
__version__ = ".".join(str(x) for x in __version_info__)

# Documentation strings format
__docformat__ = "restructuredtext en"

# ------------------------------------------------------------------------------

# Monitor bot
import herald.transports.xmpp.monitor as xmpp_monitor

# Herald constants
import herald.transports.xmpp

# Pelix
from pelix.ipopo.constants import use_waiting_list
import pelix.framework

# Standard library
import argparse
import logging

# ------------------------------------------------------------------------------


def main(xmpp_server, xmpp_port, run_monitor, peer_name, node_name):
    """
    Runs the framework

    :param xmpp_server: Address of the XMPP server
    :param xmpp_port: Port of the XMPP server
    :param run_monitor: Start the monitor bot
    :param peer_name: Name of the peer
    :param node_name: Name (also, UID) of the node hosting the peer
    """
    # Monitor configuration
    monitor_jid = 'bot@phenomtwo3000'
    main_room = 'herald'
    main_room_jid = '{0}@conference.phenomtwo3000'.format(main_room)

    # Create the framework
    framework = pelix.framework.create_framework(
        ('pelix.ipopo.core',
         'pelix.ipopo.waiting',
         'pelix.shell.core',
         'pelix.shell.ipopo',
         'pelix.shell.console',

         # Herald core
         'herald.core',
         'herald.directory',
         'herald.shell',

         # Herald XMPP
         'herald.transports.xmpp.directory',
         'herald.transports.xmpp.transport',

         # RPC
         'pelix.remote.dispatcher',
         'pelix.remote.registry',
         'herald.remote.discovery',
         'herald.remote.herald_xmlrpc',),
        {herald.FWPROP_NODE_UID: node_name,
         herald.FWPROP_NODE_NAME: node_name,
         herald.FWPROP_PEER_NAME: peer_name})

    # Start everything
    framework.start()
    context = framework.get_bundle_context()

    if run_monitor:
        # Start the monitor
        monitor = xmpp_monitor.MonitorBot(monitor_jid, "bot", "Monitor")
        monitor.connect(xmpp_server, xmpp_port, use_tls=False)
        monitor.create_main_room(main_room)

    # Instantiate components
    with use_waiting_list(context) as ipopo:
        # ... XMPP Transport
        ipopo.add(herald.transports.xmpp.FACTORY_TRANSPORT,
                  "herald-xmpp-transport",
                  {herald.transports.xmpp.PROP_XMPP_SERVER: xmpp_server,
                   herald.transports.xmpp.PROP_XMPP_PORT: xmpp_port,
                   herald.transports.xmpp.PROP_MONITOR_JID: monitor_jid,
                   herald.transports.xmpp.PROP_MONITOR_KEY: "42",
                   herald.transports.xmpp.PROP_XMPP_ROOM_JID: main_room_jid})

    # Start the framework and wait for it to stop
    framework.wait_for_stop()

    if run_monitor:
        # Stop the monitor
        monitor.disconnect()

# ------------------------------------------------------------------------------

if __name__ == "__main__":
    # Parse arguments
    parser = argparse.ArgumentParser(description="Pelix Herald demo")

    # Provider or consumer
    parser.add_argument("-m", "--monitor", action="store_true",
                        dest="monitor",
                        help="Runs the monitor bot")

    # XMPP server
    group = parser.add_argument_group("XMPP Configuration",
                                      "Configuration of the XMPP transport")
    group.add_argument("-s", "--server", action="store", default="localhost",
                       dest="xmpp_server", help="Host of the XMPP server")
    group.add_argument("-p", "--port", action="store", type=int, default=5222,
                       dest="xmpp_port", help="Port of the XMPP server")

    # Peer info
    group = parser.add_argument_group("Peer Configuration",
                                      "Identity of the Peer")
    group.add_argument("-n", "--name", action="store", default=None,
                       dest="name", help="Peer name")
    group.add_argument("--node", action="store", default=None,
                       dest="node", help="Node name")

    # Parse arguments
    args = parser.parse_args()

    # Configure the logging package
    logging.basicConfig(level=logging.INFO)
    logging.getLogger('herald').setLevel(logging.DEBUG)

    # Run the framework
    main(args.xmpp_server, args.xmpp_port, args.monitor,
         args.name, args.node)
