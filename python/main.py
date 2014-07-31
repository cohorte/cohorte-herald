#!/usr/bin/env python
# -- Content-Encoding: UTF-8 --
"""
Runs an Herald XMPP framework
"""
# Module version
__version_info__ = (0, 0, 1)
__version__ = ".".join(str(x) for x in __version_info__)

# Documentation strings format
__docformat__ = "restructuredtext en"

# ------------------------------------------------------------------------------

# Monitor bot
import herald.xmpp.monitor as xmpp_monitor

# Herald constants
import herald.xmpp

# Pelix
from pelix.ipopo.constants import use_waiting_list
import pelix.framework

# Standard library
import argparse
import logging
import sys

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
         'herald.core',
         'herald.directory',
         'herald.shell',
         'herald.xmpp.directory',
         'herald.xmpp.transport'),
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
    # Get the iPOPO service
    with use_waiting_list(context) as ipopo:
        # Instantiate remote service components
        # ... XMPP Directory
        ipopo.add(herald.xmpp.FACTORY_DIRECTORY, "herald-xmpp-directory")

        # ... XMPP Transport
        ipopo.add(herald.xmpp.FACTORY_TRANSPORT, "herald-xmpp-transport",
                  {herald.xmpp.PROP_XMPP_SERVER: xmpp_server,
                   herald.xmpp.PROP_XMPP_PORT: xmpp_port,
                   herald.xmpp.PROP_MONITOR_JID: monitor_jid,
                   herald.xmpp.PROP_MONITOR_KEY: "42",
                   herald.xmpp.PROP_XMPP_ROOM_JID: main_room_jid})

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
    parser.add_argument("-s", "--server", action="store", default="localhost",
                        dest="xmpp_server", help="Host of the XMPP server")
    parser.add_argument("-p", "--port", action="store", type=int, default=5222,
                        dest="xmpp_port", help="Port of the XMPP server")

    # Peer info
    parser.add_argument("-n", "--name", action="store", default=None,
                        dest="name", help="Peer name")

    # Node info
    parser.add_argument("--node", action="store", default=None,
                        dest="node", help="Node name")

    # Parse arguments
    args = parser.parse_args(sys.argv[1:])

    # Configure the logging package
    logging.basicConfig(level=logging.INFO)
    logging.getLogger('herald').setLevel(logging.DEBUG)

    # Run the framework
    main(args.xmpp_server, args.xmpp_port, args.monitor,
         args.name, args.node)
