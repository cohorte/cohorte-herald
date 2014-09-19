/**
 * Copyright 2014 isandlaTech
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

package org.cohorte.herald.core;

import java.util.Arrays;
import java.util.Collection;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.LinkedList;
import java.util.List;
import java.util.Map;
import java.util.Map.Entry;
import java.util.Set;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

import org.apache.felix.ipojo.annotations.Bind;
import org.apache.felix.ipojo.annotations.Component;
import org.apache.felix.ipojo.annotations.Instantiate;
import org.apache.felix.ipojo.annotations.Invalidate;
import org.apache.felix.ipojo.annotations.Modified;
import org.apache.felix.ipojo.annotations.Provides;
import org.apache.felix.ipojo.annotations.Requires;
import org.apache.felix.ipojo.annotations.ServiceController;
import org.apache.felix.ipojo.annotations.Unbind;
import org.apache.felix.ipojo.annotations.Validate;
import org.cohorte.herald.IConstants;
import org.cohorte.herald.IDirectory;
import org.cohorte.herald.IHerald;
import org.cohorte.herald.IHeraldInternal;
import org.cohorte.herald.IMessageListener;
import org.cohorte.herald.IPostCallback;
import org.cohorte.herald.IPostErrback;
import org.cohorte.herald.ITransport;
import org.cohorte.herald.Message;
import org.cohorte.herald.MessageReceived;
import org.cohorte.herald.Peer;
import org.cohorte.herald.Target;
import org.cohorte.herald.exceptions.ForgotMessage;
import org.cohorte.herald.exceptions.HeraldException;
import org.cohorte.herald.exceptions.HeraldTimeout;
import org.cohorte.herald.exceptions.NoListener;
import org.cohorte.herald.exceptions.NoTransport;
import org.cohorte.herald.exceptions.UnknownPeer;
import org.cohorte.herald.exceptions.ValueError;
import org.cohorte.herald.utils.EventData;
import org.cohorte.herald.utils.EventException;
import org.cohorte.herald.utils.FnMatch;
import org.cohorte.herald.utils.LoopTimer;
import org.osgi.framework.ServiceReference;
import org.osgi.service.log.LogService;

/**
 * Implementation of the core service of Herald
 *
 * @author Thomas Calmant
 */
@Component(publicFactory = false)
@Provides(specifications = { IHerald.class, IHeraldInternal.class })
@Instantiate(name = "herald-core")
public class Herald implements IHerald, IHeraldInternal {

    /** iPOJO requirement ID */
    private static final String ID_LISTENERS = "listeners";

    /** iPOJO requirement ID */
    private static final String ID_TRANSPORTS = "transports";

    /** Core service controller */
    @ServiceController(value = false, specification = IHerald.class)
    private boolean pController;

    /** The Herald core directory */
    @Requires
    private IDirectory pDirectory;

    /** The garbage collection timer */
    private LoopTimer pGarbageTimer;

    /** Object used to synchronize garbage collection */
    private final Object pGarbageToken = new Object();

    /** Internal service controller */
    @ServiceController(value = true)
    private boolean pInternalController;

    /** Time stamp of the last garbage collection */
    private long pLastGarbage = -1;

    /** Filter -&gt; Listeners */
    private final Map<FnMatch, Set<IMessageListener>> pListeners = new LinkedHashMap<>();

    /** Listener -&gt; Filters */
    private final Map<IMessageListener, Set<FnMatch>> pListenersFilters = new LinkedHashMap<IMessageListener, Set<FnMatch>>();

    /** The logger */
    @Requires(optional = true)
    private LogService pLogger;

    /** The thread pool */
    private ExecutorService pPool;

    /** Access ID -&gt; Transport implementation */
    private final Map<String, ITransport> pTransports = new LinkedHashMap<>();

    /** List of received messages UIDs, kept 5 minutes: UID -&gt; TTL */
    private final Map<String, Long> pTreatedMessages = new LinkedHashMap<>();

    /** Events used to block "send()" methods: UID -&gt; EventData */
    private final Map<String, EventData<Object>> pWaitingEvents = new LinkedHashMap<>();

    /** Events used for "post()" methods: UID -&gt; WaitingPost */
    private final Map<String, WaitingPost> pWaitingPosts = new LinkedHashMap<>();

