#!/usr/bin/python
# -- Content-Encoding: UTF-8 --
"""
Core probe service

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

# Bundle version
import herald.version
__version__=herald.version.__version__

# ------------------------------------------------------------------------------

# Probe constants
from herald import SERVICE_PROBE
from herald.probe import SERVICE_STORE

# Pelix
from pelix.ipopo.decorators import ComponentFactory, Requires, Provides, \
    Property, Instantiate
import pelix.ldapfilter as ldapfilter

# Standard library
import logging
_logger = logging.getLogger(__name__)

# ------------------------------------------------------------------------------


@ComponentFactory()
@Requires('_stores', SERVICE_STORE, aggregate=True, optional=True)
@Provides(SERVICE_PROBE)
@Property('_activated', 'enabled', False)
@Instantiate('herald-probe-dispatcher')
class ProbeCore(object):
    """
    Debug probe for Herald
    """
    def __init__(self):
        """
        Sets up members
        """
        # Active stores
        self._stores = []

        # Global state
        self._activated = True

        # Set of activated channels
        self._channels_enabled = set()

        # LDAP filter of each channel
        self._channels_filters = {}

    def __call_stores(self, method, *args, **kwargs):
        """
        Calls the registered stores, if any

        :param method: Name of the method to call
        :param args: Positional arguments
        :param kwargs: Keyword arguments
        """
        # Use a copy of the list of stores
        stores = self._stores[:] if self._stores else []
        for store in stores:
            try:
                # Call the method
                getattr(store, method)(*args, **kwargs)
            except AttributeError:
                # Method not implemented
                pass
            except Exception as ex:
                # Error calling store
                _logger.exception("Error calling store: %s", ex)

    def activate(self, activate=True):
        """
        (De)Activates the probe

        :param activate: Flag to activate or deactivate the probe
        """
        self._activated = activate

    def activate_channel(self, channel, activate=True):
        """
        (De)Activates a channel

        :param channel: Channel to (de)activate
        :param activate: Flag to activate or deactivate the channel
        """
        if activate:
            # Notify stores
            self.__call_stores("activate_channel", channel)

            # Activate channel
            self._channels_enabled.add(channel)

        else:
            try:
                self._channels_enabled.remove(channel)
            except KeyError:
                # Unknown channel
                pass
            else:
                # Notify stores
                self.__call_stores("deactivate_channel", channel)

    def get_active_channels(self):
        """
        Returns the (sorted) list of active channels
        """
        return sorted(self._channels_enabled)

    def is_active(self):
        """
        Returns True if the probe is active
        """
        return self._activated

    def set_channel_filter(self, channel, ldap_filter):
        """
        Sets the LDAP filter for a channel

        :param channel: Channel to filter
        :param ldap_filter: Filter on channel data
        :raise ValueError: Invalid LDAP filter
        """
        # Compute the filter
        parsed_filter = ldapfilter.get_ldap_filter(ldap_filter)

        if parsed_filter is None:
            try:
                # Remove the filter
                del self._channels_filters[channel]
            except KeyError:
                # No filter to remove
                pass
        else:
            # Store the filter
            self._channels_filters[channel] = parsed_filter

    def store(self, channel, data):
        """
        Stores data in the given channel of the probe. The given dictionary
        must respect the specifications of the target channel.

        Called from Herald internals.

        :param channel: Channel where to store data
        :param data: A dictionary of data to be stored
        """
        if self._activated and channel in self._channels_enabled:
            try:
                # Check filter
                authorized = self._channels_filters[channel].matches(data)
            except KeyError:
                # No filter
                authorized = True

            if authorized:
                self.__call_stores("store", channel, data)
