#!/usr/bin/python
# -- Content-Encoding: UTF-8 --
"""
Herald core service
"""

from .xmpp import transport, monitor

import logging
_logger = logging.getLogger(__name__)

# ------------------------------------------------------------------------------

class Herald(object):
    """
    Herald Core Service
    """
    def __init__(self, transport):
        """
        Sets up members
        """
        self._client = transport


# ------------------------------------------------------------------------------

def main(host):
    monbot = monitor.MonitorBot("bot@phenomtwo3000/monitor", "bot", "Monitor")
    monbot.connect((host, 5222))
    monbot.process(threaded=True)
    monbot.create_rooms(('herald', 'cohorte', 'monitors', 'node'))

    transport = transport.XMPPTransport()
    transport.setup("bot@phenomtwo3000/transport", "bot", "Transport")
    transport.connect((host, 5222))
    transport.process(threaded=True)

    herald = Herald(transport)

    try:
        try:
            raw_input("Press enter to stop...")
        except NameError:
            input("Press enter to stop...")
    except (KeyboardInterrupt, EOFError):
        _logger.debug("Got interruption")

    monbot.disconnect()
    transport.disconnect()
    _logger.info("Bye!")

if __name__ == '__main__':
    import sys
    logging.basicConfig(level=logging.INFO,
                        format='%(levelname)-8s %(message)s')
    logging.debug("Running on Python: %s", sys.version)
    main("127.0.0.1")