    /**
     * A message listener has been bound
     *
     * @param aListener
     *            A message listener
     * @param aReference
     *            The injected service reference
     */
    @Bind(id = ID_LISTENERS, aggregate = true, optional = true)
    protected void bindListener(final IMessageListener aListener,
            final ServiceReference<IMessageListener> aReference) {

        final Object rawFilters = aReference
                .getProperty(IConstants.PROP_FILTERS);
        String[] filters;
        if (rawFilters instanceof String) {
            // Single filter
            filters = new String[] { (String) rawFilters };

        } else if (rawFilters instanceof String[]) {
            // Copy the array
            final String[] givenFilters = (String[]) rawFilters;
            filters = Arrays.copyOf(givenFilters, givenFilters.length);

        } else {
            // Unreadable filters
            return;
        }

        synchronized (pListeners) {
            for (final String filter : filters) {
                // Compile the filter
                final FnMatch match = new FnMatch(filter);

                // Associate the listener to the filter
                Utilities.setDefault(pListeners, match,
                        new LinkedHashSet<IMessageListener>()).add(aListener);
                Utilities.setDefault(pListenersFilters, aListener,
                        new LinkedHashSet<FnMatch>()).add(match);
            }
        }
    }

    /**
     * A transport implementation has been bound
     *
     * @param aTransport
     *            A transport implementation
     * @param aReference
     *            The injected service reference
     */
    @Bind(id = ID_TRANSPORTS, aggregate = true, optional = true)
    protected void bindTransport(final ITransport aTransport,
            final ServiceReference<ITransport> aReference) {

        final String accessId = (String) aReference
                .getProperty(IConstants.PROP_ACCESS_ID);
        if (accessId == null || accessId.isEmpty()) {
            // Ignore invalid access IDs
            return;
        }

        synchronized (pTransports) {
            // Store the service
            pTransports.put(accessId, aTransport);

            // We have at least one service: provide our service
            pController = true;
        }
    }

    /*
     * (non-Javadoc)
     *
     * @see org.cohorte.herald.IHerald#fire(org.cohorte.herald.Peer,
     * org.cohorte.herald.Message)
     */
    @Override
    public String fire(final Peer aPeer, final Message aMessage)
            throws NoTransport {

        // Check if we can send the message
        if (pTransports.isEmpty()) {
            throw new NoTransport(new Target(aPeer), "No transport bound yet.");
        }

        // Try each access
        boolean success = false;
        for (final String access : aPeer.getAccesses()) {
            final ITransport transport = pTransports.get(access);
            if (transport == null) {
                // No transport for this kind of access
                continue;
            }

            try {
                // Try to use it
                transport.fire(aPeer, aMessage);

                // Success: stop here
                success = true;
                break;

            } catch (final HeraldException ex) {
                // Exception during transport
                pLogger.log(LogService.LOG_WARNING, "Error using transport "
                        + access + ": " + ex);
            }
        }

        if (!success) {
            // No transport succeeded
            throw new NoTransport(new Target(aPeer),
                    "No working transport found for peer " + aPeer);
        }

        return aMessage.getUid();
    }

    /*
     * (non-Javadoc)
     *
     * @see org.cohorte.herald.IHerald#fire(java.lang.String,
     * org.cohorte.herald.Message)
     */
    @Override
    public String fire(final String aPeerUid, final Message aMessage)
            throws NoTransport, UnknownPeer {

        return fire(pDirectory.getPeer(aPeerUid), aMessage);
    }

