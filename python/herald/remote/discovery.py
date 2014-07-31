#!/usr/bin/python
# -- Content-Encoding: UTF-8 --
"""
Herald Remote Services discovery
"""

# Herald
import herald

# Pelix
from pelix.ipopo.decorators import ComponentFactory, Requires, Provides, \
    Property, Validate
import pelix.remote.beans

# Standard library
import logging

# ------------------------------------------------------------------------------

_logger = logging.getLogger(__name__)

# ------------------------------------------------------------------------------


@ComponentFactory(pelix.remote.FACTORY_DISCOVERY_MULTICAST)
@Provides(pelix.remote.SERVICE_EXPORT_ENDPOINT_LISTENER)
@Provides(herald.SERVICE_LISTENER)
@Requires('_directory', herald.SERVICE_DIRECTORY)
@Requires('_herald', herald.SERVICE_HERALD)
@Requires('_dispatcher', pelix.remote.SERVICE_DISPATCHER)
@Requires('_registry', pelix.remote.SERVICE_REGISTRY)
@Property('_filters', herald.PROP_FILTERS, ['herald/rpc/discovery/*'])
class HeraldDiscovery(object):
    """
    Remote services discovery and notification using Herald
    """
    def __init__(self):
        """
        Sets up the component
        """
        # Herald
        self._herald = None
        self._directory = None

        # Pelix Remote Services
        self._dispatcher = None
        self._registry = None

    def _dump_endpoint(self, endpoint):
        """
        Converts an ExportEndpoint bean to a dictionary.

        :param endpoint: An ExportEndpoint bean
        :return: A dictionary
        """
        dump = {key: getattr(endpoint, key)
                for key in ("uid", "configurations", "name", "specifications")}

        # Send import-side properties
        dump['properties'] = endpoint.make_import_properties()
        dump['peer'] = self._directory.local_uid
        return dump

    def _dump_endpoints(self, endpoints):
        """
        Converts a list of ExportEndpoint beans to a list of dictionaries

        :param endpoints: A list of endpoints
        :return: A list of dictionaries
        """
        return [self._dump_endpoint(endpoint) for endpoint in endpoints]

    def _load_endpoint(self, endpoint_dict):
        """
        Make an ImportEndpoint bean from the result of a call to
        _dump_endpoint()

        :param endpoint_dict: The result of a call to _dump_endpoint(),
                              sent over Herald
        :return: An ImportEndpoint bean
        :raise KeyError: Incomplete dump
        """
        return pelix.remote.beans.ImportEndpoint(
            endpoint_dict['uid'],
            endpoint_dict['peer'],
            endpoint_dict['configurations'],
            endpoint_dict['name'],
            endpoint_dict['specifications'],
            endpoint_dict['properties'])

    def __subject(self, kind):
        """
        Prepares a subject for Herald discovery

        :return: A subject string that can be handled by Herald Discovery
        """
        return '/'.join(('herald', 'rpc', 'discovery', kind))

    @Validate
    def _validate(self, context):
        """
        Component validated
        """
        # Send a discovery signal
        endpoints = self._dump_endpoints(self._dispatcher.get_endpoints)
        self._herald.fire_group('all', self.__subject("discovery"), endpoints)

    def herald_message(self, herald_svc, message):
        """
        An Herald message has been received
        """
        kind = message.subject.rsplit('/', 1)[1]
        if kind == 'add':
            # Register the new endpoints
            for endpoint_dict in message.content:
                try:
                    endpoint = self._load_endpoint(endpoint_dict)
                    self._registry.add(endpoint)
                except KeyError as ex:
                    _logger.error("Unreadable endpoint from %s: missing %s",
                                  message.sender, ex)

        elif kind == 'remove':
            # Message only contains the UID of the endpoint
            self._registry.remove(message.content['uid'])

        elif kind == 'update':
            # Update the endpoint
            endpoint_uid = message.content['uid']
            new_properties = message.content['properties']
            self._registry.update(endpoint_uid, new_properties)

        elif kind == 'discovery':
            # Reply with the whole list of our exported endpoints
            endpoints = self._dump_endpoints(self._dispatcher.get_endpoints)
            herald_svc.reply(message, endpoints, self.__subject("discovered"))

    def endpoints_add(self, endpoints):
        """
        Multiple endpoints have been created

        :param endpoints: A list of ExportEndpoint beans
        """
        self._herald.fire_group("all", self.__subject("add"),
                                self._dump_endpoints(endpoints))

    def endpoint_updated(self, endpoint, old_properties):
        """
        An endpoint has been updated

        :param endpoint: An updated ExportEndpoint bean
        :param old_properties: Previous value of the endpoint properties
        """
        self._herald.fire_group("all", self.__subject("update"),
                                {"uid": endpoint.uid,
                                 "properties":
                                 endpoint.make_import_properties()})

    def endpoint_removed(self, endpoint):
        """
        An endpoint has been removed
        """
        self._herald.fire_group("all", self.__subject("remove"),
                                {"uid": endpoint.uid})
