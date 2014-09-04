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
 * Specification of the directory of a transport implementation
 *
 * @author Thomas Calmant
 */
public interface ITransportDirectory {

    /**
     * Requests the transport directory load create an access bean from the
     * given data, result of {@link Access#dump()}.
     *
     * @param aData
     *            Raw access data, result of {@link Access#dump()}
     * @return An access bean
     */
    Access loadAccess(Object aData);

    /**
     * Called by the Core Directory when the access data corresponding to this
     * transport has been updated in a peer
     *
     * @param aPeer
     *            The updated peer
     * @param aData
     *            The new access data (previously loaded with
     *            {@link #loadAccess(Object)}
     */
    void peerAccessSet(Peer aPeer, Access aData);

    /**
     * Called by the Core Directory when the access data corresponding to this
     * transport has been removed from a peer
     *
     * @param aPeer
     *            The updated peer
     * @param aData
     *            The previous access data
     */
    void peerAccessUnset(Peer aPeer, Access aData);
}
