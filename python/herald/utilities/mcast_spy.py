#!/usr/bin/python
# -- Content-Encoding: UTF-8 --
"""
A spy listening to a given multicast target

:author: Thomas Calmant
:copyright: Copyright 2015, isandlaTech
:license: Apache License 2.0
:version: 0.0.1
:status: Alpha

..

    Copyright 2015 isandlaTech

    Licensed under the Apache License, Version 2.0 (the "License")
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
from __future__ import print_function
import argparse
import datetime
import logging
import select
import sys

# Herald
import herald.transports.http.discovery_multicast as multicast

# ------------------------------------------------------------------------------

# Bundle version
from herald.version import *

# ------------------------------------------------------------------------------


def hexdump(src, length=16, sep='.'):
    """
    Returns src in hex dump.
    From https://gist.github.com/ImmortalPC/c340564823f283fe530b

    :param length: Nb Bytes by row.
    :param sep: For the text part, sep will be used for non ASCII char.
    :return: The hexdump
    """
    result = []

    for i in range(0, len(src), length):
        sub_src = src[i:i + length]
        hexa = ''
        for h in range(0, len(sub_src)):
            if h == length / 2:
                hexa += ' '
            h = sub_src[h]
            if not isinstance(h, int):
                h = ord(h)
            h = hex(h).replace('0x', '')
            if len(h) == 1:
                h = '0' + h
            hexa += h + ' '

        hexa = hexa.strip(' ')
        text = ''
        for c in sub_src:
            if not isinstance(c, int):
                c = ord(c)
            if 0x20 <= c < 0x7F:
                text += chr(c)
            else:
                text += sep
        result.append(('%08X:  %-' + str(length * (2 + 1) + 1) + 's  |%s|')
                      % (i, hexa, text))

    return '\n'.join(result)


def run_spy(group, port, verbose):
    """
    Runs the multicast spy

    :param group: Multicast group
    :param port: Multicast port
    :param verbose: If True, prints more details
    """
    # Create the socket
    socket, group = multicast.create_multicast_socket(group, port)
    print("Socket created:", group, "port:", port)

    # Set the socket as non-blocking
    socket.setblocking(0)

    # Prepare stats storage
    stats = {
        "total_bytes": 0,
        "total_count": 0,
        "sender_bytes": {},
        "sender_count": {},
    }

    print("Press Ctrl+C to exit")
    try:
        loop_nb = 0
        while True:
            if loop_nb % 50 == 0:
                loop_nb = 0
                print("Reading...")

            loop_nb += 1

            ready = select.select([socket], [], [], .1)
            if ready[0]:
                # Socket is ready
                data, sender = socket.recvfrom(1024)
                len_data = len(data)

                # Store stats
                stats["total_bytes"] += len_data
                stats["total_count"] += 1

                try:
                    stats["sender_bytes"][sender] += len_data
                    stats["sender_count"][sender] += 1
                except KeyError:
                    stats["sender_bytes"][sender] = len_data
                    stats["sender_count"][sender] = 1

                print("Got", len_data, "bytes from", sender[0], "port",
                      sender[1], "at", datetime.datetime.now())
                if verbose:
                    print(hexdump(data))
    except KeyboardInterrupt:
        # Interrupt
        print("Ctrl+C received: bye !")

    # Print statistics
    print("Total number of packets:", stats["total_count"])
    print("Total read bytes.......:", stats["total_bytes"])

    for sender in stats["sender_count"]:
        print("\nSender", sender[0], "from port", sender[1])
        print("\tTotal packets:", stats["sender_count"][sender])
        print("\tTotal bytes..:", stats["sender_bytes"][sender])

    return 0


def main(argv=None):
    """
    Entry point

    :param argv: Program arguments
    """
    parser = argparse.ArgumentParser(description="Multicast packets spy")

    parser.add_argument("-g", "--group", dest="group", default="239.0.0.1",
                        help="Multicast target group (address)")
    parser.add_argument("-p", "--port", type=int, dest="port", default=42000,
                        help="Multicast target port")

    parser.add_argument("-d", "--debug", action="store_true", dest="debug",
                        help="Set logger to DEBUG level")
    parser.add_argument("-v", "--verbose", action="store_true", dest="verbose",
                        help="Verbose output")

    # Parse arguments
    args = parser.parse_args(argv)

    # Configure the logger
    if args.debug:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.WARNING)

    try:
        return run_spy(args.group, args.port, args.verbose)
    except Exception as ex:
        logging.exception("Error running spy: %s", ex)

    return 1

if __name__ == '__main__':
    sys.exit(main())
