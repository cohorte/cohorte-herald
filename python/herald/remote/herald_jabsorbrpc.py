#!/usr/bin/env python
# -- Content-Encoding: UTF-8 --
"""
Pelix remote services implementation based on Herald messaging,
jsonrpclib-pelix, and using the Jabsorb format

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

# Module version
import herald.remote.herald_jsonrpc

__version_info__ = (0, 0, 1)
__version__ = ".".join(str(x) for x in __version_info__)

# Documentation strings format
__docformat__ = "restructuredtext en"

# ------------------------------------------------------------------------------

# Herald
import herald.beans as beans
import herald.remote
import herald.remote.herald_jsonrpc as herald_jsonrpc

# iPOPO decorators
from pelix.ipopo.decorators import ComponentFactory, Requires, Validate, \
    Invalidate, Property, Provides, Instantiate

# Pelix constants
import pelix.remote
import pelix.remote.transport.commons as commons
import pelix.misc.jabsorb as jabsorb

# Standard library
import logging

# JSON-RPC modules
import jsonrpclib.jsonrpc
from jsonrpclib.SimpleJSONRPCServer import SimpleJSONRPCDispatcher

# ------------------------------------------------------------------------------

HERALDRPC_CONFIGURATION = 'herald-jabsorbrpc'
""" Remote Service configuration constant """

PROP_HERALDRPC_PEER = "herald.rpc.peer"
""" UID of the peer exporting a service """

PROP_HERALDRPC_SUBJECT = 'herald.rpc.subject'
""" Subject to contact the exporter """

SUBJECT_REQUEST = 'herald/rpc/jabsorbrpc'
""" Subject to use for requests """

SUBJECT_REPLY = 'herald/rpc/jabsorbrpc/reply'
""" Subject to use for replies """

_logger = logging.getLogger(__name__)

# ------------------------------------------------------------------------------


class JabsorbRpcDispatcher(herald_jsonrpc.JsonRpcDispatcher):
    """
    A JSON-RPC dispatcher with a custom dispatch method

    Calls the dispatch method given in the constructor
    """
    def _simple_dispatch(self, name, params):
        """
        Dispatch method
        """
        # Normalize parameters
        if params:
            params = [jabsorb.from_jabsorb(param) for param in params]

        # Dispatch like JSON-RPC
        return super(JabsorbRpcDispatcher, self)._simple_dispatch(name, params)


@ComponentFactory(herald.remote.FACTORY_HERALD_JSONRPC_EXPORTER)
@Requires('_directory', herald.SERVICE_DIRECTORY)
# SERVICE_EXPORT_PROVIDER is provided by the parent class
@Provides(herald.SERVICE_LISTENER)
@Property('_filters', herald.PROP_FILTERS, [SUBJECT_REQUEST])
@Property('_kinds', pelix.remote.PROP_REMOTE_CONFIGS_SUPPORTED,
          (HERALDRPC_CONFIGURATION,))
@Instantiate('herald-rpc-exporter-jsonrpc')
class HeraldRpcServiceExporter(commons.AbstractRpcServiceExporter):
    """
    Herald Remote Services exporter
    """
    def __init__(self):
        """
        Sets up the exporter
        """
        # Call parent
        super(HeraldRpcServiceExporter, self).__init__()

        # Herald directory
        self._directory = None

        # Herald filters
        self._filters = None

        # Handled configurations
        self._kinds = None

        # Dispatcher
        self._dispatcher = None

    def make_endpoint_properties(self, svc_ref, name, fw_uid):
        """
        Prepare properties for the ExportEndpoint to be created

        :param svc_ref: Service reference
        :param name: Endpoint name
        :param fw_uid: Framework UID
        :return: A dictionary of extra endpoint properties
        """
        return {PROP_HERALDRPC_PEER: self._directory.local_uid,
                PROP_HERALDRPC_SUBJECT: SUBJECT_REQUEST}

    @Validate
    def validate(self, context):
        """
        Component validated
        """
        # Call parent
        super(HeraldRpcServiceExporter, self).validate(context)

        # Setup the dispatcher (use JSON-RPC ones)
        self._dispatcher = JabsorbRpcDispatcher(self.dispatch)

    @Invalidate
    def invalidate(self, context):
        """
        Component invalidated
        """
        # Call parent
        super(HeraldRpcServiceExporter, self).invalidate(context)

        # Clean up
        self._dispatcher = None

    def herald_message(self, herald_svc, message):
        """
        Received a message from Herald

        :param herald_svc: The Herald service
        :param message: A message bean
        """
        result = self._dispatcher.dispatch(message.content)
        herald_svc.reply(message, jabsorb.to_jabsorb(result), SUBJECT_REPLY)

# ------------------------------------------------------------------------------


class _JsonRpcEndpointProxy(object):
    """
    Proxy to use JSON-RPC over Herald
    """
    def __init__(self, name, peer, subject, send_method):
        """
        Sets up the endpoint proxy

        :param name: End point name
        :param peer: UID of the peer to contact
        :param subject: Subject to use for RPC
        :param send_method: Method to use to send a request
        """
        self.__name = name
        self.__peer = peer
        self.__subject = subject
        self.__send = send_method
        self.__cache = {}

    def __getattr__(self, name):
        """
        Prefixes the requested attribute name by the endpoint name
        """
        return self.__cache.setdefault(
            name, _JsonRpcMethod("{0}.{1}".format(self.__name, name),
                                 self.__peer, self.__subject, self.__send))


class _JsonRpcMethod(object):
    """
    Represents a method in a call proxy
    """
    def __init__(self, method_name, peer, subject, send_method):
        """
        Sets up the method

        :param method_name: Full method name
        :param peer: UID of the peer to contact
        :param subject: Subject to use for RPC
        :param send_method: Method to use to send a request
        """
        self.__name = method_name
        self.__peer = peer
        self.__subject = subject
        self.__send = send_method

    def __call__(self, *args):
        """
        Method is being called
        """
        # Forge the request
        if args:
            args = [jabsorb.to_jabsorb(arg) for arg in args]

        request = jsonrpclib.dumps(args, self.__name, encoding='utf-8')

        # Send it
        reply_message = self.__send(self.__peer, self.__subject, request)

        # Parse the reply and check for errors
        result = jabsorb.from_jabsorb(jsonrpclib.loads(reply_message.content))
        jsonrpclib.jsonrpc.check_for_errors(result)
        return result['result']


@ComponentFactory(herald.remote.FACTORY_HERALD_JSONRPC_IMPORTER)
@Requires('_herald', herald.SERVICE_HERALD)
@Provides(pelix.remote.SERVICE_IMPORT_ENDPOINT_LISTENER)
@Property('_kinds', pelix.remote.PROP_REMOTE_CONFIGS_SUPPORTED,
          (HERALDRPC_CONFIGURATION,))
@Instantiate('herald-rpc-importer-jsonrpc')
class HeraldRpcServiceImporter(commons.AbstractRpcServiceImporter):
    """
    JSON-RPC Remote Services importer
    """
    def __init__(self):
        """
        Sets up the exporter
        """
        # Call parent
        super(HeraldRpcServiceImporter, self).__init__()

        # Herald service
        self._herald = None

        # Component properties
        self._kinds = None

    def __call(self, peer, subject, content):
        """
        Method called by the proxy to send a message over Herald
        """
        return self._herald.send(peer, beans.Message(subject, content))

    def make_service_proxy(self, endpoint):
        """
        Creates the proxy for the given ImportEndpoint

        :param endpoint: An ImportEndpoint bean
        :return: A service proxy
        """
        # Get Peer UID information
        peer_uid = endpoint.properties.get(PROP_HERALDRPC_PEER)
        if not peer_uid:
            _logger.warning("Herald-RPC endpoint without peer UID: %s",
                            endpoint)
            return

        # Get request subject information
        subject = endpoint.properties.get(PROP_HERALDRPC_SUBJECT)
        if not subject:
            _logger.warning("Herald-RPC endpoint without subject: %s",
                            endpoint)
            return

        # Return the proxy
        return _JsonRpcEndpointProxy(endpoint.name, peer_uid, subject,
                                     self.__call)

    def clear_service_proxy(self, endpoint):
        """
        Destroys the proxy made for the given ImportEndpoint

        :param endpoint: An ImportEndpoint bean
        """
        # Nothing to do
        return
