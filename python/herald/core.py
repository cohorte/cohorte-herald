#!/usr/bin/python
# -- Content-Encoding: UTF-8 --
"""
Herald Core service
"""

# Herald
from herald.exceptions import InvalidPeerAccess, NoTransport, HeraldTimeout, \
    NoListener, ForgotMessage
import herald
import herald.beans as beans

# Pelix
from pelix.ipopo.decorators import ComponentFactory, Requires, Provides, \
    Validate, Invalidate, Instantiate, RequiresMap, BindField, UpdateField, \
    UnbindField
import pelix.threadpool
import pelix.utilities

# Standard library
import fnmatch
import logging
import re
import threading

# ------------------------------------------------------------------------------

_logger = logging.getLogger(__name__)

# ------------------------------------------------------------------------------


@ComponentFactory("herald-core-factory")
@Provides(herald.SERVICE_HERALD)
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

        # Message listeners (dependency)
        self._listeners = []

        # Filter -> Listener (computed)
        self.__msg_listeners = {}

        # Thread safety for listeners
        self.__lock = threading.Lock()

        # Herald transports: access ID -> implementation
        self._transports = {}

        # Notification threads
        self.__pool = pelix.threadpool.ThreadPool(5, logname="HeraldNotify")

        # Events used for blocking "send()": UID -> EventData
        self.__waiting_events = {}

        # Events used for "post()" methods: UID -> (callback, errback)
        self.__waiting_posts = {}

    @Validate
    def _validate(self, context):
        """
        Component validated
        """
        # Start the thread pool
        self.__pool.start()

    @Invalidate
    def _invalidate(self, context):
        """
        Component invalidated
        """
        # Stop the thread pool
        self.__pool.stop()

        # Clear waiting events (set them with no data)
        for event in tuple(self.__waiting_events.values()):
            event.set(None)
        self.__waiting_events.clear()

        # Clear the thread pool
        self.__pool.clear()

    def __compile_pattern(self, pattern):
        """
        Converts a file name pattern to a regular expression

        :param pattern: A file name pattern
        :return: A compiled regular expression
        """
        return re.compile(fnmatch.translate(pattern), re.IGNORECASE)

    @BindField('_listeners')
    def _bind_listener(self, _, listener, svc_ref):
        """
        A message listener has been bound
        """
        with self.__lock:
            re_filters = set(self.__compile_pattern(fn_filter)
                             for fn_filter
                             in svc_ref.get_property(herald.PROP_FILTERS)
                             or [])
            for re_filter in re_filters:
                self.__msg_listeners.setdefault(re_filter, set()) \
                    .add(listener)

    @UpdateField('_listeners')
    def _update_listener(self, _, listener, svc_ref, old_props):
        """
        The properties of a message listener have been updated
        """
        with self.__lock:
            # Get old and new filters as sets
            old_filters = set(self.__compile_pattern(fn_filter)
                              for fn_filter
                              in old_props.get(herald.PROP_FILTERS) or [])
            new_filters = set(self.__compile_pattern(fn_filter)
                              for fn_filter
                              in svc_ref.get_property(herald.PROP_FILTERS)
                              or [])

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
        with self.__lock:
            re_filters = set(self.__compile_pattern(fn_filter)
                             for fn_filter
                             in svc_ref.get_property(herald.PROP_FILTERS)
                             or [])
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

    def handle_message(self, message):
        """
        Handles a message received from a transport implementation.

        Unlocks/calls back the senders of the message this one responds to.

        :param message: A MessageReceived bean forged by the transport
        """
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

        :param message: Message received from another peer
        :param kind: Kind of error
        """
        if kind == 'no-listener':
            # No listener found for a given message
            # ... release send() calls
            try:
                # Get the request message UID
                uid = message.content['uid']
                subject = message.content['subject']
            except KeyError:
                # Invalid error content...
                return

            try:
                # Unlock the sender with an exception
                self.__waiting_events.pop(uid) \
                    .raise_exception(NoListener(uid, subject))
            except KeyError:
                # Nobody was waiting for the event
                pass

            # ... notify post() callers
            try:
                errback = self.__waiting_posts.pop(uid)[1]
            except (KeyError, IndexError):
                # No error callback for this message
                pass
            else:
                if errback is not None:
                    try:
                        errback(self, NoListener(uid, subject))
                    except Exception as ex:
                        _logger.exception("Error calling errback: %s", ex)

    def _handle_directory_message(self, message, kind):
        """
        Handles a directory update message

        :param message: Message received from another peer
        :param kind: Kind of directory message
        """
        if kind == 'newcomer':
            # A new peer appears: register it
            self._directory.register(message.content)

            # Reply to it
            self.reply(message, self._directory.get_local_peer().dump(),
                       'herald/directory/welcome')

        elif kind == 'welcome':
            # A peer replied to our 'newcomer' event
            self._directory.register(message.content)

        elif kind == 'bye':
            # A peer is going away
            self._directory.unregister(message.content)

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
                callback = self.__waiting_posts[message.reply_to][0]
            except KeyError:
                # Nobody was waiting for an answer
                pass
            else:
                try:
                    callback(self, message)
                except Exception as ex:
                    _logger.exception("Error calling back poster: %s", ex)

        # Compute the list of listeners to notify
        msg_listeners = set()
        subject = message.subject

        with self.__lock:
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
            # No listener found: send an error message
            self.reply(message,
                       {'uid': message.uid, 'subject': message.subject},
                       'herald/error/no-listener')

    def _fire_reply(self, message, reply_to):
        """
        Tries to fire a reply to the given message

        :param message: Message to send as a reply
        :param reply_to: Message the first argument replies to
        :return: The UID of the sent message, None
        """
        # Use the message source peer
        try:
            transport = self._transports[reply_to.access]
        except KeyError:
            # Reception transport is not available anymore...
            raise NoTransport("No reply transport for access {0}"
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
                raise NoTransport("Can't reply to {0} using {1} transport"
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
            raise NoTransport("No transport bound yet.")

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
                    _logger.debug("Error using transport %s: %s", access, ex)
                else:
                    # Success
                    break
        else:
            # No transport for those accesses
            raise NoTransport("No transport found for peer {0}".format(peer))

        return message.uid

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
        # Prepare an event, which will be set when the answer will be received
        event = pelix.utilities.EventData()
        self.__waiting_events[message.uid] = event

        try:
            # Fire the message
            self.fire(target, message)

            # Message sent, wait for an answer
            if event.wait(timeout):
                if event.data is not None:
                    return event.data
                else:
                    # Message cancelled due to invalidation
                    raise HeraldTimeout("Herald stops listening to messages",
                                        message)
            else:
                raise HeraldTimeout("Timeout reached before receiving a reply",
                                    message)
        finally:
            try:
                # Clean up
                del self.__waiting_events[message.uid]
            except KeyError:
                # Ignore errors at this point
                pass

    def post(self, target, message, callback, errback):
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
        :return: The message UID
        :raise KeyError: Unknown peer UID
        :raise NoTransport: No transport found to send the message
        """
        # Prepare an entry in the waiting posts
        self.__waiting_posts[message.uid] = (callback, errback)

        try:
            # Fire the message
            return self.fire(target, message)
        except:
            # Early clean up in case of exception
            try:
                del self.__waiting_posts[message.uid]
            except KeyError:
                pass

    def forget(self, uid):
        """
        Tells Herald to forget informations about the given message UIDs.

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

        try:
            errback = self.__waiting_posts.pop(uid)[1]
        except KeyError:
            # ... no pending call
            pass
        else:
            result = True
            try:
                errback(self, exception)
            except:
                # Silent exception
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
        # Normalize subject
        if not subject:
            subject = message.subject

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
            raise NoTransport("No access to reply to {0}"
                              .format(message.sender))
