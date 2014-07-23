#!/usr/bin/python
# -- Content-Encoding: UTF-8 --
"""
Herald core beans definition
"""

# Standard library
import time
import uuid

# ------------------------------------------------------------------------------

class Message(object):
    """
    Represents a message in Herald
    """
    def __init__(self, subject, content=None):
        """
        Sets up members

        :param subject: Subject of the message
        :param content: Content of the message (optional)
        """
        self._subject = subject
        self._content = content
        self._timestamp = int(time.time() * 1000)
        self._uid = str(uuid.uuid4())

    @property
    def subject(self):
        """
        The subject of the message
        """
        return self._subject

    @property
    def content(self):
        """
        The content of the message
        """
        return self._content

    @property
    def timestamp(self):
        """
        Timestamp of the message
        """
        return self._timestamp

    @property
    def uid(self):
        """
        Message UID
        """
        return self._uid
