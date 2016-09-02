#!/usr/bin/python
# -- Content-Encoding: UTF-8 --
"""
:author: Thomas Calmant
:copyright: Copyright 2014, isandlaTech
:license: Apache License 2.0
:version: 1.0.0
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
__version_info__ = (1, 0, 0)
__version__ = ".".join(str(x) for x in __version_info__)

# Documentation strings format
__docformat__ = "restructuredtext en"

# ------------------------------------------------------------------------------

import logging

# ------------------------------------------------------------------------------

# Prefix to all discovery messages
SUBJECT_DISCOVERY_PREFIX = "herald/directory/discovery"

# First message: Initial contact message, containing our dump
SUBJECT_DISCOVERY_STEP_1 = SUBJECT_DISCOVERY_PREFIX + "/step1"
# Second message: let the remote peer send its dump
SUBJECT_DISCOVERY_STEP_2 = SUBJECT_DISCOVERY_PREFIX + "/step2"
# Third message: the remote peer acknowledge, notify our listeners
SUBJECT_DISCOVERY_STEP_3 = SUBJECT_DISCOVERY_PREFIX + "/step3"

# ------------------------------------------------------------------------------


class PeerContact(object):
    """
    Standard peer discovery algorithm
    """
    def __init__(self, directory, dump_hook, logname=None):
        """
        Sets up members

        :param directory: THe Herald Core Directory
        :param dump_hook: A method that takes a parsed dump dictionary as
                          parameter and returns a patched one
        :param logname: Name of the class logger
        """
        self._directory = directory
        self._hook = dump_hook
        self._logger = logging.getLogger(logname or __name__)
        self.__delayed_notifs = {}

    def __load_dump(self, message):
        """
        Calls the hook method to modify the loaded peer description before
        giving it to the directory

        :param message: The received Herald message
        :return: The updated peer description
        """
        dump = message.content
        if self._hook is not None:
            # Call the hook
            try:
                updated_dump = self._hook(message, dump)
                if updated_dump is not None:
                    # Use the new description
                    dump = updated_dump
            except (TypeError, ValueError) as ex:
                self._logger("Invalid description hook: %s", ex)
        return dump

    def clear(self):
        """
        Clears the pending notification objects
        """
        self.__delayed_notifs.clear()

    def herald_message(self, herald_svc, message):
        """
        Handles a message received by Herald

        :param herald_svc: Herald service
        :param message: Received message
        """
        subject = message.subject
        if subject == SUBJECT_DISCOVERY_STEP_1:
            # Step 1: Register the remote peer and reply with our dump
            try:
                # Delayed registration
                notification = self._directory.register_delayed(
                    self.__load_dump(message))

                peer = notification.peer
                if peer is not None:
                    # Registration succeeded
                    self.__delayed_notifs[peer.uid] = notification

                    # Reply with our dump
                    herald_svc.reply(
                        message, self._directory.get_local_peer().dump(),
                        SUBJECT_DISCOVERY_STEP_2)
            except ValueError:
                self._logger.error("Error registering a discovered peer")

        elif subject == SUBJECT_DISCOVERY_STEP_2:
            # Step 2: Register the dump, notify local listeners, then let
            # the remote peer notify its listeners
            try:
                # Register the peer
                notification = self._directory.register_delayed(
                    self.__load_dump(message))

                if notification.peer is not None:
                    # Let the remote peer notify its listeners
                    herald_svc.reply(message, None, SUBJECT_DISCOVERY_STEP_3)

                    # Now we can notify listeners
                    notification.notify()
            except ValueError:
                self._logger.error("Error registering a peer using the "
                                   "description it sent")

        elif subject == SUBJECT_DISCOVERY_STEP_3:
            # Step 3: notify local listeners about the remote peer
            try:
                self.__delayed_notifs.pop(message.sender).notify()
            except KeyError:
                # Unknown peer
                pass
        else:
            # Unknown subject
            self._logger.warning("Unknown discovery step: %s", subject)
