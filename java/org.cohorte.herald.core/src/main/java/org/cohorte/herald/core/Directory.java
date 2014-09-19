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

import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collection;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.LinkedList;
import java.util.Map;
import java.util.Map.Entry;
import java.util.Set;
import java.util.UUID;

import org.apache.felix.ipojo.annotations.Bind;
import org.apache.felix.ipojo.annotations.Component;
import org.apache.felix.ipojo.annotations.Instantiate;
import org.apache.felix.ipojo.annotations.Provides;
import org.apache.felix.ipojo.annotations.Requires;
import org.apache.felix.ipojo.annotations.Unbind;
import org.apache.felix.ipojo.annotations.Validate;
import org.cohorte.herald.Access;
import org.cohorte.herald.IConstants;
import org.cohorte.herald.IDirectory;
import org.cohorte.herald.IDirectoryInternal;
import org.cohorte.herald.IDirectoryListener;
import org.cohorte.herald.ITransportDirectory;
import org.cohorte.herald.Peer;
import org.cohorte.herald.RawAccess;
import org.cohorte.herald.exceptions.UnknownPeer;
import org.cohorte.herald.exceptions.ValueError;
import org.osgi.framework.BundleContext;
import org.osgi.framework.ServiceReference;
import org.osgi.service.log.LogService;

/**
 * Implementation of the Herald Core Directory
 *
 * @author Thomas Calmant
 */
@Component(publicFactory = false)
@Provides(specifications = IDirectory.class)
@Instantiate(name = "herald-directory")
public class Directory implements IDirectory, IDirectoryInternal {

    /** iPOJO requirement ID */
    private static final String ID_DIRECTORIES = "directories";

    /** iPOJO requirement ID */
    private static final String ID_LISTENERS = "listeners";

    /** The bundle context */
    private final BundleContext pContext;

    /** Access ID -&gt; Transport directory */
    private final Map<String, ITransportDirectory> pDirectories = new LinkedHashMap<>();

    /** Group Name -&gt; Peers */
    private final Map<String, Set<Peer>> pGroups = new LinkedHashMap<>();

    /** Directory event listeners */
    @Requires(id = ID_LISTENERS, optional = true)
    private IDirectoryListener[] pListeners;

    /** Local peer bean */
    private Peer pLocalPeer;

    /** The logger */
    @Requires(optional = true)
    private LogService pLogger;

    /** Peer Name -&gt; Peer UIDs */
    private final Map<String, Set<String>> pNames = new LinkedHashMap<>();

    /** Peer UID -&gt; Peer bean registry */
    private final Map<String, Peer> pPeers = new LinkedHashMap<>();

    /**
     * Component instantiation
     *
     * @param aBundleContext
     *            The bundle context
     */
    public Directory(final BundleContext aBundleContext) {

        pContext = aBundleContext;
    }

    /**
     * A transport directory has been bound
     *
     * @param aDirectory
     *            A transport directory
     * @param aReference
     *            The injected service reference
     */
    @Bind(id = ID_DIRECTORIES, aggregate = true, optional = true)
    protected synchronized void bindDirectory(
            final ITransportDirectory aDirectory,
            final ServiceReference<ITransportDirectory> aReference) {

        final String accessId = (String) aReference
                .getProperty(IConstants.PROP_ACCESS_ID);
        if (accessId == null || accessId.isEmpty()) {
            // Ignore invalid access IDs
            pLogger.log(LogService.LOG_WARNING, "Invalid access ID for "
                    + aReference + " -- " + aDirectory);
            return;
        }

        // Store the service
        pDirectories.put(accessId, aDirectory);

        // Load corresponding accesses
        for (final Peer peer : pPeers.values()) {
            final Access currentAccess = peer.getAccess(accessId);
            if (currentAccess instanceof RawAccess) {
                // We need to convert a raw access
                final Access parsedAccess = aDirectory
                        .loadAccess(((RawAccess) currentAccess).getRawData());

                // Update the peer access
                peer.setAccess(accessId, parsedAccess);
            }
        }
    }

    /**
     * A listener has been bound
     *
     * @param aListener
     *            A directory listener
     */
    @Bind(id = ID_LISTENERS)
    protected synchronized void bindListener(final IDirectoryListener aListener) {

        for (final Peer peer : pPeers.values()) {
            aListener.peerRegistered(peer);
        }
    }

