#!/usr/bin/python
# -- Content-Encoding: UTF-8 --
"""
Herald core package
"""

SERVICE_HERALD = "herald.core"
"""
Specification of the core Herald service
"""

SERVICE_DIRECTORY = "herald.directory"
"""
Specification of the Herald directory service
"""

SERVICE_LISTENER = "herald.message.listener"
"""
Specification of a message listener
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

PROP_ACCESS_ID = "herald.access.id"
"""
Unique name of the kind of access a transport implementation handles
"""

PROP_FILTERS = "herald.filters"
"""
A set of filename patterns to filter messages
"""
