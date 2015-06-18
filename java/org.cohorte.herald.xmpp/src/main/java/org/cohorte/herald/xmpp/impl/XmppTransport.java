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

package org.cohorte.herald.xmpp.impl;

import java.io.IOException;
import java.util.Collection;
import java.util.LinkedHashSet;
import java.util.LinkedList;
import java.util.Set;

import org.apache.felix.ipojo.annotations.Component;
import org.apache.felix.ipojo.annotations.Invalidate;
import org.apache.felix.ipojo.annotations.Property;
import org.apache.felix.ipojo.annotations.Provides;
import org.apache.felix.ipojo.annotations.Requires;
import org.apache.felix.ipojo.annotations.ServiceController;
import org.apache.felix.ipojo.annotations.ServiceProperty;
import org.apache.felix.ipojo.annotations.Validate;
import org.cohorte.herald.HeraldException;
import org.cohorte.herald.IConstants;
import org.cohorte.herald.IDirectory;
import org.cohorte.herald.IHeraldInternal;
import org.cohorte.herald.ITransport;
import org.cohorte.herald.InvalidPeerAccess;
import org.cohorte.herald.Message;
import org.cohorte.herald.MessageReceived;
import org.cohorte.herald.Peer;
import org.cohorte.herald.Target;
import org.cohorte.herald.UnknownPeer;
import org.cohorte.herald.core.utils.MessageUtils;
import org.cohorte.herald.transport.IDiscoveryConstants;
import org.cohorte.herald.transport.PeerContact;
import org.cohorte.herald.xmpp.IXmppConstants;
import org.cohorte.herald.xmpp.IXmppDirectory;
import org.cohorte.herald.xmpp.XmppAccess;
import org.cohorte.herald.xmpp.XmppExtra;
import org.jabsorb.ng.JSONSerializer;
import org.jabsorb.ng.serializer.MarshallException;
import org.jabsorb.ng.serializer.UnmarshallException;
import org.osgi.service.log.LogService;

import rocks.xmpp.core.Jid;
import rocks.xmpp.core.XmppException;
import rocks.xmpp.core.session.XmppSession;
import rocks.xmpp.core.stanza.model.AbstractMessage.Type;
import rocks.xmpp.extensions.data.model.DataForm.Field;
import rocks.xmpp.extensions.delay.model.DelayedDelivery;
import rocks.xmpp.extensions.muc.ChatService;
import rocks.xmpp.extensions.muc.MultiUserChatManager;
import rocks.xmpp.extensions.muc.Occupant;

/**
 * Implementation of the Herald XMPP transport
 *
 * @author Thomas Calmant
 */
@Component(name = "herald-xmpp-transport-factory")
@Provides(specifications = ITransport.class)
public class XmppTransport implements ITransport, IBotListener, IRoomListener {

    @ServiceProperty(name = IConstants.PROP_ACCESS_ID,
            value = IXmppConstants.ACCESS_ID)
    private String pAccessId;

    /** The XMPP bot */
    private Bot pBot;

    /** The peer contact handler */
    private PeerContact pContact;

    /** The transport service controller */
    @ServiceController
    private boolean pController;

    /** Pending room count down */
    private final Set<MarksCallback<Jid>> pCountdowns = new LinkedHashSet<>();

    /** The Herald core directory */
    @Requires
    private IDirectory pDirectory;

    /** The Herald core service */
    @Requires
    private IHeraldInternal pHerald;

    /** XMPP server host */
    @Property(name = "xmpp.server", value = "localhost")
    private String pHost;

    /** The logger */
    @Requires
    private LogService pLogger;

    /** MUC service domain */
    private String pMucDomain;

    /** XMPP server port */
    @Property(name = "xmpp.port", value = "5222")
    private int pPort;

    /** The Jabsorb serializer */
    private final JSONSerializer pSerializer = new JSONSerializer();

    /** The XMPP directory */
    @Requires
    private IXmppDirectory pXmppDirectory;