    /*
     * (non-Javadoc)
     *
     * @see org.cohorte.herald.IDirectory#dump()
     */
    @Override
    public Map<String, Map<String, Object>> dump() {

        final Map<String, Map<String, Object>> result = new LinkedHashMap<>();
        for (final Peer peer : pPeers.values()) {
            result.put(peer.getUid(), peer.dump());
        }
        return result;
    }

    /**
     * Returns the array of strings corresponding to the value of a
     * comma-separated property value
     *
     * @param aContext
     *            Bundle context
     * @param aKey
     *            Property name
     * @return The parsed array, or an empty array (never null)
     */
    private String[] getListProperty(final BundleContext aContext,
            final String aKey) {

        final String value = getProperty(aContext, aKey);
        if (value == null) {
            return new String[0];
        }

        return value.split(",");
    }

    /*
     * (non-Javadoc)
     *
     * @see org.cohorte.herald.IDirectory#getLocalPeer()
     */
    @Override
    public Peer getLocalPeer() {

        return pLocalPeer;
    }

    /*
     * (non-Javadoc)
     *
     * @see org.cohorte.herald.IDirectory#getLocalUid()
     */
    @Override
    public String getLocalUid() {

        return pLocalPeer.getUid();
    }

    /*
     * (non-Javadoc)
     *
     * @see org.cohorte.herald.IDirectory#getPeer(java.lang.String)
     */
    @Override
    public Peer getPeer(final String aUid) throws UnknownPeer {

        final Peer peer = pPeers.get(aUid);
        if (peer == null) {
            throw new UnknownPeer(aUid);
        }

        return peer;
    }

    /*
     * (non-Javadoc)
     *
     * @see org.cohorte.herald.IDirectory#getPeers()
     */
    @Override
    public Collection<Peer> getPeers() {

        return new ArrayList<>(pPeers.values());
    }

    /*
     * (non-Javadoc)
     *
     * @see org.cohorte.herald.IDirectory#getPeersForGroup(java.lang.String)
     */
    @Override
    public Collection<Peer> getPeersForGroup(final String aGroupName) {

        final Set<Peer> peers = pGroups.get(aGroupName);
        if (peers == null) {
            return new LinkedList<>();
        } else {
            return new ArrayList<>(peers);
        }
    }

    /*
     * (non-Javadoc)
     *
     * @see org.cohorte.herald.IDirectory#getPeersForName(java.lang.String)
     */
    @Override
    public Collection<Peer> getPeersForName(final String aName) {

        // Try the name as a UID
        final Peer peer = pPeers.get(aName);
        if (peer != null) {
            return Arrays.asList(peer);
        }

        final Set<Peer> peers = new LinkedHashSet<>();
        final Set<String> uids = pNames.get(aName);
        if (uids != null) {
            for (final String uid : uids) {
                peers.add(pPeers.get(uid));
            }
        }

        return peers;
    }

    /*
     * (non-Javadoc)
     *
     * @see org.cohorte.herald.IDirectory#getPeersForNode(java.lang.String)
     */
    @Override
    public Collection<Peer> getPeersForNode(final String aNodeUid) {

        final Set<Peer> peers = new LinkedHashSet<>();
        for (final Peer peer : pPeers.values()) {
            if (peer.getNodeUid().equals(aNodeUid)) {
                peers.add(peer);
            }
        }

        return peers;
    }

    /**
     * Returns the value of the framework or system property with the given name
     *
     * @param aContext
     *            Bundle context
     * @param aKey
     *            Property name
     * @return Property value, or null
     */
    private String getProperty(final BundleContext aContext, final String aKey) {

        String value = aContext.getProperty(aKey);
        if (value == null) {
            // Not done in Equinox
            value = System.getProperty(aKey);
        }
        return value;
    }

    /**
     * Component invalidated
     */
    public void invalidate() {

        pPeers.clear();
        pGroups.clear();
        pNames.clear();
        pLocalPeer = null;
    }

    /*
     * (non-Javadoc)
     *
     * @see org.cohorte.herald.IDirectory#load(java.util.Map)
     */
    @Override
    public void load(final Map<String, Map<String, Object>> aDump) {

        for (final Entry<String, Map<String, Object>> entry : aDump.entrySet()) {
            final String uid = entry.getKey();
            if (!pPeers.containsKey(uid)) {
                try {
                    // Do not reload known peers
                    register(entry.getValue());

                } catch (final ValueError ex) {
                    pLogger.log(LogService.LOG_WARNING, "Error loading dump: "
                            + ex);
                }
            }
        }
    }

