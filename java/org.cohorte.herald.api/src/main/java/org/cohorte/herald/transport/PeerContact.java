/**
 * Copyright 2015 isandlaTech
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

package org.cohorte.herald.transport;

import java.util.LinkedHashMap;
import java.util.Map;

import org.cohorte.herald.HeraldException;
import org.cohorte.herald.IDelayedNotification;
import org.cohorte.herald.IDirectory;
import org.cohorte.herald.IHerald;
import org.cohorte.herald.IMessageListener;
import org.cohorte.herald.MessageReceived;
import org.cohorte.herald.Peer;
import org.cohorte.herald.ValueError;
import org.osgi.service.log.LogService;

/**
 * Standard peer discovery algorithm
 *
 * @author Thomas Calmant
 */
public class PeerContact implements IMessageListener {

    /** Delayed notifications store */
    private final Map<String, IDelayedNotification> pDelayedNotifs = new LinkedHashMap<String, IDelayedNotification>();

    /** The Herald Core directory */
    private final IDirectory pDirectory;

    /** The description loading hook */
    private final IContactHook pHook;

    /** The log service */
    private final LogService pLogger;

    /**
     * Sets up members
     *
     * @param aDirectory
     *            The Herald Core directory
     * @param aHook
     *            A hook to update the description of a peer before storing it
     */
    public PeerContact(final IDirectory aDirectory, final IContactHook aHook,
            final LogService aLogger) {

        pDirectory = aDirectory;
        pHook = aHook;
        pLogger = aLogger;
    }

    /**
     * Clears the pending notifications map
     */
    public void clear() {

        pDelayedNotifs.clear();
    }

    /*
     * (non-Javadoc)
     * 
     * @see
     * org.cohorte.herald.IMessageListener#heraldMessage(org.cohorte.herald.
     * IHerald, org.cohorte.herald.MessageReceived)
     */
    @Override
    public void heraldMessage(final IHerald aHerald,
            final MessageReceived aMessage) throws HeraldException {

        switch (aMessage.getSubject()) {
        case IDiscoveryConstants.SUBJECT_DISCOVERY_STEP_1: {
            /* Step 1: Register the remote peer and reply with our dump */
            try {
                // Prepare the delayed notification
                final IDelayedNotification notification = pDirectory
                        .registerDelayed(loadDescription(aMessage));

                final Peer peer = notification.getPeer();
                if (peer != null) {
                    // Registration succeeded
                    pDelayedNotifs.put(peer.getUid(), notification);

                    // Reply with our description
                    aHerald.reply(aMessage, pDirectory.getLocalPeer().dump(),
                            IDiscoveryConstants.SUBJECT_DISCOVERY_STEP_2);
                }
            } catch (final ValueError ex) {
                pLogger.log(LogService.LOG_ERROR,
                        "Error registering a discovered peer", ex);
            }
            break;
        }

        case IDiscoveryConstants.SUBJECT_DISCOVERY_STEP_2: {
            /*
             * Step 2: Register the dump, notify local listeners, then let the
             * remote peer notify its listeners
             */
            try {
                // Register the peer
                final IDelayedNotification notification = pDirectory
                        .registerDelayed(loadDescription(aMessage));

                final Peer peer = notification.getPeer();
                if (peer != null) {
                    // Registration succeeded
                    aHerald.reply(aMessage, pDirectory.getLocalPeer().dump(),
                            IDiscoveryConstants.SUBJECT_DISCOVERY_STEP_3);
                }

            } catch (final ValueError ex) {
                pLogger.log(LogService.LOG_ERROR,
                        "Error registering a peer using the description it sent");
            }
            break;
        }

        case IDiscoveryConstants.SUBJECT_DISCOVERY_STEP_3: {
            /* Step 3: notify local listeners about the remote peer */
            final IDelayedNotification notification = pDelayedNotifs
                    .remove(aMessage.getSender());
            if (notification != null) {
                notification.notifyListeners();
            }
            break;
        }

        default:
            /* Unknown subject */
            pLogger.log(LogService.LOG_WARNING, "Unknown discovery step: "
                    + aMessage.getSubject());
            break;
        }
    }

    /**
     * Calls the hook method to modify the loaded peer description before giving
     * it to the directory
     *
     * @param aMessage
     *            The received Herald message
     * @return The updated peer description
     */
    private Map<String, Object> loadDescription(final MessageReceived aMessage) {

        @SuppressWarnings("unchecked")
        final Map<String, Object> description = (Map<String, Object>) aMessage
                .getContent();

        if (pHook != null) {
            // Call the hook
            final Map<String, Object> updatedDescription = pHook
                    .updateDescription(aMessage, description);
            if (updatedDescription != null) {
                return updatedDescription;
            }
        }

        return description;
    }
}