    /**
     * Creates or joins the given rooms
     *
     * @param aRooms
     *            A list of rooms to join / create
     * @param aNickname
     *            Nickname to use in those rooms
     */
    private void createRooms(final Collection<String> aRooms,
            final String aNickname) {

        if (pMucDomain == null) {
            // No domain found yet
            pMucDomain = findFirstMucDomain();

            if (pMucDomain == null) {
                // No domain available
                return;
            }
        }

        // Prepare the list of room JIDs
        final Set<Jid> roomsJids = new LinkedHashSet<>();
        for (final String room : aRooms) {
            roomsJids.add(getRoomJid(room));
        }

        // Prepare a callback
        synchronized (pCountdowns) {
            pCountdowns.add(new MarksCallback<>(roomsJids,
                    new MarksCallback.ICallback<Jid>() {

                        @Override
                        public void onMarksDone(final Set<Jid> aSucceeded,
                                final Set<Jid> aErrors) {

                            onRoomsReady(aSucceeded, aErrors);
                        }
                    }, pLogger));
        }

        // Prepare rooms configuration
        final Collection<Field> configuration = new LinkedList<>();
        // ... no max users limit
        configuration.add(new Field(Field.Type.TEXT_SINGLE,
                "muc#roomconfig_maxusers", "0"));
        // ... open to anyone
        configuration.add(new Field(Field.Type.TEXT_SINGLE,
                "muc#roomconfig_membersonly", "0"));
        // ... every participant can send invites
        configuration.add(new Field(Field.Type.TEXT_SINGLE,
                "muc#roomconfig_allowinvites", "0"));
        // ... room can disappear
        configuration.add(new Field(Field.Type.TEXT_SINGLE,
                "muc#roomconfig_persistentroom", "0"));
        // ... OpenFire: Forbid nick changes
        configuration.add(new Field(Field.Type.TEXT_SINGLE,
                "muc#roomconfig_canchangenick", "0"));

        // Prepare the room creator
        final RoomCreator roomCreator = new RoomCreator(pBot.getSession(),
                pLogger);
        for (final Jid room : roomsJids) {
            roomCreator.createRoom(room.getLocal(), room.getDomain(),
                    aNickname, configuration, this);
        }
    }

    /**
     * Returns the domain of the first XMPP MUC service available
     *
     * @return The first found MUC domain if any, else null
     */
    private String findFirstMucDomain() {

        try {
            // Get the MUC extension manager
            final XmppSession session = pBot.getSession();
            final MultiUserChatManager mucManager = session
                    .getExtensionManager(MultiUserChatManager.class);

            // Get the list of chat services
            final Collection<ChatService> chatServices = mucManager
                    .getChatServices();

            // Use the first one available (same as Python side)
            return chatServices.iterator().next().getAddress().getDomain();

        } catch (final XmppException ex) {
            pLogger.log(LogService.LOG_ERROR,
                    "Error looking for XMPP MUC chat services: " + ex);
        }

        return null;
    }

    /*
     * (non-Javadoc)
     *
     * @see org.cohorte.herald.ITransport#fire(org.cohorte.herald.Peer,
     * org.cohorte.herald.Message)
     */
    @Override
    public void fire(final Peer aPeer, final Message aMessage)
            throws HeraldException {

        fire(aPeer, aMessage, null);
    }

    /*
     * (non-Javadoc)
     *
     * @see org.cohorte.herald.ITransport#fire(org.cohorte.herald.Peer,
     * org.cohorte.herald.Message, java.lang.Object)
     */
    @Override
    public void fire(final Peer aPeer, final Message aMessage,
            final Object aExtra) throws HeraldException {

        // Get message extra information, if any
        final XmppExtra extra;
        if (aExtra instanceof XmppExtra) {
            extra = (XmppExtra) aExtra;
        } else {
            extra = null;
        }

        // Get the request message UID
        String parentUid = null;
        if (extra != null) {
            parentUid = extra.getParentUid();
        }

        // Try to find the JID of the target
        final Jid jid = getJid(aPeer, extra);
        if (jid == null) {
            // No XMPP access information
            throw new InvalidPeerAccess(new Target(aPeer),
                    "No XMPP access found");
        }
        // update target_peer header
        if (aPeer != null)
        	aMessage.addHeader(Message.MESSAGE_HEADER_TARGET_PEER, aPeer.getUid());
        // Send the XMPP message
        try {
            sendMessage(Type.CHAT, jid, aMessage, parentUid);
        } catch (final MarshallException ex) {
            throw new HeraldException(new Target(aPeer),
                    "Error converting the content of the message to JSON: "
                            + ex, ex);
        }
    }

