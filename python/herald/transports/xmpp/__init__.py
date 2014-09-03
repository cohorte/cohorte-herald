#!/usr/bin/python
# -- Content-Encoding: UTF-8 --
"""
Herald XMPP transport implementation

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

ACCESS_ID = "xmpp"
"""
Access ID used by the XMPP transport implementation
"""

# ------------------------------------------------------------------------------

SERVICE_XMPP_DIRECTORY = "herald.xmpp.directory"
"""
Specification of the XMPP transport directory
"""

SERVICE_MONITOR_BOT = "herald.xmpp.monitor"
"""
Specification of the XMPP Monitor bot service, provided by the wrapper
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

PROP_XMPP_ROOM_NAME = "xmpp.room.name"
"""
Simple name of the Herald main room
"""

PROP_MONITOR_PASSWORD = 'xmpp.monitor.password'
"""
Password of the account of the Monitor Bot
"""

PROP_MONITOR_NICK = 'xmpp.monitor.nick'
"""
Nickname used by the Monitor Bot in the Multi-User Chat
"""


# ------------------------------------------------------------------------------

FACTORY_TRANSPORT = "herald-xmpp-transport-factory"
"""
Name of the XMPP transport implementation factory
"""

FACTORY_MONITOR = "herald-xmpp-monitor-factory"
"""
Name of the XMPP monitor bot wrapper component factory
"""
