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

package org.cohorte.herald.http.impl;

import org.cohorte.herald.ValueError;

/**
 * Specification of the HTTP transport directory
 *
 * @author Thomas Calmant
 */
public interface IHttpDirectory {

    /**
     * Checks if the peer with the given UID is known to have the given access
     *
     * @param aPeerUid
     *            The UID of a peer
     * @param aHost
     *            The tested peer host
     * @param aPort
     *            The tested HTTP port
     * @return True if the given access matches the peer UID, else false
     * @throws ValueError
     *             Unknown peer UID
     */
    boolean checkAccess(String aPeerUid, String aHost, int aPort)
            throws ValueError;
}