    /*
     * (non-Javadoc)
     *
     * @see org.cohorte.herald.IHerald#fireGroup(java.lang.String,
     * org.cohorte.herald.Message)
     */
    @Override
    public Collection<Peer> fireGroup(final String aGroupName,
            final Message aMessage) throws NoTransport {

        // Get all peers known in the group
        final Collection<Peer> allPeers = pDirectory
                .getPeersForGroup(aGroupName);

        if (pTransports.isEmpty()) {
            // Make the list of UIDs
            throw new NoTransport(new Target(aGroupName,
                    Target.toUids(allPeers)), "No transport bound yet.");
        }

        // Group peers by accesses
        final Map<String, Set<Peer>> accesses = new LinkedHashMap<>();
        for (final Peer peer : allPeers) {
            for (final String access : peer.getAccesses()) {
                Utilities.setDefault(accesses, access,
                        new LinkedHashSet<Peer>());
            }
        }

        boolean allDone = false;
        for (final Entry<String, Set<Peer>> entry : accesses.entrySet()) {
            final String access = entry.getKey();
            final Set<Peer> accessPeers = entry.getValue();

            if (accessPeers.isEmpty()) {
                // Nothing to do
                continue;
            }

            // Find the transport for this access
            final ITransport transport = pTransports.get(access);
            if (transport == null) {
                // No transport for this kind of access
                pLogger.log(LogService.LOG_DEBUG, "No transport for " + access);
                continue;
            }

            final Collection<Peer> reachedPeers;
            try {
                // Try to send the message
                reachedPeers = transport.fireGroup(aGroupName, accessPeers,
                        aMessage);

            } catch (final HeraldException ex) {
                // Try again...
                pLogger.log(LogService.LOG_DEBUG,
                        "Error group-firing message: " + ex, ex);
                continue;
            }

            allDone = true;
            for (final Set<Peer> remainingPeers : accesses.values()) {
                remainingPeers.removeAll(reachedPeers);
                if (!remainingPeers.isEmpty()) {
                    allDone = false;
                }
            }

            if (allDone) {
                break;
            }
        }

        final Set<Peer> missingPeers = new LinkedHashSet<>();
        if (!allDone) {
            // Some peers are missing
            for (final Set<Peer> remainingPeers : accesses.values()) {
                missingPeers.addAll(remainingPeers);
            }

            if (!missingPeers.isEmpty()) {
                pLogger.log(LogService.LOG_WARNING,
                        "Some peers haven't been notified: " + missingPeers);
            } else {
                pLogger.log(LogService.LOG_DEBUG,
                        "No peer to send the message to.");
            }
        }

        return missingPeers;
    }

    /**
     * Tries to fire a reply to the given message
     *
     * @param aReplyMessage
     *            Message to send as a reply
     * @param aOriginalMessage
     *            Message the first argument replies to
     * @return The UID of the sent message
     * @throws HeraldException
     *             Error trying to send the reply, or to read information about
     *             the peer
     */
    private String fireReply(final Message aReplyMessage,
            final MessageReceived aOriginalMessage) throws HeraldException {

        final String access = aOriginalMessage.getAccess();
        final String sender = aOriginalMessage.getSender();

        // Look for the transport implementation
        final ITransport transport = pTransports.get(access);
        if (transport == null) {
            throw new NoTransport(new Target(sender),
                    "No reply transport for access " + access);
        }

        // Try to get a Peer bean
        Peer peer;
        try {
            peer = pDirectory.getPeer(aOriginalMessage.getSender());

        } catch (final UnknownPeer ex) {
            // Hope the transport has enough extra information
            peer = null;
        }

        // Send the reply
        transport.fire(peer, aReplyMessage, aOriginalMessage.getExtra());
        return aReplyMessage.getUid();
    }

    /*
     * (non-Javadoc)
     *
     * @see org.cohorte.herald.IHerald#forget(java.lang.String)
     */
    @Override
    public boolean forget(final String aMessageUid) {

        boolean result = false;
        final ForgotMessage exception = new ForgotMessage(aMessageUid);

        // Release the send() call
        final EventData<?> event = pWaitingEvents.remove(aMessageUid);
        if (event != null) {
            event.raiseException(exception);
            result = true;
        }

        synchronized (pGarbageToken) {
            // Notify post() callers
            final WaitingPost waitingPost = pWaitingPosts.remove(aMessageUid);
            if (waitingPost != null) {
                waitingPost.errback(this, exception);
                result = true;
            }
        }

        return result;
    }

    /**
     * Garbage collects dead waiting post beans. Calls on a regular basis by a
     * LoopTimer
     */
    private void garbageCollect() {

        synchronized (pGarbageToken) {
            // Compute time since the last garbage collection
            long delta;
            if (pLastGarbage < 0) {
                delta = 0;
            } else {
                delta = System.currentTimeMillis() - pLastGarbage;
            }

            // Delete timed out post message beans
            final Set<String> toDelete = new LinkedHashSet<>();
            for (final Entry<String, WaitingPost> entry : pWaitingPosts
                    .entrySet()) {
                if (entry.getValue().isDead()) {
                    toDelete.add(entry.getKey());
                }
            }
            for (final String uid : toDelete) {
                pWaitingPosts.remove(uid);
            }

            // Delete UID of treated message of more than 5 minutes
            toDelete.clear();
            for (final Entry<String, Long> entry : pTreatedMessages.entrySet()) {
                final String msgUid = entry.getKey();
                final long newTTL = entry.getValue() + delta;
                // Yes, I can *update* an entry while iterating
                pTreatedMessages.put(msgUid, newTTL);

                if (newTTL > 300000) {
                    // More than 5 minutes: forget about the message
                    toDelete.add(msgUid);
                }
            }
            for (final String msgUid : toDelete) {
                pTreatedMessages.remove(msgUid);
            }

            // Update the last garbage collection time
            pLastGarbage = System.currentTimeMillis();
        }
    }

