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
import argparse
import logging

# Herald bridge
from herald.bridge.core import Bridge
from herald.bridge.input.in_socket import SocketInputTCP
from herald.bridge.output.out_serial import BridgeOutSerial

# ------------------------------------------------------------------------------

# Module version
__version_info__ = (0, 0, 1)
__version__ = ".".join(str(x) for x in __version_info__)

# Documentation strings format
__docformat__ = "restructuredtext en"

# ------------------------------------------------------------------------------


def main(args=None):
    """
    tcp2com entry point
    """
    # Parse arguments
    parser = argparse.ArgumentParser(
        description="Herald Bridge Utility: tcp2com")

    parser.add_argument("-d", "--debug", dest="debug", action="store_true",
                        help="Activate debug logs")

    # Socket input
    group = parser.add_argument_group("Socket Input Configuration",
                                      "Configuration of the TCP server")
    group.add_argument("-s", "--server", dest="sock_address",
                       default="localhost", help="Address to listen to")
    group.add_argument("-p", "--port", dest="sock_port", type=int,
                       default=8000, help="TCP Port to listen to")

    # Serial input
    group = parser.add_argument_group("Serial Output Configuration",
                                      "Configuration of the serial port")
    group.add_argument("-c", "--com", dest="serial_port", help="Serial port")
    group.add_argument("-b", "--baud-rate", dest="baud_rate", type=int,
                       default=9600, help="Serial baud rate")

    # Parse arguments
    args = parser.parse_args(args)

    # Setup logging
    if args.debug:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.WARNING)

    # Prepare bridge endpoints
    bridge = Bridge()
    bridge_in = SocketInputTCP()
    bridge_out = BridgeOutSerial()

    # Set them up
    bridge_in.setup(args.sock_address, args.sock_port)
    bridge_out.setup(args.serial_port, args.baud_rate)

    # Bind them
    bridge.set_in(bridge_in)
    bridge.set_out(bridge_out)

    # Run
    print('Starting tcp2com')
    bridge.start()
    try:
        input("Press enter to stop")
    except KeyboardInterrupt:
        pass
    bridge.close()
    print("Bye !")

if __name__ == '__main__':
    main()
