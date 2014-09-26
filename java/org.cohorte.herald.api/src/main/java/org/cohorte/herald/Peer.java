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
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.Map;
import java.util.Map.Entry;

/**
 * Represents a peer in Herald
 *
 * @author Thomas Calmant
 */
public class Peer implements Comparable<Peer> {

    /** Accesses available for this peer */
    private final Map<String, Access> pAccesses = new LinkedHashMap<>();

    /** Application ID */
    private final String pApplicationId;

    /** Associated directory */
    private final IDirectoryInternal pDirectory;

    /** The list of groups this peer belongs to */
    private final Collection<String> pGroups = new LinkedHashSet<>();

    /** Peer name */
    private String pName;

    /** Node name */
    private String pNodeName;

    /** Node UID */
    private final String pNodeUid;

    /** Peer UID */
    private final String pUid;

    /**
     * Sets up the peer bean
     *
     * @param aUid
     *            UID of the peer (can't be null nor empty)
     * @param aNodeUid
     *            UID of the node hosting the peer
     * @param aApplicationId
     *            ID of the application of the peer
     * @param aGroups
     *            Groups this peer belongs to
     * @param aDirectory
     *            The Herald core directory associated to the peer
     * @throws ValueError
     *             Invalid peer UID
     */
    public Peer(final String aUid, final String aNodeUid,
            final String aApplicationId, final Collection<String> aGroups,
            final IDirectoryInternal aDirectory) throws ValueError {

        if (aUid == null || aUid.isEmpty()) {
            throw new ValueError("Peer UID can't be empty");
        }

        // Peer information
        pUid = aUid;
        pApplicationId = aApplicationId;
        pName = pUid;
        pDirectory = aDirectory;

        // Node information
        if (aNodeUid == null || aNodeUid.isEmpty()) {
            pNodeUid = aUid;
        } else {
            pNodeUid = aNodeUid;
        }
        pNodeName = pNodeUid;

        if (aGroups != null) {
            pGroups.addAll(aGroups);
        }
    }

    /*
     * (non-Javadoc)
     *
     * @see java.lang.Comparable#compareTo(java.lang.Object)
     */
    @Override
    public int compareTo(final Peer aOther) {

        return pUid.compareTo(aOther.pUid);
    }

    /**
     * Dumps the content of this Peer into a dictionary
     *
     * @return A dictionary describing this peer
     */
    public Map<String, Object> dump() {

        final Map<String, Object> dump = new LinkedHashMap<String, Object>();
        dump.put("uid", pUid);
        dump.put("name", pName);
        dump.put("node_uid", pNodeUid);
        dump.put("node_name", pNodeName);
        dump.put("groups", pGroups.toArray(new String[pGroups.size()]));

        final Map<String, Object> accesses = new LinkedHashMap<>();
        for (final Entry<String, Access> entry : pAccesses.entrySet()) {
            accesses.put(entry.getKey(), entry.getValue().dump());
        }
        dump.put("accesses", accesses);
        return dump;
    }

    /*
     * (non-Javadoc)
     *
     * @see java.lang.Object#equals(java.lang.Object)
     */
    @Override
    public boolean equals(final Object aObj) {

        if (aObj instanceof Peer) {
            final Peer other = (Peer) aObj;
            return pUid.equals(other.pUid);
        }

        return false;
    }

    /**
     * Returns the access data associated to the given access ID
     *
     * @param aAccessId
     *            The access ID of a transport
     * @return The data associated to the transport
     */
    public Access getAccess(final String aAccessId) {

        return pAccesses.get(aAccessId);
    }

    /**
     * @return the list of accesses IDs
     */
    public Collection<String> getAccesses() {

        return new HashSet<>(pAccesses.keySet());
    }

    /**
     * Returns the ID of the application of the peer
     *
     * @return the application ID
     */
    public String getApplicationId() {

        return pApplicationId;
    }

    /**
     * @return the groups
     */
    public Collection<String> getGroups() {

        return new HashSet<>(pGroups);
    }

    /**
     * @return the name
     */
    public String getName() {

        return pName;
    }

    /**
     * @return the nodeName
     */
    public String getNodeName() {

        return pNodeName;
    }

    /**
     * @return the nodeUid
     */
    public String getNodeUid() {

        return pNodeUid;
    }

    /**
     * @return the UID
     */
    public String getUid() {

        return pUid;
    }

    /**
     * Checks if data is associated to the given access ID
     *
     * @param aAccessId
     *            The access ID of a transport
     * @return True if there is an entry for the access ID
     */
    public boolean hasAccess(final String aAccessId) {

        return pAccesses.containsKey(aAccessId);
    }

    /**
     * Checks if the peer has at least one access information
     *
     * @return True if the peer as at least one access
     */
    public boolean hasAccesses() {

        return !pAccesses.isEmpty();
    }

    /*
     * (non-Javadoc)
     *
     * @see java.lang.Object#hashCode()
     */
    @Override
    public int hashCode() {

        return pUid.hashCode();
    }

    /**
     * Sets the information associated to an access ID
     *
     * @param aAccessId
     *            An access ID
     * @param aData
     *            The description associated to the given ID
     */
    public synchronized void setAccess(final String aAccessId,
            final Access aData) {

        final Access oldData = pAccesses.remove(aAccessId);
        if (oldData == null || !oldData.equals(aData)) {
            pAccesses.put(aAccessId, aData);
            pDirectory.peerAccessSet(this, aAccessId, aData);
        }
    }

    /**
     * Sets the name of the peer
     *
     * @param aName
     *            the name of the peer
     */
    public void setName(final String aName) {

        if (aName == null || aName.isEmpty()) {
            pName = pUid;
        } else {
            pName = aName;
        }
    }

    /**
     * Sets the name of the node hosting the peer
     *
     * @param aNodeName
     *            the name of the node
     */
    public void setNodeName(final String aNodeName) {

        if (aNodeName == null || aNodeName.isEmpty()) {
            pNodeName = pNodeUid;
        } else {
            pNodeName = aNodeName;
        }
    }

    /*
     * (non-Javadoc)
     *
     * @see java.lang.Object#toString()
     */
    @Override
    public String toString() {

        if (pName != null && !pName.equals(pUid)) {
            return pName + " (" + pUid + ")";
        } else {
            return pUid;
        }
    }

    /**
     * Removes and returns the description associated to an access ID
     *
     * @param aAccessId
     *            An access ID
     * @return The associated description or null
     */
    public synchronized Access unsetAccess(final String aAccessId) {

        if (!pAccesses.containsKey(aAccessId)) {
            // Unknown access
            return null;
        }

        final Access data = pAccesses.remove(aAccessId);
        pDirectory.peerAccessUnset(this, aAccessId, data);
        return data;
    }
}
