#!/usr/bin/python
# -- Content-Encoding: UTF-8 --
"""
Definition of probe constants

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

SERVICE_STORE = 'herald.probe.store'
""" Service to store data from probes """

# ------------------------------------------------------------------------------


class DummyProbe(object):
    """
    Skeleton of a probe service implementation
    """
    def activate(self, activate=True):
        """
        (De)Activates the probe

        :param activate: Flag to activate or deactivate the probe
        """
        pass

    def activate_channel(self, channel, activate=True):
        """
        (De)Activates a channel

        :param channel: Channel to (de)activate
        :param activate: Flag to activate or deactivate the channel
        """
        pass

    def get_active_channels(self):
        """
        Returns the (sorted) list of active channels
        """
        return []

    def is_active(self):
        """
        Returns True if the probe is active
        """
        return False

    def set_channel_filter(self, channel, ldap_filter):
        """
        Sets the LDAP filter for a channel

        :param channel: Channel to filter
        :param ldap_filter: Filter on channel data
        :raise ValueError: Invalid LDAP filter
        """
        pass

    def store(self, channel, data):
        """
        Stores data in the given channel of the probe. The given dictionary
        must respect the specifications of the target channel.

        Called from Herald internals.

        :param channel: Channel where to store data
        :param data: A dictionary of data to be stored
        """
        pass
