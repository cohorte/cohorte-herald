#!/usr/bin/python
# -- Content-Encoding: UTF-8 --
"""
Herald HTTP transport implementation

:author: Thomas Calmant
:copyright: Copyright 2014, isandlaTech
:license: Apache License 2.0
:version: 0.0.2.dev
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
__version_info__ = (0, 0, 2)
__version__ = ".".join(str(x) for x in __version_info__)

# Documentation strings format
__docformat__ = "restructuredtext en"

# ------------------------------------------------------------------------------


def json_converter(obj):
    """
    Converts sets to list during JSON serialization
    """
    if isinstance(obj, (set, frozenset)):
        return tuple(obj)

    raise TypeError

# ------------------------------------------------------------------------------

try:
    # IPv4/v6 utility methods, added in Python 3.3
    import ipaddress
except ImportError:
    # Module not available
    def normalize_ip(ip_address):
        """
        Should un-map the given IP address. (Does nothing)

        :param ip_address: An IP address
        :return: The given IP address
        """
        return ip_address
else:
    def normalize_ip(ip_address):
        """
        Un-maps the given IP address: if it is an IPv4 address mapped in an
        IPv6 one, the methods returns the IPv4 address

        :param ip_address: An IP address
        :return: The un-mapped IPv4 address or the given address
        """
        try:
            parsed = ipaddress.ip_address(ip_address)
            if parsed.version == 6:
                mapped = parsed.ipv4_mapped
                if mapped is not None:
                    # Return the un-mapped IPv4 address
                    return str(mapped)
        except ValueError:
            # No an IP address: maybe a host name => keep it as is
            pass

        return ip_address
