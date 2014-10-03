Cohorte Herald for Python
*************************

Herald is an easy-to-use messaging framework.
It allows Pelix/iPOPO and Java OSGi frameworks to communicate with each other
using messages, without worrying about the underlying protocol used for
transmission.

The project is hosted on GitHub
`isandlaTech/cohorte-herald <https://github.com/isandlaTech/cohorte-herald>`_.
Issues and questions can be posted in
`project Issues section <https://github.com/isandlaTech/cohorte-herald/issues>`_.


Concepts
========

Each Pelix framework instance is considered as a *peer*.
A peer has a unique ID and a human-readable name.
An application ID is associated to each peer: only peers with the same
application ID can discover each other.

A peer can send a message to another peer or to a group of peers.
A message has a subject, which listeners register to, and a content.


Remote Services
===============

Herald provides an RPC transport implementations for Pelix Remote Services.


Transports
==========

Currently, Herald supports two protocols in Python, and one in Java:

* HTTP (Python & Java):

  * Each message is sent as a POST request.
  * Peer discovery is based on a home-made multicast heart beat protocol
  * Best transport for LAN applications and for single-peer messages
  * Implementation is based on `requests <http://docs.python-requests.org/>`_.

* XMPP (Python only, for now):

  * Each message is a either a message or a group message
  * Discovery is based on a Multi-User Chat room (XEP-0045)
  * Best transport for distributed applications and for group messages
  * Implementation is based on `SleekXMPP <http://sleekxmpp.com/>`_


License
=======

Cohorte Herald is released under the terms of the Apache Software License 2.0.
