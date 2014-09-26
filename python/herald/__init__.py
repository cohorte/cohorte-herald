#!/usr/bin/env python
# -- Content-Encoding: UTF-8 --
"""
Herald core package

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
# Service specifications

SERVICE_HERALD = "herald.core"
"""
Specification of the Herald core service. This service is provided only if
at least one transport implementation is available.
"""

SERVICE_HERALD_INTERNAL = "herald.core.internal"
"""
Synonym for the Herald core server, but with a different life cycle:
this service has the same life cycle as the Herald core component
"""

SERVICE_DIRECTORY = "herald.directory"
"""
Specification of the Herald directory service
"""

SERVICE_LISTENER = "herald.message.listener"
"""
Specification of a message listener
"""

SERVICE_DIRECTORY_LISTENER = "herald.directory.listener"
"""
Specification of a directory listener
"""

SERVICE_DIRECTORY_GROUP_LISTENER = "herald.directory.group_listener"
"""
Specification of a directory group listener
"""

SERVICE_TRANSPORT = "herald.transport"
"""
Specification of a transport implementation for Herald
"""

SERVICE_TRANSPORT_DIRECTORY = "herald.transport.directory"
"""
Specification of the directory associated to a transport implementation
"""

# ------------------------------------------------------------------------------
# Service properties

PROP_ACCESS_ID = "herald.access.id"
"""
Unique name of the kind of access a transport implementation handles
"""

PROP_FILTERS = "herald.filters"
"""
A set of filename patterns to filter messages
"""

# ------------------------------------------------------------------------------
# Framework properties

FWPROP_APPLICATION_ID = "herald.application.id"
"""
ID of the application the local peer is part of. Peers of other applications
will be ignored.
"""

DEFAULT_APPLICATION_ID = "<herald-legacy>"
""" Default application ID """

FWPROP_PEER_UID = "herald.peer.uid"
"""
UID of the peer. Default to the Pelix framework UID.
"""

FWPROP_PEER_NAME = "herald.peer.name"
"""
Human-readable name of the peer. Default to the peer UID.
"""

FWPROP_PEER_GROUPS = "herald.peer.groups"
"""
The list of groups the peer belongs to. Can be either a list or
a comma-separated list string.
"""

FWPROP_NODE_UID = "herald.node.uid"
"""
UID of the node hosting the peer. Defaults to the peer UID.
"""

FWPROP_NODE_NAME = "herald.node.name"
"""
Human-readable name of the node hosting the peer. Defaults to the node UID.
"""
