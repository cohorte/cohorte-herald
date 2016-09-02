#!/usr/bin/python
# -- Content-Encoding: UTF-8 --
"""
Herald Core service

:author: Thomas Calmant
:copyright: Copyright 2014, isandlaTech
:license: Apache License 2.0
:version: 1.0.0
:status: Alpha

..

    Copyright 2014 isandlaTech

    Licensed under the Apache License, Version 2.0 (the "License");
    you may not use this file except in compliance with the License.
    You may obtain a copy of the License at

        http://www.apache.org/licenses/LICENSE-2.0

    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS,
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    See the License for the specific language governing permissions and
    limitations under the License.
"""

# Module version
__version_info__ = (1, 0, 0)
__version__ = ".".join(str(x) for x in __version_info__)

# Documentation strings format
__docformat__ = "restructuredtext en"

# ------------------------------------------------------------------------------

# Herald
from herald.exceptions import InvalidPeerAccess, NoTransport, HeraldTimeout, \
    NoListener, ForgotMessage, PeerLost
from herald.utils import LoopTimer
import herald
import herald.beans as beans
import herald.probe

# Pelix
from pelix.ipopo.decorators import ComponentFactory, Requires, Provides, \
    Validate, Invalidate, Instantiate, RequiresMap, BindField, UpdateField, \
    UnbindField
import pelix.constants
import pelix.threadpool
import pelix.utilities

# Standard library
import fnmatch
import itertools
import logging
import re
import threading
import time

# ------------------------------------------------------------------------------

_logger = logging.getLogger(__name__)

# ------------------------------------------------------------------------------


@pelix.constants.BundleActivator
class _BundleActivator(object):
    """
    Bundle activator: registers a dummy probe service
    """
    def __init__(self):
        """
        Sets up members
        """
        self._registration = None

    def start(self, context):
        """
        Bundle started
        """
        # Register the dummy probe service
        self._registration = context.register_service(
            herald.SERVICE_PROBE, herald.probe.DummyProbe(),
            {pelix.constants.SERVICE_RANKING: -100})

    def stop(self, context):
        """
        Bundle stopped
        """
        self._registration.unregister()
        self._registration = None

# ------------------------------------------------------------------------------


class _WaitingSend(pelix.utilities.EventData):
    """
    A bean that describes a waiting send() call
    """
    def __init__(self, peer, msg_uid):
        """
        Sets up the bean
        """
        super(_WaitingSend, self).__init__()
        self.peer = peer
        self.msg_uid = msg_uid


class _WaitingPost(object):
    """
    A bean that describes parameters of a post() call
    """
    def __init__(self, callback, errback, timeout, forget_on_first, peer=None):
        """
        Sets up members

        :param callback: Method to call back when an answer is received
        :param errback: Method to call back on error
        :param timeout: Time to wait before forgetting this post, in seconds
                        (<= 0 or None for never)
        :param forget_on_first: If True, forget this post after the first
                                answer
        :param peer: Bean of the target peer, in single-target mode
        """
        self.peer = peer
        self.__callback = callback
        self.__errback = errback
        self.__forget_on_first = forget_on_first

        if timeout is not None and timeout > 0:
            self.__deadline = time.time() + timeout
        else:
            self.__deadline = None

    @property
    def forget_on_first(self):
        """
        Flag to determine if this post must be forgotten after its first reply
        """
        return self.__forget_on_first

    def is_dead(self):
        """
        Checks if the deadline has been reached

        :return: True if this message can be forgotten
        """
        if self.__deadline is not None:
            return self.__deadline > time.time()
        else:
            return False

    def callback(self, herald_svc, message):
        """
        Tries to call the callback of the post message.
        Avoids errors to go outside this method.

        :param herald_svc: Herald service instance
        :param message: Received answer message
        """
        if self.__callback is not None:
            try:
                # pylint: disable=W0703
                self.__callback(herald_svc, message)
            except Exception as ex:
                _logger.exception("Error calling callback: %s", ex)

    def errback(self, herald_svc, exception):
        """
        Tries to call the error callback of the post message.
        Avoids errors to go outside this method.

        :param herald_svc: Herald service instance
        :param exception: An exception describing/caused by the error
        """
        if self.__errback is not None:
            try:
                # pylint: disable=W0703
                self.__errback(herald_svc, exception)
            except Exception as ex:
                _logger.exception("Error calling errback: %s", ex)