    /**
     * Handles a directory update message
     *
     * @param aMessage
     *            Message received from another peer
     * @param aKind
     *            Kind of directory message
     */
    @SuppressWarnings("unchecked")
    private void handleDirectoryMessage(final MessageReceived aMessage,
            final String aKind) {

        switch (aKind) {
        case "newcomer": {
            try {
                // A new peer appears: register it
                final Map<String, Object> peerDump = (Map<String, Object>) aMessage
                        .getContent();
                pDirectory.register(peerDump);

                // Reply to it with our information
                reply(aMessage, pDirectory.getLocalPeer().dump(),
                        "herald/directory/welcome");

            } catch (final ValueError ex) {
                // Invalid UID
                pLogger.log(LogService.LOG_WARNING,
                        "Error registering a newcomer: " + ex);

            } catch (final HeraldException ex) {
                // Error sending reply
                pLogger.log(LogService.LOG_WARNING,
                        "Can't send a welcome message back to the sender: "
                                + ex);
            }
            break;
        }

        case "welcome": {
            try {
                // A peer replied to our 'newcomer' event
                // Message content: result of peer's dump()
                final Map<String, Object> peerDump = (Map<String, Object>) aMessage
                        .getContent();
                pDirectory.register(peerDump);

            } catch (final ValueError ex) {
                pLogger.log(LogService.LOG_WARNING,
                        "Error registering a peer: " + ex);
            }
            break;
        }

        case "bye": {
            // A peer is going away
            // Message content: the Peer UID
            pDirectory.unregister((String) aMessage.getContent());
            break;
        }

        default:
            // Ignore other messages
            break;
        }
    }

    /**
     * Handles an error message
     *
     * @param aMessage
     *            The error message
     * @param aKind
     *            Kind of error
     */
    private void handleError(final MessageReceived aMessage, final String aKind) {

        switch (aKind) {
        case "no-listener": {
            // No listener found for a given message
            final Map<?, ?> content = (Map<?, ?>) aMessage.getContent();
            final String uid = (String) content.get("uid");
            final String subject = (String) content.get("subject");
            if (uid == null || subject == null || uid.isEmpty()
                    || subject.isEmpty()) {
                // Invalid error content, ignore
                return;
            }

            // Set up the exception object
            final NoListener exception = new NoListener(new Target(
                    aMessage.getSender()), uid, subject);

            // Unlock the original message sender
            final EventData<?> eventData = pWaitingEvents.remove(uid);
            if (eventData != null) {
                eventData.raiseException(exception);
            }

            // Notify post() callers
            final WaitingPost waitingPost = pWaitingPosts.remove(uid);
            if (waitingPost != null) {
                waitingPost.errback(this, exception);
            }
            break;
        }

        default:
            // Unknown error
            pLogger.log(LogService.LOG_WARNING, "Unknown kind of error: "
                    + aKind);
            break;
        }
    }

    /*
     * (non-Javadoc)
     *
     * @see org.cohorte.herald.IHeraldInternal#handleMessage(org.cohorte.herald.
     * MessageReceived)
     */
    @Override
    public void handleMessage(final MessageReceived aMessage) {

        synchronized (pGarbageToken) {
            if (pTreatedMessages.containsValue(aMessage.getUid())) {
                // Message already handled, ignore it
                return;
            } else {
                // Store the message UID
                pTreatedMessages.put(aMessage.getUid(),
                        System.currentTimeMillis());
            }
        }

        // Clean up the subject
        final List<String> parts = new LinkedList<>();
        for (final String part : aMessage.getSubject().split("/")) {
            if (!part.isEmpty()) {
                parts.add(part);
            }
        }

        try {
            if (parts.get(0).equals("herald")) {
                // Internal message
                final String category = parts.get(1);
                final String kind = parts.get(2);
                switch (category) {
                case "error":
                    // Error message: handle it, but don't propagate it
                    handleError(aMessage, kind);
                    return;

                case "directory":
                    // Directory update message
                    handleDirectoryMessage(aMessage, kind);
                    break;

                default:
                    break;
                }
            }
        } catch (final IndexOutOfBoundsException ex) {
            // Not enough arguments for a directory update: ignore
        }

        // Notify others of the message
        notify(aMessage);
    }

