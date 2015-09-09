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
import threading

# PySerial
import serial

# ------------------------------------------------------------------------------

# Module version
__version_info__ = (0, 0, 1)
__version__ = ".".join(str(x) for x in __version_info__)

# Documentation strings format
__docformat__ = "restructuredtext en"

# ------------------------------------------------------------------------------

logger = logging.getLogger(__name__)

# ------------------------------------------------------------------------------


class BridgeOutSerial(object):
    """
    Bridge serial output
    """
    def __init__(self):
        """
        Sets up members
        """
        self.__stop_event = threading.Event()
        self.__bridge_in = None
        self.__serial = serial.Serial()

        # Active link ID
        self.__active_link_id = None

    def bind_bridge_input(self, bridge_in):
        """
        Sets bridge input
        """
        self.__bridge_in = bridge_in

    def setup(self, com_port, baud_rate=9600, parity='N', timeout=1):
        """
        Configure the serial port
        """
        self.__serial = serial.Serial()
        self.__serial.port = com_port
        self.__serial.baudrate = baud_rate
        self.__serial.parity = parity
        self.__serial.timeout = timeout
        self.__serial.open()

    def create_link(self, link_id):
        """
        Accepts the link if none is active
        """
        if self.__active_link_id is None:
            # Check CTS
            if not self.__serial.getDSR():
                logger.debug("Create link rejected: remote side not ready")
                return False

            # Store active link
            self.__active_link_id = link_id

            # Set the link up
            self.__serial.setRTS(True)
            return True
        else:
            logger.debug("Create link rejected (link is  active)")

    def close_link(self, link_id):
        """
        Closes the active link
        """
        if link_id == self.__active_link_id:
            logger.debug("Closing link...")

            # Set link down
            self.__serial.setRTS(False)

            # Clean up
            self.__active_link_id = None
            return True
        else:
            logger.debug("Link not closed: bad ID")

    def start(self):
        """
        Starts the tunnel
        """
        self.__stop_event.clear()
        thread = threading.Thread(target=self.read_loop,
                                  name="Herald-Bridge-SerialOutput")
        thread.daemon = True
        thread.start()

    def close(self):
        """
        Stops the bridge
        """
        # Stop
        self.__stop_event.set()

        # Notify bridge in
        if self.__bridge_in is not None and self.__active_link_id is not None:
            self.__bridge_in.link_closed(self.__active_link_id)

        if self.__serial is not None:
            # Set link down
            self.__serial.setRTS(False)
            self.__serial.close()

        # Clean up
        self.__serial = None
        self.__active_link_id = None

    def __link_lost(self):
        """
        The link has been lost
        """
        logger.debug("Link lost: active ID=%s", self.__active_link_id)

        if self.__active_link_id is not None:
            # Link down
            if self.__serial is not None:
                logger.debug("Link lost: set RTS down")
                self.__serial.setRTS(False)

            # Reset link ID
            link_id = self.__active_link_id
            self.__active_link_id = None

            # Notify bridge
            self.__bridge_in.link_closed(link_id)

    def send(self, link_id, data):
        """
        Send data over serial
        """
        if link_id == self.__active_link_id:
            try:
                logger.debug(
                    "Bridge In >>-- (%d bytes) --> Serial", len(data))
                self.__serial.write(data)
            except serial.SerialException as ex:
                logger.exception("Error writing to serial: %s", ex)

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
        if not self.__serial.getDSR():
            logger.debug("Pre-Read: DSR Down...")
            if self.__active_link_id:
                # Link lost
                logger.info("Pre-Read: link lost")
                self.__link_lost()
            else:
                # Wait a bit before the next loop
                logger.debug("Pre-Read: No active link")
                self.__stop_event.wait(.5)
        else:
            try:
                # Read (blocking, but with possible timeout)
                data = self.__serial.read(1)
                if self.__serial is None:
                    # Closing stop
                    logger.debug("Data read: serial became None")
                    return
                elif not self.__serial.getDSR():
                    # Link is down
                    logger.info("Data read: DSR down, link lost")
                    self.__link_lost()
                else:
                    # Maybe there is some data to read
                    still_to_read = self.__serial.inWaiting()
                    if still_to_read:
                        data += self.__serial.read(still_to_read)

                    if data:
                        logger.debug(
                            "Bridge In <-- (%d bytes) --<< Serial", len(data))
                        self.__bridge_in.link_data(self.__active_link_id, data)
            except serial.SerialException as ex:
                logger.error("Error reading from serial: %s", ex)
