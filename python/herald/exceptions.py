#!/usr/bin/python
# -- Content-Encoding: UTF-8 --
"""
Herald Core service
"""


class HeraldException(Exception):
    """
    Base class for all exceptions in Herald
    """
    pass


class HeraldTimeout(HeraldException):
    """
    A timeout has been reached
    """
    def __init__(self, text, message):
        """
        Sets up the exception

        :param text: Description of the exception
        :param message: The request which got no reply
        """
        super(HeraldException, self).__init__(text)
        self.message = message


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
