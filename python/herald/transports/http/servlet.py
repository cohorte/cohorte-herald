#!/usr/bin/python
# -- Content-Encoding: UTF-8 --
"""
Herald HTTP transport servlet

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
__version_info__ = (0, 0, 1)
__version__ = ".".join(str(x) for x in __version_info__)

# Documentation strings format
__docformat__ = "restructuredtext en"

# ------------------------------------------------------------------------------

# Herald
from . import ACCESS_ID, SERVICE_HTTP_DIRECTORY, SERVICE_HTTP_RECEIVER, \
    FACTORY_SERVLET
from . import beans
import herald.beans
import herald.utils as utils

# Pelix
from pelix.ipopo.decorators import ComponentFactory, Requires, Provides, \
    Property
from pelix.utilities import to_bytes, to_unicode
import pelix.http

# Standard library
import json
import logging

# ------------------------------------------------------------------------------

CONTENT_TYPE_JSON = "application/json"
""" MIME type: JSON data """

_logger = logging.getLogger(__name__)

# ------------------------------------------------------------------------------


def _make_json_result(code, message="", results=None):
    """
    An utility method to prepare a JSON result string, usable by the
    SignalReceiver

    :param code: A HTTP Code
    :param message: An associated message
    """
    return code, json.dumps({'code': code,
                             'message': message,
                             'results': results})


@ComponentFactory(FACTORY_SERVLET)
@Requires('_core', herald.SERVICE_HERALD_INTERNAL)
@Requires('_directory', herald.SERVICE_DIRECTORY)
@Requires('_http_directory', SERVICE_HTTP_DIRECTORY)
@Provides(pelix.http.HTTP_SERVLET)
@Provides(SERVICE_HTTP_RECEIVER, '_controller')
@Property('_servlet_path', pelix.http.HTTP_SERVLET_PATH, '/herald')
class HeraldServlet(object):
    """
    HTTP reception servlet
    """
    def __init__(self):
        """
        Sets up the servlet
        """
        # Herald services
        self._core = None
        self._directory = None

        # Herald HTTP directory
        self._http_directory = None

        # Service controller (set once bound)
        self._controller = False

        # Local information
        self._host = None
        self._port = None
        self._servlet_path = None

    def get_access_info(self):
        """
        Retrieves the (host, port) tuple to access this signal receiver.

        WARNING: The host might (often) be "localhost"

        :return: An (host, port, path) tuple
        """
        return (self._host, self._port, self._servlet_path)

    def bound_to(self, path, parameters):
        """
        Servlet bound to a HTTP service

        :param path: The path to access the servlet
        :param parameters: The server & servlet parameters
        """
        if self._host is None and path == self._servlet_path:
            # Update our access informations
            self._host = parameters[pelix.http.PARAM_ADDRESS]
            self._port = int(parameters[pelix.http.PARAM_PORT])

            # Tell the directory we're ready
            access = beans.HTTPAccess(self._host, self._port, path)
            self._directory.get_local_peer().set_access(ACCESS_ID, access)

            # Register our service
            self._controller = True
            return True
        else:
            return False

    def unbound_from(self, path, parameters):
        """
        Servlet unbound from a HTTP service

        :param path: The path to access the servlet
        :param parameters: The server & servlet parameters
        """
        if path == self._servlet_path:
            # Unregister our service
            self._controller = False

            # Update the directory
            self._directory.get_local_peer().unset_access(ACCESS_ID)

            # Clear our access information
            self._host = None
            self._port = None

    def do_GET(self, request, response):
        """
        Handles a GET request: sends the description of the local peer

        :param request: The HTTP request bean
        :param response: The HTTP response handler
        """
        # pylint: disable=C0103
        peer_dump = self._directory.get_local_peer().dump()
        content = json.dumps(peer_dump, default=utils.json_converter)
        response.send_content(200, content, CONTENT_TYPE_JSON)

    def do_POST(self, request, response):
        """
        Handles a POST request, i.e. the reception of a message

        :param request: The HTTP request bean
        :param response: The HTTP response handler
        """
        # pylint: disable=C0103
        # Default code and content
        code = 200
        content = ""

        # Check content type
        content_type = request.get_header('content-type')
        if content_type not in (None, CONTENT_TYPE_JSON):
            # Unknown content type
            code, content = _make_json_result(500, "Unknown content type")

        else:
            # Extract headers
            subject = request.get_header('herald-subject')
            uid = request.get_header('herald-uid')
            reply_to = request.get_header('herald-reply-to')
            timestamp = request.get_header('herald-timestamp')
            json_content = json.loads(to_unicode(request.read_data()))

            # Store sender information
            extra = {'host': request.get_client_address()[0],
                     'port': int(request.get_header('herald-port', 80)),
                     'path': request.get_header('herald-path'),
                     'parent_uid': uid}

            try:
                # Look for the sender UID from the directory
                sender_uid = self._http_directory.from_address(extra['host'],
                                                               extra['port'])
            except KeyError:
                sender_uid = "<unknown>"

            # Let Herald handle the message
            message = herald.beans.MessageReceived(uid, subject, json_content,
                                                   sender_uid, reply_to,
                                                   ACCESS_ID, timestamp, extra)
            self._core.handle_message(message)

        # Convert content (Python 3)
        content = to_bytes(content)

        # Send response
        response.send_content(code, content, CONTENT_TYPE_JSON)
