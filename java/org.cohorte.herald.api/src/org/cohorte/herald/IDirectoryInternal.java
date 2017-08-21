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
 * Specification of the non-service methods the Herald core directory must
 * implement
 *
 * @author Thomas Calmant
 */
public interface IDirectoryInternal {

    /**
     * Easy access to the local peer UID
     *
     * @return the UID of the local UID
     */
    String getLocalUid();

    /**
     * Called by a Peer bean when one of its accesses has been set
     *
     * @param aPeer
     *            The updated peer
     * @param aAccessId
     *            The ID of the modified access
     * @param aData
     *            The access data
     */
    void peerAccessSet(Peer aPeer, String aAccessId, Access aData);

    /**
     * Called by a Peer bean when one of its accesses has been removed
     *
     * @param aPeer
     *            The updated peer
     * @param aAccessId
     *            The ID of the modified access
     * @param aData
     *            The access data
     */
    void peerAccessUnset(Peer aPeer, String aAccessId, Access aData);
}