    /*
     * (non-Javadoc)
     *
     * @see org.cohorte.herald.ITransport#fireGroup(java.lang.String,
     * java.util.Collection, org.cohorte.herald.Message)
     */
    @Override
    public Collection<Peer> fireGroup(final String aGroup,
            final Collection<Peer> aPeers, final Message aMessage)
            throws HeraldException {

        // Get the application ID
        final String appId = pDirectory.getApplicationId();

        // Compute the JID of the group chat room
        Jid groupJid;
        if (aGroup.equals("all") || aGroup.equals("others")) {
            // Use the main room to contact all peers
            groupJid = getRoomJid(appId);

        } else {
            // Use the group as room name
            groupJid = getRoomJid(appId + "--" + aGroup);
        }
        // update target_group header
        if (aGroup!= null)
        	aMessage.addHeader(Message.MESSAGE_HEADER_TARGET_GROUP, aGroup);
        // Send the XMPP message
        try {
            sendMessage(Type.GROUPCHAT, groupJid, aMessage, null);
        } catch (final MarshallException ex) {
            throw new HeraldException(
                    new Target(aGroup, Target.toUids(aPeers)),
                    "Error converting the content of the message to JSON: "
                            + ex, ex);
        }
        return aPeers;
    }

    /**
     * Looks for the JID to use to communicate with a peer
     *
     * @param aPeer
     *            A peer bean or null
     * @param aExtra
     *            The extra information for a reply or null
     * @return The JID to use to reply, or null
     */
    private Jid getJid(final Peer aPeer, final XmppExtra aExtra) {

        Jid jid = null;
        if (aExtra != null) {
            // Try to use the extra information
            jid = aExtra.getSenderJid();
        }

        // Try to read information from the peer
        if (jid == null && aPeer != null) {
            final XmppAccess access = (XmppAccess) aPeer
                    .getAccess(IXmppConstants.ACCESS_ID);
            if (access != null) {
                jid = access.getJid();
            }
        }

        return jid;
    }

    /**
     * Prepares a JID object for the given room in the current MUC domain
     *
     * @param aRoomName
     *            The short name of a room
     * @return A JID object
     */
    public Jid getRoomJid(final String aRoomName) {

        return new Jid(aRoomName, pMucDomain);
    }

    /**
     * Component invalidated
     */
    @Invalidate
    public void invalidate() {

        // Clear the bot
        pBot.disconnect();
        pBot = null;

        // Clean up members
        pContact.clear();
        pContact = null;
        pMucDomain = null;
    }

    /*
     * (non-Javadoc)
     * 
     * @see
     * org.cohorte.herald.xmpp.IBotListener#onMessage(rocks.xmpp.core.stanza
     * .model.client.Message)
     */
    @Override
    public void onMessage(
            final rocks.xmpp.core.stanza.model.client.Message aMessage) {

        // Check subject
        final String subject = aMessage.getSubject();
        if (subject == null || subject.isEmpty()) {
            // No subject: ignore
            return;
        }

        // Avoid delayed messages
        if (aMessage.getExtension(DelayedDelivery.class) != null) {
            // Delayed message: ignore
            return;
        }

        // Get sender information
        final Jid senderJid = aMessage.getFrom();

        // Check if the message is from MultiUser Chat or direct
        final boolean isMucMessage = aMessage.getType() == Type.GROUPCHAT
                || senderJid.getDomain().equals(pMucDomain);

        // Try to find the peer UID of the sender
        String senderUid;
        if (isMucMessage) {
            // Group message: resource is the isolate ID
            senderUid = senderJid.getResource();
        } else {
            try {
                // Get information from our cache
                senderUid = pXmppDirectory.fromJID(senderJid.asBareJid())
                        .getUid();
            } catch (final UnknownPeer ex) {
                // Unknown peer
                senderUid = "<unknown>";
            }
        }

        // Get message information
        final String msgUid = aMessage.getThread();
        final String replyTo = aMessage.getParentThread();
        
        // Parse content
        MessageReceived rcv_msg = null;
    	Object content;    	
    	
        try {
        	//content = pSerializer.fromJSON(aMessage.getBody());
        	rcv_msg = MessageUtils.fromJSON(aMessage.getBody());
    		if (rcv_msg != null) 
    			content = rcv_msg.getContent();
    		else {
    			content = null;	        			
    		}
        } catch (final UnmarshallException ex) {
            // Error parsing content: use the raw body
            pLogger.log(LogService.LOG_ERROR, "Error parsing message content: "
                    + ex, ex);
            content = aMessage.getBody();
            rcv_msg = new MessageReceived(msgUid, subject, content, null, null, null, null);
        }
       
        // Prepare the extra information
        final XmppExtra extra = new XmppExtra(senderJid, msgUid);
        
        rcv_msg.addHeader(Message.MESSAGE_HEADER_UID, msgUid);
        rcv_msg.addHeader(Message.MESSAGE_HEADER_SENDER_UID, senderUid);
        rcv_msg.addHeader(Message.MESSAGE_HEADER_REPLIES_TO, replyTo);
        rcv_msg.setContent(content);
        rcv_msg.setAccess(IXmppConstants.ACCESS_ID);
        rcv_msg.setExtra(extra);
        
        // Call back the core service

        if (subject.startsWith(IDiscoveryConstants.SUBJECT_DISCOVERY_PREFIX)) {
            // Handle discovery message
            try {
                pContact.handleDiscoveryMessage(pHerald, rcv_msg);

            } catch (final HeraldException ex) {
                // Error replying to a discovered peer
                pLogger.log(LogService.LOG_ERROR,
                        "Error replying to a discovered peer: " + ex, ex);
            }
        } else {
            pHerald.handleMessage(rcv_msg);
        }
    }

