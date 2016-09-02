#!/usr/bin/python
# -- Content-Encoding: UTF-8 --
"""
Shell commands for the probe

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

# Herald
import herald

# Pelix
from pelix.ipopo.decorators import ComponentFactory, Requires, RequiresBest, \
    Provides, Instantiate, Validate, Invalidate
from pelix.ipopo.constants import use_ipopo
import pelix.constants
import pelix.shell

# ------------------------------------------------------------------------------


@ComponentFactory("herald-probe-factory")
@RequiresBest("_probe", herald.SERVICE_PROBE)
@Requires("_utils", pelix.shell.SERVICE_SHELL_UTILS)
@Provides(pelix.shell.SERVICE_SHELL_COMMAND)
@Instantiate("herald-probe-shell")
class ProbeCommands(object):
    """
    Herald probe shell commands
    """
    def __init__(self):
        """
        Sets up the object
        """
        self._context = None
        self._probe = None
        self._utils = None

    @Validate
    def _validate(self, context):
        """
        Component validated
        """
        self._context = context

    @Invalidate
    def _invalidate(self, _):
        """
        Component invalidated
        """
        self._context = None

    def get_namespace(self):
        """
        Retrieves the name space of this command handler
        """
        return "herald"

    def get_methods(self):
        """
        Retrieves the list of tuples (command, method) for this command handler
        """
        return [("enable_probe", self.enable_probe),
                ("enable_channel", self.enable_channel),
                ("disable_probe", self.disable_probe),
                ("disable_channel", self.disable_channel),
                ("set_channel_filter", self.set_channel_filter),
                ("probe_state", self.probe_state),
                ("install_default", self.install_default_probe)]

    def enable_probe(self, _):
        """
        Enables the probe
        """
        self._probe.activate(True)

    def disable_probe(self, _):
        """
        Disables the probe
        """
        self._probe.activate(False)

    def enable_channel(self, _, *channels):
        """
        Enables a probe channel
        """
        for channel in channels:
            self._probe.activate_channel(channel, True)

    def disable_channel(self, _, *channels):
        """
        Disables a probe channel
        """
        for channel in channels:
            self._probe.activate_channel(channel, True)

    def set_channel_filter(self, session, channel, ldap_filter=""):
        """
        Sets the LDAP filter associated to a channel
        """
        try:
            self._probe.set_channel_filter(channel, ldap_filter)
        except ValueError as ex:
            session.write_line("Invalid LDAP filter: {0} -- {1}",
                               ex, ldap_filter)

    def probe_state(self, session):
        """
        Prints the current probe configuration
        """
        active_probe = self._probe.is_active()
        lines = ["Enabled........: {0}".format(active_probe)]
        if active_probe:
            lines.append("Active channels:")
            lines.extend("\t* {0}".format(channel)
                         for channel in self._probe.get_active_channels())
        lines.append("")

        session.write_line("\n".join(lines))

    def install_default_probe(self, session):
        """
        Installs the default probe bundles (doesn't enable it)
        """
        for bundle in ("herald.probe.core", "herald.probe.store_log",
                       "herald.probe.store_sqlite"):
            try:
                self._context.install_bundle(bundle).start()
            except pelix.constants.BundleException as ex:
                session.write_line("Error installing {0}: {1}", bundle, ex)

        with use_ipopo(self._context) as ipopo:
            # Instantiate components
            # ... Log store
            ipopo.instantiate(
                'herald-probe-log-factory', 'herald-probe-log',
                {'logger.prefix': 'herald.debug'})

            # ... SQLite store
            ipopo.instantiate(
                'herald-probe-sqlite-factory', 'herald-probe-sqlite',
                {'db.file': 'herald_probe.db'})