    /**
     * Component invalidated
     */
    @Invalidate
    public void invalidate() {

        // Stop the garbage collector
        pGarbageTimer.cancel();

        // Stop the thread pool
        pPool.shutdownNow();

        // Clear waiting events
        for (final EventData<?> event : pWaitingEvents.values()) {
            event.set(null);
        }

        synchronized (pGarbageToken) {
            final HeraldException exception = new HeraldTimeout(null,
                    "Herald stops to listen to messages", null);
            for (final WaitingPost waiting : pWaitingPosts.values()) {
                waiting.errback(this, exception);
            }
        }

        // Clean up
        pWaitingEvents.clear();
        pWaitingPosts.clear();
        pGarbageTimer = null;
        pPool = null;
    }

    /**
     * Calls back message senders about responses or notifies the reception of a
     * message
     *
     * @param aMessage
     *            The received message
     */
    private void notify(final MessageReceived aMessage) {

        final String repliesTo = aMessage.getReplyTo();
        if (repliesTo != null && !repliesTo.isEmpty()) {
            // This message is a reply: unlock the sender of the original
            // message
            final EventData<Object> event = pWaitingEvents.remove(repliesTo);
            if (event != null) {
                // Set the data
                event.set(aMessage.getContent());
            }

            synchronized (pGarbageToken) {
                // Notify post() callers
                final WaitingPost waitingPost = pWaitingPosts.get(repliesTo);
                if (waitingPost != null) {
                    waitingPost.callback(this, aMessage);
                    if (waitingPost.isForgetOnFirst()) {
                        // Forget about the message
                        pWaitingPosts.remove(repliesTo);
                    }
                }
            }
        }

        // Compute the list of listeners to notify
        final Set<IMessageListener> listeners = new LinkedHashSet<>();
        final String subject = aMessage.getSubject();

        synchronized (pListeners) {
            for (final Entry<FnMatch, Set<IMessageListener>> entry : pListeners
                    .entrySet()) {
                if (entry.getKey().matches(subject)) {
                    listeners.addAll(entry.getValue());
                }
            }
        }

        if (!listeners.isEmpty()) {
            // Call listeners in the thread pool
            for (final IMessageListener listener : listeners) {
                pPool.execute(new Runnable() {

                    @Override
                    public void run() {

                        try {
                            listener.heraldMessage(Herald.this, aMessage);

                        } catch (final HeraldException ex) {
                            pLogger.log(LogService.LOG_WARNING,
                                    "Error notifying listener " + listener
                                            + ": " + ex, ex);
                        }
                    }
                });
            }

        } else {
            // No listener found: send an error message
            final Map<String, Object> content = new LinkedHashMap<>();
            content.put("uid", aMessage.getUid());
            content.put("subject", aMessage.getSubject());

            try {
                reply(aMessage, content, "herald/error/no-listener");

            } catch (final HeraldException ex) {
                // We can't send an error back
                pLogger.log(LogService.LOG_ERROR,
                        "Can't send an error back to the sender: " + ex);
            }
        }
    }

    /*
     * (non-Javadoc)
     *
     * @see org.cohorte.herald.IHerald#post(org.cohorte.herald.Peer,
     * org.cohorte.herald.Message, org.cohorte.herald.IPostCallback,
     * org.cohorte.herald.IPostErrback)
     */
    @Override
    public String post(final Peer aPeer, final Message aMessage,
            final IPostCallback aCallback, final IPostErrback aErrback)
            throws NoTransport {

        return post(aPeer, aMessage, aCallback, aErrback, 180L, true);
    }

    /*
     * (non-Javadoc)
     *
     * @see org.cohorte.herald.IHerald#post(org.cohorte.herald.Peer,
     * org.cohorte.herald.Message, org.cohorte.herald.IPostCallback,
     * org.cohorte.herald.IPostErrback, java.lang.Long)
     */
    @Override
    public String post(final Peer aPeer, final Message aMessage,
            final IPostCallback aCallback, final IPostErrback aErrback,
            final Long aTimeout) throws NoTransport {

        return post(aPeer, aMessage, aCallback, aErrback, aTimeout, true);
    }

