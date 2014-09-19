#!/usr/bin/python
# -- Content-Encoding: UTF-8 --
"""
Herald HTTP transport implementation

:author: Thomas Calmant
:copyright: Copyright 2014, isandlaTech
:license: Apache License 2.0
:version: 0.0.1
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

# Documentation strings format
__docformat__ = "restructuredtext en"

# ------------------------------------------------------------------------------

ACCESS_ID = "http"
"""
Access ID used by the HTTP transport implementation
"""

# ------------------------------------------------------------------------------

SERVICE_HTTP_DIRECTORY = "herald.http.directory"
"""
Specification of the HTTP transport directory
"""

SERVICE_HTTP_RECEIVER = "herald.http.receiver"
"""
Specification of the HTTP transport servlet (reception side)
"""

SERVICE_HTTP_TRANSPORT = "herald.http.transport"
"""
Specification of the HTTP transport implementation (sending side)
"""

# ------------------------------------------------------------------------------

FACTORY_SERVLET = "herald-http-servlet-factory"
"""
Name of the HTTP reception servlet factory
"""

FACTORY_DISCOVERY_MULTICAST = "herald-http-discovery-multicast-factory"
"""
Name of the Multicast discovery component factory
"""

# ------------------------------------------------------------------------------

PROP_MULTICAST_GROUP = "multicast.group"
"""
Name of the multicast group configuration property
"""

PROP_MULTICAST_PORT = "multicast.port"
"""
Name of the multicast port configuration property
"""