    /*
     * (non-Javadoc)
     * 
     * @see
     * org.cohorte.herald.xmpp.impl.IRoomListener#onRoomCreated(rocks.xmpp.core
     * .Jid, java.lang.String)
     */
    @Override
    public void onRoomCreated(final Jid aRoomJid, final String aNick) {

        synchronized (pCountdowns) {
            final Set<MarksCallback<Jid>> toRemove = new LinkedHashSet<>();
            for (final MarksCallback<Jid> marksCallback : pCountdowns) {
                // Mark the room
                marksCallback.set(aRoomJid);

                // Check for cleanup
                if (marksCallback.isDone()) {
                    toRemove.add(marksCallback);
                }
            }

            // Clean up
            pCountdowns.removeAll(toRemove);
        }
    }

    /*
     * (non-Javadoc)
     * 
     * @see
     * org.cohorte.herald.xmpp.impl.IRoomListener#onRoomError(rocks.xmpp.core
     * .Jid, java.lang.String, java.lang.String, java.lang.String)
     */
    @Override
    public void onRoomError(final Jid aRoomJid, final String aNick,
            final String aCondition, final String aDescription) {

        synchronized (pCountdowns) {
            final Set<MarksCallback<Jid>> toRemove = new LinkedHashSet<>();
            for (final MarksCallback<Jid> marksCallback : pCountdowns) {
                // Mark the room
                marksCallback.setError(aRoomJid);

                // Check for cleanup
                if (marksCallback.isDone()) {
                    toRemove.add(marksCallback);
                }
            }

            // Clean up
            pCountdowns.removeAll(toRemove);
        }

        pLogger.log(LogService.LOG_ERROR, "Error creating room: "
                + aDescription + " (" + aCondition + ")");
    }

    /*
     * (non-Javadoc)
     *
     * @see
     * org.cohorte.herald.xmpp.impl.IRoomListener#onRoomIn(rocks.xmpp.core.Jid,
     * rocks.xmpp.extensions.muc.Occupant)
     */
    @Override
    public void onRoomIn(final Jid aRoomJid, final Occupant aOccupant) {

        // Nothing to do
    }

    /*
     * (non-Javadoc)
     *
     * @see
     * org.cohorte.herald.xmpp.impl.IRoomListener#onRoomOut(rocks.xmpp.core.Jid,
     * rocks.xmpp.extensions.muc.Occupant)
     */
    @Override
    public void onRoomOut(final Jid aRoomJid, final Occupant aOccupant) {

        final String uid = aOccupant.getNick();
        final Jid appRoomJid = getRoomJid(pDirectory.getApplicationId());

        if (!aOccupant.isSelf() && aRoomJid.equals(appRoomJid)) {
            // Someone else is leaving the main room: clean up the directory
            try {
                final Peer peer = pDirectory.getPeer(uid);
                peer.unsetAccess(IXmppConstants.ACCESS_ID);
                pLogger.log(LogService.LOG_DEBUG, "Peer " + peer
                        + " disconnected from XMPP");

            } catch (final UnknownPeer ex) {
                // Ignore
            }
        }
    }

