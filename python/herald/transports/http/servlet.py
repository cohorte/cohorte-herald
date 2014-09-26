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
__version_info__ = (0, 0, 2)
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
    Property, Validate
from pelix.utilities import to_bytes, to_unicode
import pelix.http
import pelix.misc.jabsorb as jabsorb

# Standard library
import json
import logging
import threading

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
        self._can_provide = False
        self.__lock = threading.Lock()

        # Local information
        self._host = None
        self._port = None
        self._servlet_path = None

    @Validate
    def validate(self, context):
        """
        Component validated
        """
        # Normalize the servlet path
        if not self._servlet_path.startswith('/'):
            self._servlet_path = '/' + self._servlet_path

    def get_access_info(self):
        """
        Retrieves the (host, port) tuple to access this signal receiver.

        WARNING: The host might (often) be "localhost"

        :return: An (host, port, path) tuple
        """
        return self._host, self._port, self._servlet_path

    def __set_controller(self):
        """
        Sets the service controller to True if possible
        """
        with self.__lock:
            self._controller = self._can_provide

    def bound_to(self, path, parameters):
        """
        Servlet bound to a HTTP service

        :param path: The path to access the servlet
        :param parameters: The server & servlet parameters
        """
        if self._host is None and path == self._servlet_path:
            # Update our access information
            self._host = parameters[pelix.http.PARAM_ADDRESS]
            self._port = int(parameters[pelix.http.PARAM_PORT])

            # Tell the directory we're ready
            access = beans.HTTPAccess(self._host, self._port, path)
            self._directory.get_local_peer().set_access(ACCESS_ID, access)

            with self.__lock:
                # Register our service: use a different thread to let the
                # HTTP service register this servlet
                self._can_provide = True
                threading.Thread(target=self.__set_controller,
                                 name="Herald-HTTP-Servlet-Bound").start()
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
            with self.__lock:
                # Lock next provide
                self._can_provide = False

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
        jabsorb_content = jabsorb.to_jabsorb(peer_dump)
        content = json.dumps(jabsorb_content, default=utils.json_converter)
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
            # Unknown content type -> Error 412 "Precondition failed"
            _logger.critical("Bad content type: %s", content_type)
            code, content = _make_json_result(412, "Unknown content type")

        else:
            # Extract headers
            subject = request.get_header('herald-subject')
            uid = request.get_header('herald-uid')
            reply_to = request.get_header('herald-reply-to')
            timestamp = request.get_header('herald-timestamp')
            sender_uid = request.get_header('herald-sender-uid')
            json_content = to_unicode(request.read_data())
            msg_content = jabsorb.from_jabsorb(json.loads(json_content))

            # Store sender information
            host = request.get_client_address()[0]
            port = int(request.get_header('herald-port', 80))
            extra = {'host': host, 'port': port,
                     'path': request.get_header('herald-path'),
                     'parent_uid': uid}

            try:
                # Check the sender UID port
                # (not perfect, but can avoid spoofing)
                if not self._http_directory.check_access(sender_uid,
                                                         host, port):
                    # Port doesn't match: invalid UID
                    sender_uid = "<invalid>"
            except ValueError as ex:
                # Unknown peer UID: keep it as is
                pass

            # Let Herald handle the message
            message = herald.beans.MessageReceived(uid, subject, msg_content,
                                                   sender_uid, reply_to,
                                                   ACCESS_ID, timestamp, extra)
            self._core.handle_message(message)

        # Convert content (Python 3)
        if content:
            content = jabsorb.to_jabsorb(content)

        content = to_bytes(content)

        # Send response
        response.send_content(code, content, CONTENT_TYPE_JSON)
