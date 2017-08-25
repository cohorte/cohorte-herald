#!/usr/bin/python
# -- Content-Encoding: UTF-8 --
"""
Herald Core service

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


class HeraldException(Exception):
    """
    Base class for all exceptions in Herald
    """
    def __init__(self, target, text, cause=None):
        """
        Sets up the exception

        :param target: A Target bean
        :param text: A description of the error
        :param cause: The cause of the error
        """
        super(HeraldException, self).__init__(text)
        self.target = target
        self.cause = cause


class NoTransport(HeraldException):
    """
    No transport has been found to contact the targeted peer
    """
    pass


class InvalidPeerAccess(HeraldException):
    """
    The description of an access to peer can't be read by the access handler
    """
    pass


class PeerLost(HeraldException):
    """
    A peer has been lost while we were waiting for it
    """
    pass


class HeraldTimeout(HeraldException):
    """
    A timeout has been reached
    """
    def __init__(self, target, text, message):
        """
        Sets up the exception

        :param text: Description of the exception
        :param message: The request which got no reply
        """
        super(HeraldTimeout, self).__init__(target, text)
        self.message = message


class NoListener(HeraldException):
    """
    The message has been received by the remote peer, but no listener has been
    found to register it.
    """
    def __init__(self, target, uid, subject):
        """
        Sets up the exception

        :param target: Target peer with no listener
        :param uid: Original message UID
        :param subject: Subject of the original message
        """
        super(NoListener, self).__init__(
            target, "No listener for {0} ({1})".format(uid, subject))
        self.uid = uid
        self.subject = subject


class ForgotMessage(HeraldException):
    """
    Exception given to callback methods waiting for a message that has been
    declared to be forgotten by forget().
    """
    def __init__(self, uid):
        """
        Sets up the exception

        :param uid: UID of the forgotten message
        """
        super(ForgotMessage, self).__init__(None, "Forgot message {0}"
                                            .format(uid))
        self.uid = uid
