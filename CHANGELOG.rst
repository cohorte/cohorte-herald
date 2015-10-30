Changes form the 0.0.4 to 0.0.5
-------------------------------

** New Features
    * Choosing to which group the service will be exported [#19]
    * Added the Python EventAPI bridge project

** Enhancements
	* Better message handling in HeraldDiscovery (RPC) [commit/522855f05d15a7c01634771c930c3d488a023c2a]

** Bug Fix	
	* Solve the "TTL reached" issue [isandlaTech/cohorte-herald/pull/26]
	* Minor fix to the 3-phase handshake in Java [isandlaTech/cohorte-herald/pull/24]
	* When an error occurs during post, don't pop associated event [isandlaTech/cohorte-herald@6b08455]
	* Avoid handling reply messages on HeraldRPCExporter

Changes form the 0.0.3 to 0.0.4
-------------------------------

** New Features
    * Herald Remote Shell: open a shell session on another peer (experimental)

** Improvements
    * New Message format encapsulating headers and metadata
    * Herald unlocks send() calls when the target peer is unregistered.
    It also calls the errback of post() calls.

** Bug Fix
    * Fixing synchronisation problem: XMPP transport blocked on
    ``_on_disconnected`` (isandlaTech/cohorte-herald/issues/14).
