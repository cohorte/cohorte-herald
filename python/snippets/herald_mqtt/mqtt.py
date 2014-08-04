"""
MQTT provider for Herald
"""

import herald.beans as beans
import pelix.misc.mqtt_client as mqtt
import threading

class MQTTRouter(object):
    """
    MQTT Router
    """
    def __init__(self):
        # (host, port) => link
        self._links = {}

        self.__lock = threading.Lock()


    def get_link(self, peer):
        """
        Retrieves the link to the given peer
        """
        for access in peer.accesses:
            if access.type == 'mqtt':
                break
        else:
            # No MQTT access found
            return None

        # Get server access tuple
        server = (access.server.host, access.server.port)

        with self.__lock:
            try:
                # Get existing link
                return self._links[server]

            except KeyError:
                # Create a new link
                link = self._links[server] = MQTTLink(access)
                return link


class MQTTLink(object):
    """
    MQTT link
    """
    def __init__(self, peer_access):
        # Store the peer access
        assert isinstance(peer_access, beans.MQTTAccess)
        self._access = peer_access

        # Prepare the MQTT client
        self._client = mqtt.MqttClient(mqtt.MqttClient.generate_id("herald"))

        # Connect to the server
        self._client.connect(self._access.server.host, self._access.server.port,
                             self._access.keepalive)

    def close(self):
        """
        Closes the link
        """
        self._client.disconnect()


    def send(self, message):
        """
        Sends a message
        """
        pass


    def post(self, message):
        """
        Posts a message
        """
        pass
