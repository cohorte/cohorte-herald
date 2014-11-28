Herald
******

Herald is an easy-to-use messaging framework.
It allows Pelix/iPOPO and Java OSGi frameworks to communicate with each other
using messages, without worrying about the underlying protocol used for
transmission.


Concepts
========

Each Pelix or OSGi framework instance is considered as a *peer*.
A peer has a unique ID and a human-readable name.
An application ID is associated to each peer: only peers with the same
application ID can discover each other.

A peer can send a message to another peer or to a group of peers.
A message has a subject, which listeners register to, and a content.


Remote Services
===============

Herald provides an RPC transport implementations for Pelix Remote Services
(Python) and for
`Cohorte Remote Services <https://github.com/isandlaTech/cohorte-remote-services>`_
(Java).


Transports
==========

Currently, Herald supports two protocols in Python, and one in Java:

* HTTP (Python & Java):

  * Each message is sent as a POST request.
  * Peer discovery is based on a home-made multicast heart beat protocol
  * Best transport for LAN applications and for single-peer messages
  * Python implementation is based on
    `requests <http://docs.python-requests.org/>`_.
  * Java implementation uses the builtin HTTP client. It requires the
    `Felix HTTP service <http://felix.apache.org/documentation/subprojects/apache-felix-http-service.html>`_
    to work correctly.

* XMPP (Python & Java):

  * Each message is a either a message or a group message
  * Discovery is based on a Multi-User Chat room (XEP-0045)
  * Best transport for distributed applications and for group messages
  * Python implementation is based on `SleekXMPP <http://sleekxmpp.com/>`_


License
=======

Cohorte Herald is released under the terms of the Apache Software License 2.0.
