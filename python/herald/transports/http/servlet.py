#!/usr/bin/python
# -- Content-Encoding: UTF-8 --
"""
Herald HTTP transport servlet

:author: Thomas Calmant
:copyright: Copyright 2014, isandlaTech
:license: Apache License 2.0
:version: 1.0.1
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

# Bundle version
import herald.version
__version__=herald.version.__version__

# ------------------------------------------------------------------------------

# Herald
from . import ACCESS_ID, SERVICE_HTTP_DIRECTORY, SERVICE_HTTP_RECEIVER, \
    FACTORY_SERVLET, CONTENT_TYPE_JSON
from . import beans
import herald.beans
import herald.transports.peer_contact as peer_contact
import herald.utils as utils
import herald.transports.http

# Pelix
from pelix.ipopo.decorators import ComponentFactory, Requires, Provides, \
    Property, Validate, Invalidate, RequiresBest
from pelix.utilities import to_bytes, to_unicode
import pelix.http
import pelix.misc.jabsorb as jabsorb

# Standard library
import json
import logging
import threading
import time
import uuid

# ------------------------------------------------------------------------------

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
@RequiresBest('_probe', herald.SERVICE_PROBE)
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
        self._probe = None

        # Peer contact handling
        self.__contact = None

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

    @staticmethod
    def __load_dump(message, description):
        """
        Loads and updates the remote peer dump with its HTTP access

        :param message: A message containing a remote peer description
        :param description: The parsed remote peer description
        :return: The peer dump map
        """
        if message.access == ACCESS_ID:
            # Forge the access to the HTTP server using extra information
            extra = message.extra
            description['accesses'][ACCESS_ID] = \
                beans.HTTPAccess(extra['host'], extra['port'],
                                 extra['path']).dump()
        return description

    @Validate
    def validate(self, _):
        """
        Component validated
        """
        # Normalize the servlet path
        if not self._servlet_path.startswith('/'):
            self._servlet_path = '/{0}'.format(self._servlet_path)

        # Prepare the peer contact handler
        self.__contact = peer_contact.PeerContact(
            self._directory, self.__load_dump, __name__ + ".contact")

    @Invalidate
    def invalidate(self, _):
        """
        Component invalidated
        """
        # Clean up internal storage
        self.__contact.clear()
        self.__contact = None

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

    def unbound_from(self, path, _):
        """
        Servlet unbound from a HTTP service

        :param path: The path to access the servlet
        :param _: The server & servlet parameters
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

    def do_GET(self, _, response):
        """
        Handles a GET request: sends the description of the local peer

        :param _: The HTTP request bean
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

        # Extract headers
        """
        content_type = request.get_header('content-type')
        subject = request.get_header('herald-subject')
        uid = request.get_header('herald-uid')
        reply_to = request.get_header('herald-reply-to')
        timestamp = request.get_header('herald-timestamp')
        sender_uid = request.get_header('herald-sender-uid')
        """
        content_type = request.get_header('content-type')
        subject = None
        uid = None
        reply_to = None
        timestamp = None
        sender_uid = None
        
        raw_content = to_unicode(request.read_data())
        
        # Client information
        host = utils.normalize_ip(request.get_client_address()[0])
        
        message = None
        
        if content_type != CONTENT_TYPE_JSON:
            # Raw message
            uid = str(uuid.uuid4())
            subject = herald.SUBJECT_RAW
            #msg_content = raw_content
            msg_content = raw_content
            port = -1
            extra = {'host': host, 'raw': True}     
            
            # construct a new Message bean
            message = herald.beans.MessageReceived(uid, subject, msg_content,
                                               None, None,
                                               ACCESS_ID, None, extra)                  
        else:
            # Herald message
            try:            
                received_msg = utils.from_json(raw_content)                
            except Exception as ex:
                _logger.exception("DoPOST ERROR:: %s", ex)
                
            msg_content = received_msg.content
            
            subject = received_msg.subject
            uid = received_msg.uid
            reply_to = received_msg.reply_to
            timestamp = received_msg.timestamp
            sender_uid = received_msg.sender
            
            if not uid or not subject:
                # Raw message
                uid = str(uuid.uuid4())
                subject = herald.SUBJECT_RAW
                #msg_content = raw_content
                msg_content = raw_content
                port = -1
                extra = {'host': host, 'raw': True}     
                
                # construct a new Message bean
                message = herald.beans.MessageReceived(uid, subject, msg_content,
                                               None, None,
                                               ACCESS_ID, None, extra) 
                
            else:       
                # Store sender information
                try:                 
                    port = int(received_msg.get_header(herald.transports.http.MESSAGE_HEADER_PORT))                    
                except (KeyError, ValueError, TypeError):
                    port = 80
                path = None
                if herald.transports.http.MESSAGE_HEADER_PATH in received_msg.headers:
                    path = received_msg.get_header(herald.transports.http.MESSAGE_HEADER_PATH)                
                extra = {'host': host, 'port': port,
                         'path': path,
                         'parent_uid': uid}
    
                try:
                    # Check the sender UID port
                    # (not perfect, but can avoid spoofing)
                    if not self._http_directory.check_access(
                            sender_uid, host, port):
                        # Port doesn't match: invalid UID
                        sender_uid = "<invalid>"
                except ValueError:
                    # Unknown peer UID: keep it as is
                    pass
            
                # Prepare the bean
                received_msg.add_header(herald.MESSAGE_HEADER_SENDER_UID, sender_uid)
                received_msg.set_access(ACCESS_ID)
                received_msg.set_extra(extra)
                message = received_msg
                           
        # Log before giving message to Herald
        self._probe.store(
            herald.PROBE_CHANNEL_MSG_RECV,
            {"uid": message.uid, "timestamp": time.time(),
             "transport": ACCESS_ID, "subject": message.subject,
             "source": sender_uid, "repliesTo": reply_to or "",
             "transportSource": "[{0}]:{1}".format(host, port)})

        if subject.startswith(peer_contact.SUBJECT_DISCOVERY_PREFIX):
            # Handle discovery message
            self.__contact.herald_message(self._core, message)
        else:
            # All other messages are given to Herald Core
            self._core.handle_message(message)

        # Convert content (Python 3)
        if content:
            content = jabsorb.to_jabsorb(content)

        content = to_bytes(content)

        # Send response
        response.send_content(code, content, CONTENT_TYPE_JSON)
