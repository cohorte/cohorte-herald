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

package org.cohorte.herald.exceptions;

import org.cohorte.herald.Target;

/**
 * No peer matches the UID used in a call
 *
 * @author Thomas Calmant
 */
public class UnknownPeer extends HeraldException {

    /** Serialization version UID */
    private static final long serialVersionUID = 1L;

    /**
     * Sets up the exception
     *
     * @param aUid
     *            UID of the unknown Peer
     */
    public UnknownPeer(final String aUid) {

        super(new Target(aUid), "Unknown peer: " + aUid);
    }
}
