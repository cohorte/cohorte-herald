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

package org.cohorte.herald;

/**
 * Specification of a directory event listener
 *
 * @author Thomas Calmant
 */
public interface IDirectoryListener {

    /**
     * Notification about the registration of a peer
     *
     * @param aPeer
     *            The registered peer
     */
    void peerRegistered(Peer aPeer);

    /**
     * Notifies about the unregistration of a peer
     * 
     * @param aPeer
     *            The unregistered peer
     */
    void peerUnregistered(Peer aPeer);

    /**
     * Notifies about the update of the access of a peer
     *
     * @param aPeer
     *            The modified peer
     * @param aAccessId
     *            ID of the modified access
     * @param aData
     *            New access data (null on unset)
     * @param aPrevious
     *            Previous access data (null on first set)
     */
    void peerUpdated(Peer aPeer, String aAccessId, Access aData,
            Access aPrevious);
}