    /**
     * Constructs the bean representing the local peer (this framework), using
     * framework properties
     *
     * @param aContext
     *            The bundle context
     * @return The local peer bean
     */
    private Peer makeLocalPeer() {

        // Get the peer UID
        String peerUid = getProperty(pContext, IConstants.FWPROP_PEER_UID);
        if (peerUid == null || peerUid.isEmpty()) {
            peerUid = UUID.randomUUID().toString();
        }

        // Node UID
        final String nodeUid = getProperty(pContext, IConstants.FWPROP_NODE_UID);

        // Groups
        final String[] rawGroups = getListProperty(pContext,
                IConstants.FWPROP_PEER_GROUPS);
        final Set<String> groups = new LinkedHashSet<>(Arrays.asList(rawGroups));

        // Add pre-configured groups
        groups.add("all");
        if (nodeUid != null && !nodeUid.isEmpty()) {
            groups.add(nodeUid);
        }

        // Make the bean
        final Peer peer;
        try {
            peer = new Peer(peerUid, nodeUid, groups, this);
        } catch (final ValueError ex) {
            // Never happens, but who knows...
            pLogger.log(LogService.LOG_ERROR,
                    "Error creating the local peer bean: " + ex);
            return null;
        }

        // Setup node and name information
        peer.setName(getProperty(pContext, IConstants.FWPROP_PEER_NAME));
        peer.setNodeName(getProperty(pContext, IConstants.FWPROP_NODE_NAME));
        return peer;
    }

    /**
     * Notifies all listeners that a peer has been registered
     *
     * @param aPeer
     *            The registered peer
     */
    private void notifyPeerRegistered(final Peer aPeer) {

        for (final IDirectoryListener listener : pListeners) {
            listener.peerRegistered(aPeer);
        }
    }

    /**
     * Notifies all listeners that a peer has been unregistered
     *
     * @param aPeer
     *            The unregistered peer
     */
    private void notifyPeerUnregistered(final Peer aPeer) {

        for (final IDirectoryListener listener : pListeners) {
            listener.peerUnregistered(aPeer);
        }
    }

    /**
     * Notifies all listeners that a peer has been updated
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
    private void notifyPeerUpdated(final Peer aPeer, final String aAccessId,
            final Access aData, final Access aPrevious) {

        for (final IDirectoryListener listener : pListeners) {
            listener.peerUpdated(aPeer, aAccessId, aData, aPrevious);
        }
    }

    /*
     * (non-Javadoc)
     *
     * @see
     * org.cohorte.herald.IDirectoryInternal#peerAccessSet(org.cohorte.herald
     * .Peer, java.lang.String, org.cohorte.herald.Access)
     */
    @Override
    public void peerAccessSet(final Peer aPeer, final String aAccessId,
            final Access aData) {

        final ITransportDirectory directory = pDirectories.get(aAccessId);
        if (directory == null) {
            // No transport directory for this kind of access
            return;
        }

        // Notify this directory
        directory.peerAccessSet(aPeer, aData);

        if (pPeers.containsKey(aPeer.getUid())) {
            // Notify listeners only if the peer is already/still registered
            notifyPeerUpdated(aPeer, aAccessId, aData, null);
        }
    }

    /*
     * (non-Javadoc)
     *
     * @see
     * org.cohorte.herald.IDirectoryInternal#peerAccessUnset(org.cohorte.herald
     * .Peer, java.lang.String, org.cohorte.herald.Access)
     */
    @Override
    public void peerAccessUnset(final Peer aPeer, final String aAccessId,
            final Access aData) {

        final ITransportDirectory directory = pDirectories.get(aAccessId);
        if (directory == null) {
            // No transport directory for this kind of access
            return;
        }

        // Notify this directory
        directory.peerAccessUnset(aPeer, aData);

        // Notify directory listeners
        notifyPeerUpdated(aPeer, aAccessId, null, aData);

        if (!aPeer.hasAccesses()) {
            unregister(aPeer.getUid());
        }
    }