    /*
     * (non-Javadoc)
     *
     * @see org.cohorte.herald.IHerald#post(org.cohorte.herald.Peer,
     * org.cohorte.herald.Message, org.cohorte.herald.IPostCallback,
     * org.cohorte.herald.IPostErrback, java.lang.Long, boolean)
     */
    @Override
    public String post(final Peer aPeer, final Message aMessage,
            final IPostCallback aCallback, final IPostErrback aErrback,
            final Long aTimeout, final boolean aForgetOnFirst)
            throws NoTransport {

        synchronized (pGarbageToken) {
            // Prepare an entry in the waiting posts
            pWaitingPosts.put(aMessage.getUid(), new WaitingPost(aCallback,
                    aErrback, aTimeout, aForgetOnFirst));
        }

        try {
            // Fire the message
            return fire(aPeer, aMessage);

        } catch (final HeraldException ex) {
            // Early clean up in case of exception
            synchronized (pGarbageToken) {
                pWaitingPosts.remove(aMessage.getUid());
            }
            throw ex;
        }
    }

    /*
     * (non-Javadoc)
     *
     * @see org.cohorte.herald.IHerald#post(java.lang.String,
     * org.cohorte.herald.Message, org.cohorte.herald.IPostCallback,
     * org.cohorte.herald.IPostErrback)
     */
    @Override
    public String post(final String aPeerUid, final Message aMessage,
            final IPostCallback aCallback, final IPostErrback aErrback)
            throws UnknownPeer, NoTransport {

        return post(aPeerUid, aMessage, aCallback, aErrback, 180L, true);
    }

    /*
     * (non-Javadoc)
     *
     * @see org.cohorte.herald.IHerald#post(java.lang.String,
     * org.cohorte.herald.Message, org.cohorte.herald.IPostCallback,
     * org.cohorte.herald.IPostErrback, java.lang.Long)
     */
    @Override
    public String post(final String aPeerUid, final Message aMessage,
            final IPostCallback aCallback, final IPostErrback aErrback,
            final Long aTimeout) throws UnknownPeer, NoTransport {

        return post(aPeerUid, aMessage, aCallback, aErrback, aTimeout, true);
    }

    /*
     * (non-Javadoc)
     *
     * @see org.cohorte.herald.IHerald#post(java.lang.String,
     * org.cohorte.herald.Message, org.cohorte.herald.IPostCallback,
     * org.cohorte.herald.IPostErrback, java.lang.Long, boolean)
     */
    @Override
    public String post(final String aPeerUid, final Message aMessage,
            final IPostCallback aCallback, final IPostErrback aErrback,
            final Long aTimeout, final boolean aForgetOnFirst)
            throws UnknownPeer, NoTransport {

        return post(pDirectory.getPeer(aPeerUid), aMessage, aCallback,
                aErrback, aTimeout, aForgetOnFirst);
    }

    /*
     * (non-Javadoc)
     *
     * @see org.cohorte.herald.IHerald#postGroup(java.lang.String,
     * org.cohorte.herald.Message, org.cohorte.herald.IPostCallback,
     * org.cohorte.herald.IPostErrback, java.lang.Long)
     */
    @Override
    public String postGroup(final String aGroupName, final Message aMessage,
            final IPostCallback aCallback, final IPostErrback aErrback,
            final Long aTimeout) throws ValueError, NoTransport {

        // Get all peers known in the group
        final Collection<Peer> allPeers = pDirectory
                .getPeersForGroup(aGroupName);
        if (allPeers.isEmpty()) {
            throw new ValueError("Unknown group: " + aGroupName);
        }

        if (pTransports.isEmpty()) {
            // Make the list of UIDs
            throw new NoTransport(new Target(aGroupName,
                    Target.toUids(allPeers)), "No transport bound yet.");
        }

        synchronized (pGarbageToken) {
            // Prepare an entry in the waiting posts
            pWaitingPosts.put(aMessage.getUid(), new WaitingPost(aCallback,
                    aErrback, aTimeout, false));
        }

        // Group peers by accesses
        final Map<String, Set<Peer>> accesses = new LinkedHashMap<>();
        for (final Peer peer : allPeers) {
            for (final String access : peer.getAccesses()) {
                Utilities.setDefault(accesses, access,
                        new LinkedHashSet<Peer>());
            }
        }

        for (final Entry<String, Set<Peer>> entry : accesses.entrySet()) {
            final String access = entry.getKey();
            final Set<Peer> accessPeers = entry.getValue();

            if (accessPeers.isEmpty()) {
                // Nothing to do
                continue;
            }

            // Find the transport for this access
            final ITransport transport = pTransports.get(access);
            if (transport == null) {
                // No transport for this kind of access
                pLogger.log(LogService.LOG_DEBUG, "No transport for " + access);
                continue;
            }

            final Collection<Peer> reachedPeers;
            try {
                // Try to send the message
                reachedPeers = transport.fireGroup(aGroupName, accessPeers,
                        aMessage);

            } catch (final HeraldException ex) {
                // Try again...
                pLogger.log(LogService.LOG_DEBUG,
                        "Error group-firing message: " + ex, ex);
                continue;
            }

            boolean allDone = true;
            for (final Set<Peer> remainingPeers : accesses.values()) {
                remainingPeers.removeAll(reachedPeers);
                if (!remainingPeers.isEmpty()) {
                    allDone = false;
                }
            }

            if (allDone) {
                break;
            }
        }

        return aMessage.getUid();
    }

