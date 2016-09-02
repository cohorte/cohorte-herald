#!/usr/bin/python
# -- Content-Encoding: UTF-8 --
"""
Herald HTTP transport implementation

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

# Module version
__version_info__ = (1, 0, 0)
__version__ = ".".join(str(x) for x in __version_info__)

# Documentation strings format
__docformat__ = "restructuredtext en"

# ------------------------------------------------------------------------------

# Herald HTTP
from . import ACCESS_ID, SERVICE_HTTP_RECEIVER, SERVICE_HTTP_TRANSPORT, \
    CONTENT_TYPE_JSON

# HTTP requests
import requests.exceptions

# Herald Core
from herald.exceptions import InvalidPeerAccess
import herald
import herald.beans as beans
import herald.utils as utils
import herald.transports.http

# Pelix
from pelix.ipopo.decorators import ComponentFactory, Requires, Provides, \
    Property, BindField, Validate, Invalidate, Instantiate, RequiresBest
from pelix.utilities import to_str
import pelix.utilities
import pelix.threadpool
import pelix.misc.jabsorb as jabsorb

# Standard library
import json
import logging
import time

# ------------------------------------------------------------------------------

_logger = logging.getLogger(__name__)

# ------------------------------------------------------------------------------


@ComponentFactory('herald-http-transport-factory')
@RequiresBest('_probe', herald.SERVICE_PROBE)
@Requires('_directory', herald.SERVICE_DIRECTORY)
@Requires('_local_recv', SERVICE_HTTP_RECEIVER)
@Provides((herald.SERVICE_TRANSPORT, SERVICE_HTTP_TRANSPORT))
@Property('_access_id', herald.PROP_ACCESS_ID, ACCESS_ID)
@Instantiate('herald-http-transport')
class HttpTransport(object):
    """
    HTTP sender for Herald.
    """
    def __init__(self):
        """
        Sets up the transport
        """
        # Herald Core directory
        self._directory = None

        # Debug probe
        self._probe = None

        # Properties
        self._access_id = ACCESS_ID

        # Local UID
        self.__peer_uid = None

        # Request send pool
        self.__pool = pelix.threadpool.ThreadPool(5, logname="herald-http")

        # Requests session
        self.__session = requests.Session()

        # Local access information
        self.__access_port = None
        self.__access_path = None

    @BindField('_local_recv')
    def _bind_local_receiver(self, _, service, svc_ref):
        """
        The local receiver has been bound
        """
        access = service.get_access_info()
        self.__access_port = access[1]
        self.__access_path = access[2]

    @Validate
    def _validate(self, _):
        """
        Component validated
        """
        self.__peer_uid = self._directory.local_uid
        self.__session = requests.Session()
        self.__session.stream = False
        self.__pool.start()

    @Invalidate
    def _invalidate(self, _):
        """
        Component invalidated
        """
        self.__peer_uid = None
        self.__session.close()
        self.__pool.stop()

    def __get_access(self, peer, extra=None):
        """
        Computes the URL to access the Herald servlet on the given peer

        :param peer: A Peer bean
        :param extra: Extra information, given for replies
        :return: A URL, or None
        """
        host = None
        port = 0
        path = None
        if extra is not None:
            # Try to use extra information
            host = extra.get('host')
            port = extra.get('port')
            path = extra.get('path')

        if not host:
            try:
                # Use the directory
                host, port, path = peer.get_access(ACCESS_ID).access
            except (KeyError, AttributeError):
                # Invalid access: stop here
                return None

        # Normalize arguments
        if ':' in host:
            # IPv6 address
            host = '[{0}]'.format(host)

        if port == 0:
            port = 80

        if path[0] == '/':
            path = path[1:]

        return 'http://{0}:{1}/{2}'.format(host, port, path)

    def __prepare_message(self, message, parent_uid=None, target_peer=None, target_group=None):
        """
        Prepares a HTTP request.

        :param message: The Message bean to send
        :param parent_uid: UID of the message this one replies to (optional)
        :return: A (headers, content) tuple
        """
        # Prepare headers
        """
        headers = {'content-type': CONTENT_TYPE_JSON,
                   'herald-subject': message.subject,
                   'herald-uid': message.uid,
                   'herald-sender-uid': self.__peer_uid,
                   'herald-timestamp': int(time.time() * 1000),
                   'herald-port': self.__access_port,
                   'herald-path': self.__access_path}
        """
        headers = {'content-type': CONTENT_TYPE_JSON} 
        message.add_header(herald.MESSAGE_HEADER_SENDER_UID, self.__peer_uid)
        message.add_header(herald.transports.http.MESSAGE_HEADER_PORT, self.__access_port)
        message.add_header(herald.transports.http.MESSAGE_HEADER_PATH, self.__access_path)
        if parent_uid:
            #headers['herald-reply-to'] = parent_uid
            message.add_header(herald.MESSAGE_HEADER_REPLIES_TO, parent_uid)
        # update target peer header
        if target_peer is not None:
            message.add_header(herald.MESSAGE_HEADER_TARGET_PEER, target_peer.uid) 
        # update target peer header
        if target_group is not None:
            message.add_header(herald.MESSAGE_HEADER_TARGET_GROUP, target_group)     
        if message.subject in herald.SUBJECTS_RAW:
            content = utils.to_str(message.content)
        else:
            # Convert content to JSON
            content = utils.to_json(message)
            
        return headers, content

    def __post_message(self, url, content, headers):
        """
        Method called directly or in a thread to send a POST HTTP request

        :param url: Target URL
        :param content: Request body
        :param headers: Request headers
        :return: A response bean
        """
        try:
            return self.__session.post(url, content, headers=headers)
        except requests.exceptions.ConnectionError as ex:
            # Connection aborted during request
            _logger.error("Connection error while posting a message: %s", ex)
            return None

    def fire(self, peer, message, extra=None):
        """
        Fires a message to a peer

        :param peer: A Peer bean
        :param message: Message bean to send
        :param extra: Extra information used in case of a reply
        :raise InvalidPeerAccess: No information found to access the peer
        :raise Exception: Error sending the request or on the server side
        """
        # Get the request message UID, if any
        parent_uid = None
        if extra is not None:
            parent_uid = extra.get('parent_uid')

        # Try to read extra information
        url = self.__get_access(peer, extra)
        if not url:
            # No HTTP access description
            raise InvalidPeerAccess(beans.Target(peer=peer),
                                    "No '{0}' access found"
                                    .format(self._access_id))           
        # Send the HTTP request (blocking) and raise an error if necessary
        headers, content = self.__prepare_message(message, parent_uid, target_peer=peer)

        # Log before sending
        self._probe.store(
            herald.PROBE_CHANNEL_MSG_SEND,
            {"uid": message.uid, "timestamp": time.time(),
             "transport": ACCESS_ID, "subject": message.subject,
             "target": peer.uid if peer else "<unknown>",
             "transportTarget": url, "repliesTo": parent_uid or ""})

        self._probe.store(
            herald.PROBE_CHANNEL_MSG_CONTENT,
            {"uid": message.uid, "content": content}
        )

        response = self.__post_message(url, content, headers)
        if response is None:
            # The error has been logged in post_message
            raise IOError("Error sending message {0}".format(message.uid))
        else:
            # Raise an error if the status isn't 2XX
            response.raise_for_status()

    def fire_group(self, group, peers, message):
        """
        Fires a message to a group of peers

        :param group: Name of a group
        :param peers: Peers to communicate with
        :param message: Message to send
        :return: The list of reached peers

        """
        # Prepare the message
        headers, content = self.__prepare_message(message, target_group=group)

        # The list of peers having been reached
        accessed_peers = set()
        countdown = pelix.utilities.CountdownEvent(len(peers))

        def peer_result(_, exception, target_peer):
            """
            Called back once the request has been posted
            """
            if exception is None:
                # No exception => success
                accessed_peers.add(target_peer)

            # In any case: update the count down
            countdown.step()

        # Store the message once
        self._probe.store(
            herald.PROBE_CHANNEL_MSG_CONTENT,
            {"uid": message.uid, "content": content}
        )

        # Send a request to each peers
        for peer in peers:

            # Try to read extra information
            url = self.__get_access(peer)
            if url:
                # Log before sending
                self._probe.store(
                    herald.PROBE_CHANNEL_MSG_SEND,
                    {"uid": message.uid, "timestamp": time.time(),
                     "transport": ACCESS_ID, "subject": message.subject,
                     "target": peer.uid, "transportTarget": url,
                     "repliesTo": ""})

                # Send the HTTP requests (from the thread pool)
                future = self.__pool.enqueue(self.__post_message,
                                             url, content, headers)
                future.set_callback(peer_result, peer)
            else:
                # No HTTP access description
                _logger.debug("No '%s' access found for %s", self._access_id,
                              peer)

        # Wait for the requests to be sent (no more than 30s)
        if not countdown.wait(10):
            _logger.warning("Not all peers have been reached after 10s...")

        return set(accessed_peers)
