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
import uuid

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


class BridgeInSerial(object):
    """
    Bridge serial input
    """
    def __init__(self):
        """
        Sets up members
        """
        self.__stop_event = threading.Event()

        # Bridge output
        self.__bridge_out = None

        # Serial link
        self.__serial = serial.Serial()

        # Re-open link timer
        self.__timer = None

        # Output link ID
        self.__active_link_id = None

    def bind_bridge_output(self, bridge_out):
        """
        Sets bridge output
        """
        self.__bridge_out = bridge_out

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

    def start(self):
        """
        Starts the tunnel
        """
        self.__stop_event.clear()

        # Ready to read
        self.__serial.setDTR(True)

        # Start reading
        thread = threading.Thread(target=self.read_loop,
                                  name="Herald-Bridge-SerialInput")
        thread.daemon = True
        thread.start()

    def close(self):
        """
        Stops the bridge
        """
        # Stop reading
        self.__serial.setDTR(False)

        # Stop reading
        self.__stop_event.set()
        self.__serial.close()
        self.__serial = None

        # Close the output link
        self.__bridge_out.close_link(self.__active_link_id)

    def link_data(self, link_id, data):
        """
        Send data over serial
        """
        if link_id == self.__active_link_id:
            try:
                logger.debug(
                    "Bridge Out >>-- (%d bytes) --> Serial", len(data))
                self.__serial.write(data)
            except serial.SerialException as ex:
                logger.exception("Error writing to serial: %s", ex)

    def link_closed(self, link_id):
        """
        The output link has been closed by the target
        """
        if link_id == self.__active_link_id:
            logger.debug("Link closed: setting DTR")
            # Notify the bridge
            self.__serial.setDTR(False)

            # Wait a little before re-opening the link
            self.__run_reopen_timer()

    def __run_reopen_timer(self, delay=.5):
        """
        (Re)Starts the re-open link time
        """
        if self.__timer is not None:
            # Cancel the current timer
            self.__timer.cancel()

        # Setup the timer
        self.__timer = threading.Timer(delay, self.__reopen_link)
        self.__timer.start()

    def __reopen_link(self, restart_time=True):
        """
        Try to reopen the output link
        """
        try:
            # Reopen the link
            self.__active_link_id = uuid.uuid4().hex
            logger.debug("Trying to reopen link...")
            self.__bridge_out.create_link(self.__active_link_id)
        except Exception as ex:
            # Something went wrong
            logger.exception("Error re-opening link: %s", ex)
            self.__active_link_id = None

            if restart_time:
                # Try again later
                self.__run_reopen_timer()
            return False
        else:
            # All OK
            logger.debug("Link re-opened: %s", self.__active_link_id)
            self.__serial.setDTR(True)
            self.__timer = None
            return True

    def __link_lost(self):
        """
        The link has been lost
        """
        logger.debug("Link lost: active ID=%s", self.__active_link_id)
        if self.__active_link_id is not None:
            # Clean up link ID
            link_id = self.__active_link_id
            self.__active_link_id = None

            # Notify the bridge
            logger.debug("Link lost: Notify Bridge out...")
            self.__bridge_out.close_link(link_id)

    def read_loop(self):
        """
        Reading loop
        """
        while not self.__stop_event.is_set():
            self.read_once()

    def read_once(self):
        """
        Reads one frame from serial input
        """
        if not self.__serial.getCTS():
            logger.debug("Pre-Read: CTS Down...")
            if self.__active_link_id:
                # Link lost
                logger.info("Pre-Read: link lost")
                self.__link_lost()
            else:
                # Wait a bit before the next loop
                logger.debug("Pre-Read: No active link")
                self.__stop_event.wait(.5)
        else:
            if not self.__active_link_id:
                # New connexion !
                if not self.__reopen_link(False):
                    # Couldn't open link, wait and see
                    self.__stop_event.wait(.5)
                    return

            # Link is up
            try:
                # Read (blocking, but with possible timeout)
                data = self.__serial.read(1)
                if self.__serial is None:
                    # Closing stop
                    logger.debug("Data read: serial became None")
                    return
                elif not self.__serial.getCTS():
                    # Link is down
                    logger.info("Data read: CTS down, link lost")
                    self.__link_lost()
                else:
                    # Data to read
                    still_to_read = self.__serial.inWaiting()
                    if still_to_read:
                        data += self.__serial.read(still_to_read)

                    if data:
                        logger.debug(
                            "Serial >>-- (%d bytes) --> Bridge Out", len(data))
                        self.__bridge_out.send(self.__active_link_id, data)
            except serial.SerialException as ex:
                logger.exception("Error reading from serial: %s", ex)
