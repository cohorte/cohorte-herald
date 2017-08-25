#!/usr/bin/python
# -- Content-Encoding: UTF-8 --
"""
Herald HTTP transport implementation

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

import threading
import json
import logging

import herald

import pelix.misc.jabsorb as jabsorb



# ------------------------------------------------------------------------------

_logger = logging.getLogger(__name__)

# ------------------------------------------------------------------------------

def json_converter(obj):
    """
    Converts sets to list during JSON serialization
    """
    if isinstance(obj, (set, frozenset)):
        return tuple(obj)

    raise TypeError

def to_json(msg):
    """
    Returns a JSON string representation of this message
    """
    result = {}
    
    # herald specification version
    #result[herald.MESSAGE_HERALD_VERSION] = herald.HERALD_SPECIFICATION_VERSION
    
    # headers
    result[herald.MESSAGE_HEADERS] = {}        
    if msg.headers is not None:
        for key in msg.headers:
            result[herald.MESSAGE_HEADERS][key] = msg.headers.get(key) or None        
    
    # subject
    result[herald.MESSAGE_SUBJECT] = msg.subject
    # content
    if msg.content is not None:
        if isinstance(msg.content, str):
            # string content
            result[herald.MESSAGE_CONTENT] = msg.content
        else:
            # jaborb content
            result[herald.MESSAGE_CONTENT] = jabsorb.to_jabsorb(msg.content)
    
    # metadata
    result[herald.MESSAGE_METADATA] = {}        
    if msg.metadata is not None:
        for key in msg.metadata:
            result[herald.MESSAGE_METADATA][key] = msg.metadata.get(key) or None
            
    return json.dumps(result, default=herald.utils.json_converter)


def from_json(json_string):
    """
    Returns a new MessageReceived from the provided json_string string
    """
    # parse the provided json_message
    try:            
        parsed_msg = json.loads(json_string)            
    except ValueError as ex:            
        # if the provided json_message is not a valid JSON
        return None
    except TypeError as ex:
        # if json_message not string or buffer
        return None
    herald_version = None
    # check if it is a valid Herald JSON message
    if herald.MESSAGE_HEADERS in parsed_msg:
        if herald.MESSAGE_HERALD_VERSION in parsed_msg[herald.MESSAGE_HEADERS]:
            herald_version = parsed_msg[herald.MESSAGE_HEADERS].get(herald.MESSAGE_HERALD_VERSION)                         
    if herald_version is None or herald_version != herald.HERALD_SPECIFICATION_VERSION:
        _logger.error("Herald specification of the received message is not supported!")
        return None   
    # construct new Message object from the provided JSON object    
    msg = herald.beans.MessageReceived(uid=(parsed_msg[herald.MESSAGE_HEADERS].get(herald.MESSAGE_HEADER_UID) or None), 
                          subject=parsed_msg[herald.MESSAGE_SUBJECT], 
                          content=None, 
                          sender_uid=(parsed_msg[herald.MESSAGE_HEADERS].get(herald.MESSAGE_HEADER_SENDER_UID) or None), 
                          reply_to=(parsed_msg[herald.MESSAGE_HEADERS].get(herald.MESSAGE_HEADER_REPLIES_TO) or None), 
                          access=None,
                          timestamp=(parsed_msg[herald.MESSAGE_HEADERS].get(herald.MESSAGE_HEADER_TIMESTAMP) or None) 
                          )                           
    # set content
    try:
        if herald.MESSAGE_CONTENT in parsed_msg:
            parsed_content = parsed_msg[herald.MESSAGE_CONTENT]                              
            if parsed_content is not None:
                if isinstance(parsed_content, str):
                    msg.set_content(parsed_content)
                else:
                    msg.set_content(jabsorb.from_jabsorb(parsed_content))
    except KeyError as ex:
        _logger.error("Error retrieving message content! " + str(ex)) 
    # other headers
    if herald.MESSAGE_HEADERS in parsed_msg:
        for key in parsed_msg[herald.MESSAGE_HEADERS]:
            if key not in msg._headers:
                msg._headers[key] = parsed_msg[herald.MESSAGE_HEADERS][key]         
    # metadata
    if herald.MESSAGE_METADATA in parsed_msg:
        for key in parsed_msg[herald.MESSAGE_METADATA]:
            if key not in msg._metadata:
                msg._metadata[key] = parsed_msg[herald.MESSAGE_METADATA][key] 
                       
    return msg

# ------------------------------------------------------------------------------

try:
    # IPv4/v6 utility methods, added in Python 3.3
    import ipaddress
except ImportError:
    # Module not available
    def normalize_ip(ip_address):
        """
        Should un-map the given IP address. (Does nothing)

        :param ip_address: An IP address
        :return: The given IP address
        """
        return ip_address
else:
    def normalize_ip(ip_address):
        """
        Un-maps the given IP address: if it is an IPv4 address mapped in an
        IPv6 one, the methods returns the IPv4 address

        :param ip_address: An IP address
        :return: The un-mapped IPv4 address or the given address
        """
        try:
            parsed = ipaddress.ip_address(ip_address)
            if parsed.version == 6:
                mapped = parsed.ipv4_mapped
                if mapped is not None:
                    # Return the un-mapped IPv4 address
                    return str(mapped)
        except ValueError:
            # No an IP address: maybe a host name => keep it as is
            pass

        return ip_address

# ------------------------------------------------------------------------------


class LoopTimer(threading.Thread):
    """
    Same as Python's Timer class, but executes the requested method
    again and again, until cancel() is called.
    """
    def __init__(self, interval, function, args=None, kwargs=None, name=None):
        """
        Sets up the timer

        :param interval: Time to wait between calls (in seconds)
        :param function: Function to call
        :param args: Function arguments (as a list)
        :param kwargs: Function keyword arguments (as a dictionary)
        :param name: Name of the loop thread
        """
        threading.Thread.__init__(self, name=name)
        self.daemon = True
        self.interval = interval
        self.function = function
        self.args = args if args is not None else []
        self.kwargs = kwargs if kwargs is not None else {}
        self.finished = threading.Event()

    def cancel(self):
        """
        Cancels the timer if it hasn't finished yet
        """
        self.finished.set()

    def run(self):
        """
        Runs the given method until cancel() is called
        """
        # The "or" part is for Python 2.6
        while not (self.finished.wait(self.interval)
                   or self.finished.is_set()):
            self.function(*self.args, **self.kwargs)