    /**
     * Called when all MUC rooms have created or joined
     *
     * @param aSucceeded
     *            List of joined rooms
     * @param aErrors
     *            List of room that couldn't be joined
     */
    private void onRoomsReady(final Set<Jid> aSucceeded, final Set<Jid> aErrors) {

        pLogger.log(LogService.LOG_DEBUG, "Client joined rooms: " + aSucceeded);
        if (!aErrors.isEmpty()) {
            pLogger.log(LogService.LOG_ERROR, "Error joining rooms: " + aErrors);
        }

        // We're on line, register our service
        pLogger.log(LogService.LOG_DEBUG,
                "XMPP transport service activating...");
        pController = true;
        pLogger.log(LogService.LOG_INFO, "XMPP transport service activated");

        // Register our local access
        final Peer localPeer = pDirectory.getLocalPeer();
        localPeer.setAccess(pAccessId, new XmppAccess(pBot.getJid()));

        // Start the discovery handshake
        pLogger.log(LogService.LOG_DEBUG, "Sending discovery step 1...");
        final Message message = new Message(
                IDiscoveryConstants.SUBJECT_DISCOVERY_STEP_1, localPeer.dump());
        try {
            sendMessage(Type.GROUPCHAT,
                    getRoomJid(localPeer.getApplicationId()), message, null);
        } catch (final MarshallException ex) {
            pLogger.log(LogService.LOG_ERROR,
                    "Error sending discovery step 1: " + ex, ex);
        }
    }

    /*
     * (non-Javadoc)
     *
     * @see
     * org.cohorte.herald.xmpp.IBotListener#onSessionEnd(org.xmpp.XmppSession)
     */
    @Override
    public void onSessionEnd(final XmppSession aSession) {

        // Clean up our access
        pDirectory.getLocalPeer().unsetAccess(IXmppConstants.ACCESS_ID);

        // Shut down the service
        pController = false;
    }

    /*
     * (non-Javadoc)
     *
     * @see
     * org.cohorte.herald.xmpp.IBotListener#onSessionStart(org.xmpp.XmppSession)
     */
    @Override
    public void onSessionStart(final XmppSession aSession) {

        // Log our JID
        pLogger.log(LogService.LOG_INFO, "Bot connected with JID: "
                + pBot.getJid().asBareJid());

        // Get local peer information
        final Peer localPeer = pDirectory.getLocalPeer();
        final String appId = localPeer.getApplicationId();

        // Create/join rooms for each group
        final Set<String> allRooms = new LinkedHashSet<>();
        for (final String group : localPeer.getGroups()) {
            allRooms.add(appId + "--" + group);
        }
        allRooms.add(appId);

        // Wait to have joined all rooms before activating the service
        pLogger.log(LogService.LOG_DEBUG, "Creating XMPP rooms...");
        createRooms(allRooms, localPeer.getUid());
    }

    /**
     * Prepares and sends a message over XMPP
     *
     * @param aType
     *            Kind of message (chat or groupchat)
     * @param aJid
     *            Target JID or MUC room
     * @param aMessage
     *            Herald message bean
     * @param aParentUid
     *            UID of the message this one replies to (optional)
     * @throws MarshallException
     *             Error converting the content of the message to JSON
     */
    private void sendMessage(final Type aType, final Jid aJid,
            final Message aMessage, final String aParentUid)
            throws MarshallException {

    	// update headers
    	aMessage.addHeader(Message.MESSAGE_HEADER_SENDER_UID, pDirectory.getLocalUid());
        // Convert content to JSON        
    	final String content = MessageUtils.toJSON(aMessage);
    	
        // Prepare the XMPP message
        final rocks.xmpp.core.stanza.model.client.Message xmppMsg = new rocks.xmpp.core.stanza.model.client.Message(
                aJid, aType, content);
        xmppMsg.setFrom(pBot.getJid());
        xmppMsg.setSubject(aMessage.getSubject());
        xmppMsg.setThread(aMessage.getUid());
        if (aParentUid != null) {
            xmppMsg.setParentThread(aParentUid);
        }

        // Send it
        pBot.send(xmppMsg);
    }

    /**
     * Component validated
     */
    @Validate
    public void validate() {

        // Ensure we do not provide the service at first
        pController = false;

        // Prepare the serializer
        try {
            pSerializer.registerDefaultSerializers();
        } catch (final Exception ex) {
            pLogger.log(LogService.LOG_ERROR,
                    "Error initializing the Jabsorb serializer: " + ex, ex);
            return;
        }

        // Prepare the peer contact handler
        pContact = new PeerContact(pDirectory, null, pLogger);

        // Prepare the bot
        pBot = new Bot(this, pLogger, pDirectory.getLocalUid());
        try {
            pBot.connect(pHost, pPort);
        } catch (final IOException ex) {
            pLogger.log(LogService.LOG_ERROR,
                    "Error connecting to the XMPP server: " + ex, ex);
        }
    }
}
