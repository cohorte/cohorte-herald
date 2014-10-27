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
import org.cohorte.herald.xmpp.IBotListener;
import org.cohorte.herald.xmpp.IXmppConstants;
import org.cohorte.herald.xmpp.IXmppDirectory;
import org.cohorte.herald.xmpp.XmppAccess;
import org.cohorte.herald.xmpp.XmppExtra;
import org.jabsorb.ng.JSONSerializer;
import org.jabsorb.ng.serializer.MarshallException;
import org.jabsorb.ng.serializer.UnmarshallException;
import org.osgi.service.log.LogService;

import rocks.xmpp.core.Jid;
import rocks.xmpp.core.session.XmppSession;
import rocks.xmpp.core.stanza.model.AbstractMessage.Type;
import rocks.xmpp.extensions.delay.model.DelayedDelivery;
import rocks.xmpp.extensions.muc.Occupant;

/**
 * Implementation of the Herald XMPP transport
 *
 * @author Thomas Calmant
 */
@Component(name = "herald-xmpp-transport-factory")
@Provides(specifications = ITransport.class)
public class XmppTransport implements ITransport, IBotListener {

    @ServiceProperty(name = IConstants.PROP_ACCESS_ID,
            value = IXmppConstants.ACCESS_ID)
    private String pAccessId;

    /** The XMPP bot */
    private Bot pBot;

    /** The transport service controller */
    @ServiceController
    private boolean pController;

    /** The Herald core directory */
    @Requires
    private IDirectory pDirectory;

    /** The Herald core service */
    @Requires
    private IHeraldInternal pHerald;

    /** XMPP server host */
    @Property(name = "xmpp.server", value = "localhost")
    private String pHost;

    /** The join key */
    @Property(name = "xmpp.monitor.key")
    private String pKey;

    /** The logger */
    @Requires
    private LogService pLogger;

    /** String JID of the main room */
    @Property(name = "xmpp.room.jid")
    private String pMainRoom;

    /** The parsed JID of the main room */
    private Jid pMainRoomJid;

    /** The monitor JID */
    @Property(name = "xmpp.monitor.jid")
    private String pMonitorJid;

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

        Jid groupJid;
        if (aGroup.equals("all")) {
            // Use the main room to contact all peers
            groupJid = pMainRoomJid;

        } else {
            // Use the group as room name
            groupJid = new Jid(aGroup, pMucDomain);
        }

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
     * Component invalidated
     */
    @Invalidate
    public void invalidate() {

        // Clear the bot
        pBot.disconnect();
        pBot = null;

        // Clean up members
        pMucDomain = null;
        pMainRoomJid = null;
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

        // Parse content
        Object content;
        try {
            content = pSerializer.fromJSON(aMessage.getBody());
        } catch (final UnmarshallException ex) {
            // Error parsing content: use the raw body
            pLogger.log(LogService.LOG_ERROR, "Error parsing message content: "
                    + ex, ex);
            content = aMessage.getBody();
        }

        // Get message information
        final String msgUid = aMessage.getThread();
        final String replyTo = aMessage.getParentThread();

        // Prepare the extra information
        final XmppExtra extra = new XmppExtra(senderJid, msgUid);

        // Call back the core service
        final MessageReceived msgReceived = new MessageReceived(msgUid,
                subject, content, senderUid, replyTo, IXmppConstants.ACCESS_ID,
                extra);
        pHerald.handleMessage(msgReceived);
    }

    /*
     * (non-Javadoc)
     * 
     * @see
     * org.cohorte.herald.xmpp.IBotListener#onRoomIn(org.xmpp.extension.muc.
     * ChatRoom, org.xmpp.extension.muc.Occupant)
     */
    @Override
    public void onRoomIn(final Jid aRoomJid, final Occupant aOccupant) {

        if (!pController && aRoomJid.equals(pMainRoomJid)
                && (aOccupant == null || aOccupant.isSelf())) {
            // We're on line, in the main room, register our service
            pController = true;

            // Register our local access
            final Peer localPeer = pDirectory.getLocalPeer();
            localPeer.setAccess(IXmppConstants.ACCESS_ID,
                    new XmppAccess(pBot.getJid()));

            // Send the "new comer" message
            final Message message = new Message("herald/directory/newcomer",
                    localPeer.dump());
            try {
                sendMessage(Type.GROUPCHAT, aRoomJid, message, null);
            } catch (final MarshallException ex) {
                pLogger.log(LogService.LOG_ERROR,
                        "Error sending the 'newcomer' message: " + ex, ex);
            }
        }
    }

    /*
     * (non-Javadoc)
     * 
     * @see
     * org.cohorte.herald.xmpp.IBotListener#onRoomOut(org.xmpp.extension.muc
     * .ChatRoom, org.xmpp.extension.muc.Occupant)
     */
    @Override
    public void onRoomOut(final Jid aRoomJid, final Occupant aOccupant) {

        final String uid = aOccupant.getNick();
        if (!aOccupant.isSelf() && aRoomJid.equals(pMainRoomJid)) {
            // Someone else is leaving the main room: clean up the directory
            try {
                final Peer peer = pDirectory.getPeer(uid);
                peer.unsetAccess(IXmppConstants.ACCESS_ID);

            } catch (final UnknownPeer ex) {
                // Ignore
            }
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

        // Ask the monitor to invite us, using our UID as nickname
        final Peer local = pDirectory.getLocalPeer();
        pLogger.log(LogService.LOG_INFO, "Requesting to join " + pMonitorJid);
        pBot.heraldJoin(local.getUid(), pMonitorJid, pKey, local.getGroups());
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

        // Convert content to JSON
        final String content = pSerializer.toJSON(aMessage.getContent());

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

        // Compute the MUC domain
        pMainRoomJid = Jid.valueOf(pMainRoom);
        pMucDomain = pMainRoomJid.getDomain();

        // Prepare the bot
        pBot = new Bot(this, pLogger);
        try {
            pBot.connect(pHost, pPort);
        } catch (final IOException ex) {
            pLogger.log(LogService.LOG_ERROR,
                    "Error connecting to the XMPP server: " + ex, ex);
        }
    }
}