@ComponentFactory("herald-core-factory")
@Provides((herald.SERVICE_HERALD_INTERNAL, herald.SERVICE_DIRECTORY_LISTENER))
@Provides(herald.SERVICE_HERALD, '_controller')
@Requires('_directory', herald.SERVICE_DIRECTORY)
@Requires('_listeners', herald.SERVICE_LISTENER, True, True)
@RequiresMap('_transports', herald.SERVICE_TRANSPORT, herald.PROP_ACCESS_ID,
             False, False, True)
@Instantiate("herald-core")
class Herald(object):
    """
    Herald core service
    """
    def __init__(self):
        """
        Sets up members
        """
        # Herald core directory
        self._directory = None

        # Service controller
        self._controller = False

        # Message listeners (dependency)
        self._listeners = []

        # Filter -> Listener (computed)
        self.__msg_listeners = {}

        # Herald transports: access ID -> implementation
        self._transports = {}

        # Notification threads
        self.__pool = pelix.threadpool.ThreadPool(5, logname="HeraldNotify")

        # Garbage collection timer
        self.__gc_timer = None

        # Last time a GC was done
        self._last_gc = None

        # List of received messages UIDs, kept 5 minutes: UID -> TTL
        self.__treated = {}

        # Events used for blocking "send()": UID -> EventData
        self.__waiting_events = {}

        # Events used for "post()" methods:
        # UID -> _WaitingPost
        self.__waiting_posts = {}

        # Thread safety
        self.__listeners_lock = threading.Lock()
        self.__gc_lock = threading.Lock()

    @Validate
    def _validate(self, context):
        """
        Component validated
        """
        # Start the thread pool
        self.__pool.start()

        # Start the garbage collector
        self._last_gc = None
        self.__gc_timer = LoopTimer(30, self.__garbage_collect,
                                    name="Herald-GC")
        self.__gc_timer.start()

    @Invalidate
    def _invalidate(self, _):
        """
        Component invalidated
        """
        # Stop the garbage collector
        self.__gc_timer.cancel()
        self.__gc_timer.join()
        self.__gc_timer = None

        # Stop the thread pool
        self.__pool.stop()

        # Clear waiting events (set them with no data)
        for event in tuple(self.__waiting_events.values()):
            event.set(None)

        exception = HeraldTimeout(None, "Herald stops to listen to messages",
                                  None)
        with self.__gc_lock:
            for waiting_post in self.__waiting_posts.values():
                waiting_post.errback(self, exception)

        # Clear storage
        self.__waiting_events.clear()
        self.__waiting_posts.clear()

        # Clear the thread pool
        self.__pool.clear()

    def __compile_pattern(self, pattern):
        """
        Converts a file name pattern to a regular expression

        :param pattern: A file name pattern
        :return: A compiled regular expression
        """
        return re.compile(fnmatch.translate(pattern), re.IGNORECASE)

    @BindField('_transports')
    def _bind_transport(self, _, listener, svc_ref):
        """
        A transport implementation has been bound
        """
        # Activate the service
        def set_svc():
            self._controller = True
        threading.Thread(target=set_svc, name="Herald-Bind").start()

    @UnbindField('_transports')
    def _unbind_transport(self, _, listener, svc_ref):
        """
        A transport implementation has gone away
        """
        if len(self._transports) == 1:
            # Last transport is going away
            def set_svc():
                self._controller = False
            threading.Thread(target=set_svc, name="Herald-Unbind").start()

    @BindField('_listeners')
    def _bind_listener(self, _, listener, svc_ref):
        """
        A message listener has been bound
        """
        svc_filters = pelix.utilities.to_iterable(
            svc_ref.get_property(herald.PROP_FILTERS), False)

        re_filters = set(self.__compile_pattern(fn_filter)
                         for fn_filter in svc_filters)

        with self.__listeners_lock:
            for re_filter in re_filters:
                self.__msg_listeners.setdefault(re_filter, set()) \
                    .add(listener)

    @UpdateField('_listeners')
    def _update_listener(self, _, listener, svc_ref, old_props):
        """
        The properties of a message listener have been updated
        """
        svc_filters = pelix.utilities.to_iterable(
            svc_ref.get_property(herald.PROP_FILTERS), False)

        new_filters = set(self.__compile_pattern(fn_filter)
                          for fn_filter in svc_filters)

        with self.__listeners_lock:
            # Get old and new filters as sets
            old_svc_filters = pelix.utilities.to_iterable(
                old_props.get(herald.PROP_FILTERS), False)

            old_filters = set(self.__compile_pattern(fn_filter)
                              for fn_filter in old_svc_filters)

            # Compute differences
            added_filters = new_filters.difference(old_filters)
            removed_filters = old_filters.difference(new_filters)

            # Add new filters
            for re_filter in added_filters:
                self.__msg_listeners.setdefault(re_filter, set()) \
                    .add(listener)

            # Remove old ones
            for re_filter in removed_filters:
                try:
                    listeners = self.__msg_listeners[re_filter]
                    listeners.remove(listener)
                except KeyError:
                    # Filter or listener not found
                    pass
                else:
                    # Clean up dictionary if necessary
                    if not listeners:
                        del self.__msg_listeners[re_filter]

    @UnbindField('_listeners')
    def _unbind_listener(self, _, listener, svc_ref):
        """
        A message listener has gone away
        """
        svc_filters = pelix.utilities.to_iterable(
            svc_ref.get_property(herald.PROP_FILTERS), False)

        with self.__listeners_lock:
            re_filters = set(self.__compile_pattern(fn_filter)
                             for fn_filter in svc_filters)
            for re_filter in re_filters:
                try:
                    listeners = self.__msg_listeners[re_filter]
                    listeners.remove(listener)
                except KeyError:
                    # Filter or listener not found
                    pass
                else:
                    # Clean up dictionary if necessary
                    if not listeners:
                        del self.__msg_listeners[re_filter]

    def __garbage_collect(self):
        """
        Garbage collects dead waiting post beans. Calls on a regular basis
        by a LoopTimer
        """
        with self.__gc_lock:
            # Compute last garbage collect time
            if self._last_gc is None:
                gc_delta = 0
            else:
                gc_delta = int(time.time()) - self._last_gc

            # Delete timed out post message beans
            to_delete = [uid
                         for uid, waiting_post in self.__waiting_posts.items()
                         if waiting_post.is_dead()]
            for uid in to_delete:
                del self.__waiting_posts[uid]

            # Delete UID of treated message of more than 5 minutes
            to_delete = []
            for uid, ttl in self.__treated.items():
                new_ttl = ttl + gc_delta
                self.__treated[uid] = new_ttl
                if new_ttl > 300:
                    to_delete.append(uid)

            for uid in to_delete:
                del self.__treated[uid]

            # Update the "last garbage collect time"
            self._last_gc = int(time.time())

    def handle_message(self, message):
        """
        Handles a message received from a transport implementation.

        Unlocks/calls back the senders of the message this one responds to.

        :param message: A MessageReceived bean forged by the transport
        """
        with self.__gc_lock:
            if message.uid in self.__treated:
                # Message already handled, maybe it has been received by
                # another transport
                return
            else:
                # Store the message UID in the treated messages
                self.__treated[message.uid] = 0

        # User a tuple, because list can't be compared to tuples
        parts = tuple(part for part in message.subject.split('/') if part)
        try:
            if parts[0] == 'herald':
                # Internal message
                if parts[1] == 'error':
                    # Error message: handle it, but don't propagate it
                    self._handle_error(message, parts[2])
                    return

                elif parts[1] == 'directory':
                    # Directory update message
                    self._handle_directory_message(message, parts[2])
        except IndexError:
            # Not enough arguments for a directory update: ignore
            pass

        # Notify others of the message
        self.__notify(message)

    def _handle_error(self, message, kind):
        """
        Handles an error message

        :param message: MessageReceived bean, received from another peer
        :param kind: Kind of error
        """
        if kind == 'no-listener':
            # No listener found for a given message
            # ... release send() calls
            try:
                # Get the original message UID and Subject
                uid = message.content['uid']
                exception = NoListener(beans.Target(message.sender), uid,
                                       message.content['subject'])
            except KeyError:
                # Invalid error content...
                return

            try:
                # Unlock the poster with an exception
                self.__waiting_events.pop(uid).raise_exception(exception)
            except KeyError:
                # Nobody was waiting for the event
                pass

            # ... notify post() callers
            try:
                self.__waiting_posts[uid].errback(self, exception)
            except KeyError:
                # No error callback for this message
                pass

    def _handle_directory_message(self, message, kind):
        """
        Handles a directory update message

        :param message: Message received from another peer
        :param kind: Kind of directory message
        """
        if kind == 'bye':
            # A peer is going away
            self._directory.unregister(message.content)
        elif kind == 'dump':
            # request directory dump            
            directory_dump = self._directory.dump()
            if directory_dump is not None:
                self.reply(message, directory_dump)

    def peer_unregistered(self, peer):
        """
        Peer unregistered: raise an exception in all pending send/post calls
        """
        # Prepare the exception to raise
        exception = PeerLost(peer, "Peer {0} has been lost".format(peer))

        # ... unlock send() calls
        uids = [uid for uid, event in self.__waiting_events.items()
                if peer == event.peer]
        for uid in uids:
            self.__waiting_events.pop(uid).raise_exception(exception)

        with self.__gc_lock:
            # ... list post() callers for this peer
            entries = {uid: waiting_post
                       for uid, waiting_post in self.__waiting_posts.items()
                       if peer == waiting_post.peer}

            # Clean up callers dictionary
            for uid in entries:
                del self.__waiting_posts[uid]

        # ... notify post() callers
        for waiting_post in entries.values():
            waiting_post.errback(self, exception)

    @staticmethod
    def peer_registered(peer):
        """
        Peer registered: ignore
        """
        pass

    @staticmethod
    def peer_updated(peer, access_id, data, previous):
        """
        Peer updated: ignore
        """
        pass

    def __notify(self, message):
        """
        Calls back message senders about responses or notifies the reception of
        a message

        :param message: The received message
        """
        if message.reply_to:
            # ... unlock send() calls
            try:
                # This is an answer to a message: unlock the sender
                self.__waiting_events.pop(message.reply_to).set(message)
            except KeyError:
                # Nobody was waiting for the event
                pass

            # ... notify post() callers
            try:
                with self.__gc_lock:
                    waiting_post = self.__waiting_posts[message.reply_to]
            except KeyError:
                # Nobody was waiting for an answer
                pass
            else:
                waiting_post.callback(self, message)
                if waiting_post.forget_on_first:
                    # First answer received: forget about the message
                    del self.__waiting_posts[message.reply_to]

        # Compute the list of listeners to notify
        msg_listeners = set()
        subject = message.subject

        with self.__listeners_lock:
            for re_filter, re_listeners in self.__msg_listeners.items():
                if re_filter.match(subject) is not None:
                    msg_listeners.update(re_listeners)

        if msg_listeners:
            # Call listeners in the thread pool
            for listener in msg_listeners:
                try:
                    self.__pool.enqueue(listener.herald_message,
                                        self, message)
                except (AttributeError, ValueError):
                    # Invalid listener
                    pass
        else:
            try:
                # No listener found: send an error message
                self.reply(message,
                           {'uid': message.uid, 'subject': message.subject},
                           'herald/error/no-listener')
            except Exception as ex:
                _logger.error("Can't send an error back to the sender: %s", ex)

    def _fire_reply(self, message, reply_to):
        """
        Tries to fire a reply to the given message

        :param message: Message to send as a reply
        :param reply_to: Message the first argument replies to
        :return: The UID of the sent message
        """
        # Use the message source peer
        try:
            transport = self._transports[reply_to.access]
        except KeyError:
            # Reception transport is not available anymore...
            raise NoTransport(beans.Target(uid=reply_to.sender),
                              "No reply transport for access {0}"
                              .format(reply_to.access))
        else:
            # Try to get the Peer bean. If unknown, consider that the
            # "extra" data will help the transport to reply
            try:
                peer = self._directory.get_peer(reply_to.sender)
            except KeyError:
                peer = None

            try:
                # Send the reply
                transport.fire(peer, message, reply_to.extra)
            except InvalidPeerAccess:
                raise NoTransport(beans.Target(uid=reply_to.sender),
                                  "Can't reply to {0} using {1} transport"
                                  .format(peer, reply_to.access))
            else:
                # Reply sent. Stop here
                return message.uid

    def fire(self, target, message):
        """
        Fires (and forget) the given message to the target

        :param target: The UID of a Peer, or a Peer object
        :param message: A Message bean
        :return: The UID of the message sent
        :raise KeyError: Unknown peer UID
        :raise NoTransport: No transport found to send the message
        """
        # Standard behavior
        # Get the Peer object
        if not isinstance(target, beans.Peer):
            peer = self._directory.get_peer(target)
        else:
            peer = target

        # Check if some transports are bound
        if not self._transports:
            raise NoTransport(beans.Target(uid=peer.uid),
                              "No transport bound yet.")

        # Get accesses
        accesses = peer.get_accesses()
        for access in accesses:
            try:
                transport = self._transports[access]
            except KeyError:
                # No transport for this kind of access
                pass
            else:
                try:
                    # Call it
                    transport.fire(peer, message)
                except InvalidPeerAccess as ex:
                    # Transport can't read peer access data
                    _logger.debug("Error reading access for transport %s: %s",
                                  access, ex)
                except Exception as ex:
                    # Exception during transport
                    _logger.info("Error using transport %s: %s", access, ex)
                else:
                    # Success
                    break
        else:
            # No transport for those accesses
            raise NoTransport(beans.Target(uid=peer.uid),
                              "No working transport found for peer {0}"
                              .format(peer))

        return message.uid

    def fire_group(self, group, message):
        """
        Fires (and forget) the given message to the given group of peers

        :param group: The name of a group of peers
        :param message: A Message bean
        :return: A tuple: the UID of the message sent and the list of peers
        :raise KeyError: Unknown group
        :raise NoTransport: No transport found to send the message
        """
        # Get all peers known in the group
        all_peers = self._directory.get_peers_for_group(group)
        if not all_peers:
            _logger.info("No peer in group %s", group)
            return message.uid, set()

        # Check if some transports are bound
        if not self._transports:
            raise NoTransport(
                beans.Target(group=group,
                             uids=[peer.uid for peer in all_peers]),
                "No transport bound yet.")

        # Find the common accesses
        accesses = {}
        for peer in all_peers:
            for access in peer.get_accesses():
                accesses.setdefault(access, set()).add(peer)

        missing = []
        for access, access_peers in accesses.items():
            if not access_peers:
                # Nothing to do
                continue

            try:
                transport = self._transports[access]
            except KeyError:
                # No transport for this kind of access
                _logger.debug("No transport for %s", access)
            else:
                try:
                    # Call it
                    reached_peers = transport.fire_group(group, access_peers,
                                                         message)
                    if reached_peers is None:
                        reached_peers = access_peers
                except InvalidPeerAccess as ex:
                    # Transport can't find group access data
                    _logger.debug("Missing access info: %s", ex)
                else:
                    # Success: clean up waiting peers
                    all_done = True
                    for remaining_peers in accesses.values():
                        remaining_peers.difference_update(reached_peers)
                        if remaining_peers:
                            # Still some peers to notify
                            all_done = False

                    if all_done:
                        break
        else:
            missing = set(itertools.chain(*accesses.values()))
            if missing:
                _logger.warning("Some peers haven't been notified: %s",
                                ', '.join(str(peer) for peer in missing))
            else:
                _logger.debug("No peer to send the message to.")

        return message.uid, missing

    def send(self, target, message, timeout=None):
        """
        Sends a message, and waits for its reply

        :param target: The UID of a Peer, or a Peer object
        :param message: A Message bean
        :param timeout: Maximum time to wait for an answer
        :return: The reply message bean
        :raise KeyError: Unknown peer UID
        :raise NoTransport: No transport found to send the message
        :raise NoListener: Message received, but nobody was registered to
                           listen to it
        :raise HeraldTimeout: Timeout raised before getting an answer
        """
        # Get the Peer object
        if not isinstance(target, beans.Peer):
            peer = self._directory.get_peer(target)
        else:
            peer = target

        # Prepare an event, which will be set when the answer will be received
        event = _WaitingSend(peer, message.uid)
        self.__waiting_events[message.uid] = event

        try:
            # Fire the message
            self.fire(peer, message)

            # Message sent, wait for an answer
            if event.wait(timeout):
                if event.data is not None:
                    return event.data
                else:
                    # Message cancelled due to invalidation
                    raise HeraldTimeout(beans.Target(uid=peer.uid),
                                        "Herald stops listening to messages",
                                        message)
            else:
                raise HeraldTimeout(beans.Target(uid=peer.uid),
                                    "Timeout reached before receiving a reply",
                                    message)
        finally:
            try:
                # Clean up
                del self.__waiting_events[message.uid]
            except KeyError:
                # Ignore errors at this point
                pass

    def post(self, target, message, callback, errback,
             timeout=180, forget_on_first=True):
        """
        Posts a message. The given methods will be called back as soon as a
        result is given, or in case of error

        The given callback methods must have the following signatures:
          - callback(herald, reply_message)
          - errback(herald, exception)

        :param target: The UID of a Peer, or a Peer object
        :param message: A Message bean
        :param callback: Method to call back when a reply is received
        :param errback: Method to call back if an error occurs
        :param timeout: Time after which the message will be forgotten
        :param forget_on_first: Forget the message after the first answer
        :return: The message UID
        :raise KeyError: Unknown peer UID
        :raise NoTransport: No transport found to send the message
        """
        # Get the Peer object
        if not isinstance(target, beans.Peer):
            peer = self._directory.get_peer(target)
        else:
            peer = target

        with self.__gc_lock:
            # Prepare an entry in the waiting posts
            self.__waiting_posts[message.uid] = \
                _WaitingPost(callback, errback, timeout, forget_on_first, peer)

        try:
            # Fire the message
            # pylint: disable=W0702
            return self.fire(peer, message)
        except:
            # Early clean up in case of exception
            try:
                with self.__gc_lock:
                    del self.__waiting_posts[message.uid]
            except KeyError:
                pass

            # Propagate the error
            raise

    def post_group(self, group, message, callback, errback,
                   timeout=180):
        """
        Posts a message to a group of peers. The given methods will be called
        back as soon as a result is given, or in case of error.

        If no timeout is given, the message UID must be forgotten manually.

        :param group: The name of a group of peers
        :param message: A Message bean
        :param callback: Method to call back when a reply is received
        :param errback: Method to call back if an error occurs
        :param timeout: Time after which the message will be forgotten
        :return: The message UID
        :raise KeyError: Unknown group
        :raise NoTransport: No transport found to send the message
        """
        # Get all peers known in the group
        all_peers = self._directory.get_peers_for_group(group)

        # Check if some transports are bound
        if not self._transports:
            raise NoTransport(
                beans.Target(group=group,
                             uids=[peer.uid for peer in all_peers]),
                "No transport bound yet.")

        with self.__gc_lock:
            # Prepare an entry in the waiting posts
            self.__waiting_posts[message.uid] = \
                _WaitingPost(callback, errback, timeout, False)

        # Find the common accesses
        accesses = {}
        for peer in all_peers:
            for access in peer.get_accesses():
                accesses.setdefault(access, set()).add(peer)

        for access, access_peers in accesses.items():
            if not access_peers:
                # Nothing to do
                continue

            try:
                transport = self._transports[access]
            except KeyError:
                # No transport for this kind of access
                pass
            else:
                try:
                    # Call it
                    transport.fire_group(group, access_peers, message)
                except InvalidPeerAccess:
                    # Transport can't find group access data
                    pass
                else:
                    # Success: clean up waiting peers
                    all_done = True
                    for remaining_peers in accesses.values():
                        remaining_peers.difference_update(access_peers)
                        if remaining_peers:
                            # Still some peers to notify
                            all_done = False

                    if all_done:
                        break

        return message.uid

    def forget(self, uid):
        """
        Tells Herald to forget information about the given message UIDs.

        This can be used to clean up references to a component being
        invalidated.

        :param uid: The UID of a message
        :return: True if there was a reference about this message
        """
        # Prepare the exception
        result = False
        exception = ForgotMessage(uid)

        # ... release the send() call
        try:
            self.__waiting_events.pop(uid).raise_exception(exception)
            result = True
        except KeyError:
            # ... no pending call
            pass

        with self.__gc_lock:
            try:
                self.__waiting_posts.pop(uid).errback(self, exception)
                result = True
            except KeyError:
                # ... no pending call
                pass

        return result

    def reply(self, message, content, subject=None):
        """
        Replies to a message

        :param message: Original message
        :param content: Content of the response
        :param subject: Reply message subject (same as request if None)
        :raise NoTransport: No transport/access found to send the reply
        """
        # Normalize subject. By default, add a 'reply' prefix,
        # to avoid potential loops
        if subject is None:
            subject = '/'.join(('reply', message.subject))

        try:
            # Try to reuse the same transport
            self._fire_reply(beans.Message(subject, content), message)
        except NoTransport:
            # Continue...
            pass
        else:
            # No error
            return

        # If not possible: fire a standard reply
        try:
            # Fire the reply
            self.fire(message.sender, beans.Message(subject, content))
        except KeyError:
            # Convert KeyError to NoTransport
            raise NoTransport(beans.Target(uid=message.sender),
                              "No access to reply to {0}"
                              .format(message.sender))