    /*
     * (non-Javadoc)
     *
     * @see org.cohorte.herald.IHerald#reply(org.cohorte.herald.MessageReceived,
     * java.lang.Object)
     */
    @Override
    public void reply(final MessageReceived aMessage, final Object aContent)
            throws HeraldException {

        reply(aMessage, aContent, null);
    }

    /*
     * (non-Javadoc)
     *
     * @see org.cohorte.herald.IHerald#reply(org.cohorte.herald.MessageReceived,
     * java.lang.Object, java.lang.String)
     */
    @Override
    public void reply(final MessageReceived aMessage, final Object aContent,
            final String aSubject) throws HeraldException {

        // Normalize the subject
        String subject = aSubject;
        if (subject == null || subject.isEmpty()) {
            subject = "reply/" + aMessage.getSubject();
        }

        // Prepare the message to send
        final Message newMessage = new Message(subject, aContent);

        try {
            // Try to reuse the transport
            fireReply(newMessage, aMessage);
            return;
        } catch (final HeraldException ex) {
            // Can't reuse the transport, use another one
        }

        fire(aMessage.getSender(), newMessage);
    }

    /*
     * (non-Javadoc)
     *
     * @see org.cohorte.herald.IHerald#send(org.cohorte.herald.Peer,
     * org.cohorte.herald.Message)
     */
    @Override
    public Object send(final Peer aPeer, final Message aMessage)
            throws HeraldException {

        try {
            return send(aPeer, aMessage, null);

        } catch (final HeraldTimeout ex) {
            // Can't happen
            return null;
        }
    }

    /*
     * (non-Javadoc)
     *
     * @see org.cohorte.herald.IHerald#send(org.cohorte.herald.Peer,
     * org.cohorte.herald.Message, java.lang.Long)
     */
    @Override
    public Object send(final Peer aPeer, final Message aMessage,
            final Long aTimeout) throws HeraldException {

        // Prepare the event bean
        final EventData<Object> event = new EventData<>();
        pWaitingEvents.put(aMessage.getUid(), event);

        try {
            // Fire the message
            fire(aPeer, aMessage);

            // Message sent: wait for an answer
            if (event.waitEvent(aTimeout)) {
                final Object data = event.getData();
                if (data != null) {
                    return data;

                } else {
                    // Herald is stopping...
                    throw new HeraldTimeout(new Target(aPeer),
                            "Herald stops listening to message", aMessage);
                }

            } else {
                throw new HeraldTimeout(new Target(aPeer),
                        "Timeout reached before receiving a reply", aMessage);
            }

        } catch (final EventException ex) {
            // Something went wrong waiting for the event
            if (ex.getCause() instanceof HeraldException) {
                throw (HeraldException) ex.getCause();
            } else {
                throw new HeraldException(new Target(aPeer),
                        "Error waiting for an answer: " + ex, ex);
            }

        } finally {
            // Clean up
            pWaitingEvents.remove(aMessage.getUid());
        }
    }

    /*
     * (non-Javadoc)
     *
     * @see org.cohorte.herald.IHerald#send(java.lang.String,
     * org.cohorte.herald.Message)
     */
    @Override
    public Object send(final String aPeerUid, final Message aMessage)
            throws HeraldException {

        try {
            return send(aPeerUid, aMessage, null);

        } catch (final HeraldTimeout ex) {
            // Can't happen
            return null;
        }
    }

