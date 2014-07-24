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
