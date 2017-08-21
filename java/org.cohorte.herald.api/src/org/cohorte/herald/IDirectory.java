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
import java.util.Map;

/**
 * Specification of the Herald core directory service
 *
 * @author Thomas Calmant
 */
public interface IDirectory {

    /**
     * Dumps the content of the local directory in a dictionary
     *
     * @return A UID -&gt; description dictionary
     */
    Map<String, Map<String, Object>> dump();

    /**
     * Easy access to the application ID of the local peer
     *
     * @return the application ID of the local peer
     */
    String getApplicationId();

    /**
     * Returns the bean representing the local peer
     *
     * @return the local Peer bean
     */
    Peer getLocalPeer();

    /**
     * Easy access to the local peer UID
     *
     * @return the UID of the local UID
     */
    String getLocalUid();

    /**
     * Returns the Peer bean matching the given peer UID
     *
     * @param aUid
     *            The UID of a peer
     * @return The corresponding Peer bean
     * @throws UnknownPeer
     *             Unknown peer UID
     */
    Peer getPeer(String aUid) throws UnknownPeer;

    /**
     * Returns all known peers
     *
     * @return all known peers
     */
    Collection<Peer> getPeers();

    /**
     * Returns the Peer beans of the peers belonging to the given group
     *
     * @param aGroupName
     *            The name of a group
     * @return A list of Peer beans
     */
    Collection<Peer> getPeersForGroup(String aGroupName);

    /**
     * Returns the Peer beans of the peers having the given name
     *
     * @param aName
     *            The name of a peer
     * @return The peers having the given name
     */
    Collection<Peer> getPeersForName(String aName);

    /**
     * Returns the Peer beans of the peers hosted on the given node
     *
     * @param aNodeUid
     *            The UID of a node
     * @return The peers hosted on the node
     */
    Collection<Peer> getPeersForNode(String aNodeUid);

    /**
     * Loads the content of a dump
     *
     * @param aDump
     *            The dictionary result of a call to {@link #dump()}
     */
    void load(Map<String, Map<String, Object>> aDump);

    /**
     * Registers a peer
     *
     * @param aDescription
     *            Description of the peer, in the format of {@link #dump()}
     * @return The registered Peer bean (null if UID matches local peer)
     * @throws ValueError
     *             Invalid peer UID
     */
    Peer register(Map<String, Object> aDescription) throws ValueError;

    /**
     * Registers a peer, but lets the caller choose when to notify the listeners
     *
     * @param aDescription
     *            Description of the peer, in the format of {@link #dump()}
     * @return An object to notify peer registration listeners later
     * @throws ValueError
     *             Invalid peer UID
     */
    IDelayedNotification registerDelayed(final Map<String, Object> aDescription)
            throws ValueError;

    /**
     * Unregisters a peer from the directory
     *
     * @param aUid
     *            UID of the peer
     * @return The Peer bean if it was known, else null
     */
    Peer unregister(String aUid);
}
