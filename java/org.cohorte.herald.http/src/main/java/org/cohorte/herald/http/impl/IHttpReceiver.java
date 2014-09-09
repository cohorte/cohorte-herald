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

import java.util.Map;

import org.cohorte.herald.http.HTTPAccess;

/**
 * Specification of the HTTP transport reception side
 *
 * @author Thomas Calmant
 */
public interface IHttpReceiver {

    /**
     * Returns the description of the access to the local servlet
     *
     * @return The description of the local access
     */
    HTTPAccess getAccessInfo();

    /**
     * Grabs the description of the peer with the given information.
     *
     * @param aHostAddress
     *            The address of the peer
     * @param aPort
     *            The HTTP port of the peer
     * @param aPath
     *            The path to the Herald servlet
     * @return The result of the Peer's dump() method, or null
     */
    Map<String, Object> grabPeer(String aHostAddress, int aPort, String aPath);
}
