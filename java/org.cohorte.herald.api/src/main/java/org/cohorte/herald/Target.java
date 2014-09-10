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

import java.util.Collection;
import java.util.LinkedHashSet;

/**
 * The description of the target of a message, used in exceptions
 *
 * @author Thomas Calmant
 */
public class Target {

    /**
     * Converts a list of peers to a list of UIDs
     *
     * @param aPeers
     *            A list of peers
     * @return A list of UIDs
     */
    public static Collection<String> toUids(final Collection<Peer> aPeers) {

        final Collection<String> uids = new LinkedHashSet<>();
        if (aPeers == null) {
            return uids;
        }

        for (final Peer peer : aPeers) {
            uids.add(peer.getUid());
        }

        return uids;
    }

    /** The name of a group */
    private final String pGroup;

    /** The UID of a peer */
    private final String pUId;

    /** A list of UIDs */
    private final Collection<String> pUids = new LinkedHashSet<>();

    /**
     * Sets up a single-peer target
     *
     * @param aPeer
     *            The targeted bean
     */
    public Target(final Peer aPeer) {

        this(aPeer != null ? aPeer.getUid() : "<unknown>");
    }

    /**
     * Sets up a single-peer target
     *
     * @param aUid
     *            The UID of targeted peer
     */
    public Target(final String aUid) {

        pUId = aUid;
        pGroup = null;
    }

    /**
     * Sets up a group target
     *
     * @param aGroup
     *            Name of the group
     * @param aUids
     *            UIDs of the peers in the given group
     */
    public Target(final String aGroup, final Collection<String> aUids) {

        pUId = null;
        pGroup = aGroup;
        if (aUids != null) {
            pUids.addAll(aUids);
        }
    }

    /**
     * @return the group
     */
    public String getGroup() {

        return pGroup;
    }

    /**
     * @return the uId
     */
    public String getUId() {

        return pUId;
    }

    /**
     * @return the UIDs
     */
    public Collection<String> getUids() {

        return pUids;
    }
}