    /*
     * (non-Javadoc)
     *
     * @see org.cohorte.herald.IDirectory#register(java.util.Map)
     */
    @Override
    @SuppressWarnings({ "unchecked", "rawtypes" })
    public synchronized Peer register(final Map<String, Object> aDescription)
            throws ValueError {

        final String uid = (String) aDescription.get("uid");
        if (pLocalPeer.getUid().equals(uid)) {
            // Ignore local peer
            return null;
        }

        boolean peerUpdate = true;
        Peer peer = pPeers.get(uid);
        if (peer == null) {
            // Peer is unknown: full registration
            peerUpdate = false;

            // Extract groups
            final Set<String> groups = new LinkedHashSet<>();
            final Object rawGroups = aDescription.get("groups");
            if (rawGroups instanceof String[]) {
                groups.addAll(Arrays.asList((String[]) rawGroups));
            } else if (rawGroups instanceof Collection) {
                groups.addAll((Collection) rawGroups);
            }

            // Make the new peer bean
            peer = new Peer(uid, (String) aDescription.get("node_uid"), groups,
                    this);
            peer.setName((String) aDescription.get("name"));
            peer.setNodeName((String) aDescription.get("node_name"));
        }

        // In any case, parse and store (new/updated) accesses
        final Map<String, Object> accesses = (Map<String, Object>) aDescription
                .get("accesses");
        for (final Entry<String, Object> entry : accesses.entrySet()) {
            // Get the access ID
            final String accessId = entry.getKey();

            // Find the associated transport directory and load the access
            Access data;
            final ITransportDirectory directory = pDirectories.get(accessId);
            if (directory != null) {
                data = directory.loadAccess(entry.getValue());
            } else {
                // No directory yet
                data = new RawAccess(accessId, entry.getValue());
            }

            // Store the data
            peer.setAccess(accessId, data);
        }

        if (!peerUpdate) {
            // Store the peer after accesses have been set
            // (avoids to notify about update before registration)
            pPeers.put(uid, peer);

            // Store in names
            final Set<String> names = Utilities.setDefault(pNames,
                    peer.getName(), new LinkedHashSet<String>());
            names.add(uid);

            // Store in groups
            for (final String group : peer.getGroups()) {
                final Set<Peer> peers = Utilities.setDefault(pGroups, group,
                        new LinkedHashSet<Peer>());
                peers.add(peer);
            }

            // Notify about registration only once (ignore access updates)
            notifyPeerRegistered(peer);
        }

        return peer;
    }

    /**
     * A transport directory has gone away
     *
     * @param aDirectory
     *            A transport directory
     * @param aReference
     *            The injected service reference
     */
    @Unbind(id = ID_DIRECTORIES)
    protected synchronized void unbindDirectory(
            final ITransportDirectory aDirectory,
            final ServiceReference<ITransportDirectory> aReference) {

        final String accessId = (String) aReference
                .getProperty(IConstants.PROP_ACCESS_ID);
        if (accessId == null || accessId.isEmpty()) {
            // Ignore invalid access IDs
            return;
        }

        // Forget about the service
        pDirectories.remove(accessId);

        // Update accesses
        for (final Peer peer : pPeers.values()) {
            final Access currentAccess = peer.getAccess(accessId);
            if (currentAccess != null) {
                peer.setAccess(accessId,
                        new RawAccess(accessId, currentAccess.dump()));
            }
        }
    }

    /*
     * (non-Javadoc)
     *
     * @see org.cohorte.herald.IDirectory#unregister(java.lang.String)
     */
    @Override
    public synchronized Peer unregister(final String aUid) {

        final Peer peer = pPeers.remove(aUid);
        if (peer == null) {
            // Unknown peer: stop there
            return null;
        }

        // Remove it from dictionaries
        final Set<String> uids = pNames.get(peer.getName());
        uids.remove(aUid);
        if (uids.isEmpty()) {
            // No more UIDs for this name: clean up
            pNames.remove(peer.getName());
        }

        for (final String group : peer.getGroups()) {

            final Set<Peer> peers = pGroups.get(group);
            peers.remove(peer);
            if (!"all".equals(group) && peers.isEmpty()) {
                // No more peers for this group: clean up
                pGroups.remove(group);
            }
        }

        // Notify listeners
        notifyPeerUnregistered(peer);
        return peer;
    }

    /**
     * Component validated
     *
     * @param aContext
     *            Bundle context
     */
    @Validate
    public void validate() {

        // Clean up everything (just in case)
        pPeers.clear();
        pNames.clear();
        pGroups.clear();

        // Prepare the local peer
        pLocalPeer = makeLocalPeer();
        for (final String group : pLocalPeer.getGroups()) {
            pGroups.put(group, new LinkedHashSet<Peer>());
        }
    }
}
