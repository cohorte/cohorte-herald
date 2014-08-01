#!/usr/bin/python
# -- Content-Encoding: UTF-8 --
"""
Herald Core service
"""

# Herald
import herald

# Pelix
from pelix.ipopo.decorators import ComponentFactory, Provides, Property, \
    Instantiate

# Standard library
import logging

# ------------------------------------------------------------------------------

_logger = logging.getLogger(__name__)

# ------------------------------------------------------------------------------


@ComponentFactory("herald-client-factory")
@Provides(herald.SERVICE_LISTENER)
@Property('_filters', herald.PROP_FILTERS, ('/hello/*', 'titi/toto'))
@Instantiate("herald-client")
class Herald(object):
    """
    Herald core service
    """
    def __init__(self):
        """
        Sets up members
        """
        # Filters
        self._filters = None

    def herald_message(self, herald_svc, message):
        """
        A message has been received
        """
        _logger.info("Client got message: %s", message.subject)
        if message.subject.startswith('/hello/'):
            name = message.subject.split('/')[2]
            herald_svc.reply(message, "Hello, {0}".format(name.title()))
