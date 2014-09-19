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

import org.cohorte.herald.IDelayedNotification;
import org.cohorte.herald.Peer;

/**
 * Implementation of the delayed notification bean
 *
 * @author Thomas Calmant
 */
public class DelayedNotification implements IDelayedNotification {

    /** The directory to use to notify listeners */
    private final Directory pDirectory;

    /** The peer being registered */
    private final Peer pPeer;

    /**
     * Sets up the delayed notification
     *
     * @param aPeer
     *            The peer being registered
     * @param aDirectory
     *            The directory to call to notify about the registration (null
     *            to ignore notification)
     */
    public DelayedNotification(final Peer aPeer, final Directory aDirectory) {

        pPeer = aPeer;
        pDirectory = aDirectory;
    }

    /*
     * (non-Javadoc)
     *
     * @see org.cohorte.herald.IDelayedNotification#getPeer()
     */
    @Override
    public Peer getPeer() {

        return pPeer;
    }

    /*
     * (non-Javadoc)
     *
     * @see org.cohorte.herald.IDelayedNotification#notifyListeners()
     */
    @Override
    public boolean notifyListeners() {

        if (pDirectory != null) {
            pDirectory.notifyPeerRegistered(pPeer);
            return true;
        }

        return false;
    }
}
