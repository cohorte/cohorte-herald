#!/usr/bin/python
# -- Content-Encoding: UTF-8 --
"""
Shell commands to handle tunnels

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
import herald.tunnel
import herald.tunnel.config as config

# Pelix
from pelix.ipopo.decorators import ComponentFactory, Requires, Provides, \
    Instantiate
import pelix.shell

# Standard library
import socket

# ------------------------------------------------------------------------------

SOCK_TYPE = {
    'tcp': socket.SOCK_STREAM,
    'udp': socket.SOCK_DGRAM,
}

# ------------------------------------------------------------------------------


@ComponentFactory("herald-tunnel-shell-factory")
@Requires("_tunnel", herald.tunnel.SERVICE_TUNNEL)
@Requires("_utils", pelix.shell.SERVICE_SHELL_UTILS)
@Provides(pelix.shell.SERVICE_SHELL_COMMAND)
@Instantiate("herald-tunnel-shell")
class HeraldCommands(object):
    """
    Herald shell commands
    """
    def __init__(self):
        """
        Sets up the object
        """
        self._tunnel = None
        self._utils = None

    @staticmethod
    def get_namespace():
        """
        Retrieves the name space of this command handler
        """
        return "tunnel"

    def get_methods(self):
        """
        Retrieves the list of tuples (command, method) for this command handler
        """
        return [("open", self.open_tunnel),
                ("close", self.close_tunnel),
                ("list_in", self.list_in_tunnels),
                ("list_out", self.list_out_tunnels),
                ]

    def open_tunnel(self, io_handler, local_port, target_peer,
                    target_address, target_port, kind="tcp"):
        """
        Opens a new tunnel
        """
        # Prepare configurations
        in_config = config.InputSocketConfiguration()
        in_config.address = "localhost"
        in_config.port = int(local_port)
        in_config.sock_type = SOCK_TYPE[kind]

        out_config = config.InputSocketConfiguration()
        out_config.address = target_address
        out_config.port = int(target_port)
        out_config.sock_type = SOCK_TYPE[kind]

        # Create tunnel
        uid = self._tunnel.open_tunnel(in_config, target_peer, out_config)
        io_handler.write_line("Tunnel opened: {0}", uid)
        return uid

    def close_tunnel(self, io_handler, uid):
        """
        Closes a tunnel
        """
        try:
            self._tunnel.close_tunnel(uid)
            io_handler.write_line("Tunnel closed")
        except KeyError:
            io_handler.write_line("Unknown tunnel: {0}", uid)

    def list_in_tunnels(self, io_handler, uid=None):
        """
        Lists the input tunnels
        """
        header = ('UID', 'Input', 'Output Peer', 'Output')
        lines = [info for info in self._tunnel.get_input_info(uid)]
        io_handler.write_line(self._utils.make_table(header, lines))

    def list_out_tunnels(self, io_handler):
        """
        Lists the output tunnels
        """
        header = ('UID', 'Source Peer', 'Output')
        lines = [info for info in self._tunnel.get_output_info()]
        io_handler.write_line(self._utils.make_table(header, lines))
