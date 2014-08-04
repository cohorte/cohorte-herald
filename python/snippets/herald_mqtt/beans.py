"""
Beans definition
"""

import threading
import json

class Peer(object):
    """
    Decription of a peer
    """
    def __init__(self):
        # UUID of the peer
        self.peer_id = ""

        # Names of the groups including this peer
        self.groups = set()

        # Accesses to the peer
        self.accesses = []

# ------------------------------------------------------------------------------

class Future(object):
    """
    An object to wait for the result of a threaded execution
    """
    def __init__(self):
        """
        Sets up the FutureResult object
        """
        self._done_event = threading.Event()
        self._result = None
        self._exception = None


    def execute(self, method, args, kwargs):
        """
        Execute the given method and stores its result.
        The result is considered "done" even if the method raises an exception

        :param method: The method to execute
        :param args: Method positional arguments
        :param kwargs: Method keyword arguments
        :raise Exception: The exception raised by the method
        """
        # Normalize arguments
        if args is None:
            args = []

        if kwargs is None:
            kwargs = {}

        try:
            # Call the method
            self._result = method(*args, **kwargs)

        except Exception as ex:
            self._exception = ex
            raise

        finally:
            # Mark the action as executed
            self._done_event.set()


    def done(self):
        """
        Returns True if the job has finished, else False
        """
        return self._done_event.is_set()


    def result(self, timeout=None):
        """
        Waits up to timeout for the result the threaded job.
        Returns immediately the result if the job has already been done.

        :param timeout: The maximum time to wait for a result (in seconds)
        :raise OSError: The timeout raised before the job finished
        :raise Exception: Raises the exception that occurred executing
                          the method
        """
        if self._done_event.wait(timeout) or self._done_event.is_set():
            if self._exception is not None:
                raise self._exception

            return self._result

        raise OSError("Timeout raised")

# ------------------------------------------------------------------------------

class AbstractPeerAccess(object):
    """
    Describes the access to a peer
    """
    def __init__(self):
        # UUID of the associated peer
        self.peer_id = ""
        self.type = ""

class TCPAccess(AbstractPeerAccess):
    """
    TCP access to a peer
    """
    def __init__(self):
        # Parent attributes
        super(TCPAccess, self).__init__()
        self.type = "tcp"

        # Host name/IP
        self.host = ""

        # Access port
        self.port = 0

class HTTPAccess(TCPAccess):
    """
    HTTP Signals access
    """
    def __init__(self):
        super(HTTPAccess, self).__init__()
        self.type = "http"

class UDPAccess(TCPAccess):
    """
    UDP access to a peer: same as TCP
    """
    def __init__(self):
        super(UDPAccess, self).__init__()
        self.type = "udp"

class MQTTAccess(AbstractPeerAccess):
    """
    MQTT access to a peer
    """
    def __init__(self):
        # Parent attributes
        super(MQTTAccess, self).__init__()
        self.type = "mqtt"

        # MQTT Server access (TCPAccess)
        self.server = None

        # Heartbeat
        self.keepalive = 60

        # Topic (pattern)
        self.topic = ""

# ------------------------------------------------------------------------------

class RawMessage(object):
    """
    Describes the message sent by the herald
    """
    def __init__(self):
        # Message topic (URI like)
        self.topic = ""

        # Message content (user-defined)
        self._content = None

    @property
    def content(self):
        """
        Returns the content that will be sent in the message
        """
        return self._content

    def serialize(self):
        """
        Returns raw content, as is
        """
        return self.content


class JsonMessage(RawMessage):
    """
    A message with some extra informations, serialized in JSON
    """
    def __init__(self):
        super(JsonMessage, self).__init__()

        # Message UID
        self.uid = ""

        # Timestamp
        self.timestamp = 0

    @property
    def content(self):
        """
        Returns the content that will be sent in the message
        """
        return {'uid': self.uid,
                'timestamp': self.timestamp,
                'content': self._content}

    def serialize(self):
        """
        Returns raw content, as is
        """
        return json.dumps(self.content)

# ------------------------------------------------------------------------------

class AbstractRouter(object):
    """
    Represents a router, requesting links to protocols
    """
    def __init__(self):
        # Available protocol handlers
        self._protocols = []

    def get_link(self, peer):
        """
        Retrieves a link to the peer

        :param peer: A Peer description
        :return: A link to the peer, None if none available
        """
        assert isinstance(peer, Peer)

        for protocol in self._protocols:
            try:
                # Try to get a link
                return protocol.get_link(peer)

            except ValueError:
                # Peer can't be handled by this protocol
                pass

        # No link found
        return None

# ------------------------------------------------------------------------------

class AbstractProtocol(object):
    """
    Represents a protocol provider, used by routers to give links to peers
    """
    def get_link(self, peer):
        """
        Returns a link to the given peer

        :param peer: A Peer description
        :return: A link to the peer
        :raise ValueError: Invalid access to the peer
        """
        raise NotImplementedError

# ------------------------------------------------------------------------------

class AbstractLink(object):
    """
    Represents a link to a peer
    """
    def send(self, message):
        """
        Sends a message (synchronous)

        :param message: Message to send
        :return: Message response(s)
        """
        future = self.post(message)
        future.join()
        return future.result


    def post(self, message):
        """
        Posts a message (asynchronous)

        :param message: Message to send
        :return: Message response(s)
        """
        raise NotImplementedError


    def fire(self, message):
        """
        Fires a message (fire & forget)

        :param message: Message to fire
        """
        raise NotImplementedError
