#!/usr/bin/python
# -- Content-Encoding: UTF-8 --
"""
Herald Core service
"""

class HeraldException(Exception):
    pass

class NoTransport(HeraldException):
    pass

class InvalidPeerAccess(HeraldException):
    pass
