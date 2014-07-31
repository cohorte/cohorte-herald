#!/usr/bin/python
# -- Content-Encoding: UTF-8 --
"""
Herald XMPP transport implementation
"""

ACCESS_ID = "xmpp"
"""
Access ID used by the XMPP transport implementation
"""

# ------------------------------------------------------------------------------

SERVICE_XMPP_DIRECTORY = "herald.xmpp.directory"
"""
Specification of the XMPP transport directory
"""

# ------------------------------------------------------------------------------

PROP_XMPP_SERVER = "xmpp.server"
"""
Name of XMPP server host
"""

PROP_XMPP_PORT = "xmpp.port"
"""
XMPP server port
"""

PROP_MONITOR_JID = "xmpp.monitor.jid"
"""
JID of the Monitor Bot to contact to join Herald rooms
"""

PROP_MONITOR_KEY = "xmpp.monitor.key"
"""
Key to send to the Monitor Bot when requesting for an invite
"""

PROP_XMPP_ROOM_JID = "xmpp.room.jid"
"""
Full JID of the Herald main room
"""

# ------------------------------------------------------------------------------

FACTORY_TRANSPORT = "herald-xmpp-transport-factory"
"""
Name of the XMPP transport implementation factory
"""

FACTORY_DIRECTORY = "herald-xmpp-directory-factory"
"""
Name of the XMPP transport directory factory
"""
