#!/usr/bin/python
# -- Content-Encoding: UTF-8 --
"""
Herald sample client, for debugging purpose

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
