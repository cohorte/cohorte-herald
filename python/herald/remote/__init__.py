#!/usr/bin/python
# -- Content-Encoding: UTF-8 --
"""
Pelix Remote Services implementation based on Herald

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

# Documentation strings format
__docformat__ = "restructuredtext en"

# ------------------------------------------------------------------------------

FACTORY_DISCOVERY = 'herald-remote-discovery-factory'
"""
Name of the Herald Remote Services discovery component factory
"""

FACTORY_HERALD_XMLRPC_EXPORTER = 'herald-rpc-exporter-xmlrpc-factory'
"""
Name of the component factory for the xmlrpclib-based exporter
"""

FACTORY_HERALD_XMLRPC_IMPORTER = 'herald-rpc-importer-xmlrpc-factory'
"""
Name of the component factory for the xmlrpclib-based importer
"""

FACTORY_HERALD_JSONRPC_EXPORTER = 'herald-rpc-exporter-jsonrpc-factory'
"""
Name of the component factory for the jsonrpclib-based exporter
"""

FACTORY_HERALD_JSONRPC_IMPORTER = 'herald-rpc-importer-jsonrpc-factory'
"""
Name of the component factory for the jsonrpclib-based importer
"""

PROP_TARGET_GROUP = 'herald.rpc.target.group'
"""
Name of group to whom a discovery message is sent.
"""

DEFAULT_TARGET_GROUP = 'all'
"""
Default name of group to whom a discovery message is sent.
"""