    /*
     * (non-Javadoc)
     *
     * @see org.cohorte.herald.IHerald#send(java.lang.String,
     * org.cohorte.herald.Message, java.lang.Long)
     */
    @Override
    public Object send(final String aPeerUid, final Message aMessage,
            final Long aTimeout) throws HeraldException {

        return send(pDirectory.getPeer(aPeerUid), aMessage, aTimeout);
    }

    /**
     * A message listener has gone away
     *
     * @param aListener
     *            A message listener
     * @param aReference
     *            The injected service reference
     */
    @Unbind(id = ID_LISTENERS)
    protected void unbindListener(final IMessageListener aListener,
            final ServiceReference<IMessageListener> aReference) {

        synchronized (pListeners) {
            final Set<FnMatch> filters = pListenersFilters.remove(aListener);
            if (filters == null) {
                // Unknown listener
                return;
            }

            for (final FnMatch match : filters) {
                // Forget about the listener
                final Set<IMessageListener> listeners = pListeners.get(match);
                listeners.remove(aListener);

                // Clean up
                if (listeners.isEmpty()) {
                    pListeners.remove(match);
                }
            }
        }
    }

    /**
     * A transport implementation has gone away
     *
     * @param aTransport
     *            A transport implementation
     * @param aReference
     *            The injected service reference
     */
    @Unbind(id = ID_TRANSPORTS)
    protected void unbindTransport(final ITransport aTransport,
            final ServiceReference<ITransport> aReference) {

        final String accessId = (String) aReference
                .getProperty(IConstants.PROP_ACCESS_ID);
        if (accessId == null || accessId.isEmpty()) {
            // Ignore invalid access IDs
            return;
        }

        synchronized (pTransports) {
            // Forget about the service
            pTransports.remove(accessId);

            if (pTransports.isEmpty()) {
                // No more transport service: we can't provide the service
                pController = false;
            }
        }
    }

    /**
     * A message listener has been updated
     *
     * @param aListener
     *            A message listener
     * @param aReference
     *            The injected service reference
     */
    @Modified(id = ID_LISTENERS)
    protected void updateListener(final IMessageListener aListener,
            final ServiceReference<IMessageListener> aReference) {

        final Object rawFilters = aReference
                .getProperty(IConstants.PROP_FILTERS);
        final Set<String> newFilters = new LinkedHashSet<>();
        if (rawFilters instanceof String) {
            // Single filter
            newFilters.add((String) rawFilters);

        } else if (rawFilters instanceof String[]) {
            // Copy the array
            newFilters.addAll(Arrays.asList((String[]) rawFilters));

        } else {
            // Unreadable filters: forget about the listener
            unbindListener(aListener, aReference);
            return;
        }

        synchronized (pListeners) {
            // Get current filters
            final Set<FnMatch> currentFilters = Utilities.setDefault(
                    pListenersFilters, aListener, new LinkedHashSet<FnMatch>());
            final Set<String> currentFiltersStrings = new LinkedHashSet<>(
                    currentFilters.size());
            for (final FnMatch filter : currentFilters) {
                currentFiltersStrings.add(filter.toString());
            }

            // Compare with known state
            final Set<String> addedFilters = new LinkedHashSet<>(newFilters);
            addedFilters.removeAll(currentFiltersStrings);

            final Set<String> removedFilters = new LinkedHashSet<>(
                    currentFiltersStrings);
            removedFilters.removeAll(newFilters);

            // Add new filters
            for (final String filter : addedFilters) {
                // Compile the filter
                final FnMatch match = new FnMatch(filter);

                // Associate the listener to the filter
                Utilities.setDefault(pListeners, match,
                        new LinkedHashSet<IMessageListener>()).add(aListener);
                Utilities.setDefault(pListenersFilters, aListener,
                        new LinkedHashSet<FnMatch>()).add(match);
            }

            // Clean up removed ones
            for (final String filter : removedFilters) {
                // Compile the filter
                final FnMatch match = new FnMatch(filter);

                // Remove the listener from the registry
                final Set<IMessageListener> listeners = pListeners.get(match);
                listeners.remove(aListener);

                // Clean up
                if (listeners.isEmpty()) {
                    pListeners.remove(match);
                }
            }
        }
    }

    /**
     * Component validated
     */
    @Validate
    public void validate() {

        // Start the notification thread pool
        pPool = Executors.newFixedThreadPool(5);

        // Start the garbage collector
        pGarbageTimer = new LoopTimer(30000, new Runnable() {

            @Override
            public void run() {

                garbageCollect();
            }
        }, "Herald-GC");
        pGarbageTimer.start();
    }
}
