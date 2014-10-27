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
import java.security.KeyManagementException;
import java.security.NoSuchAlgorithmException;
import java.util.Arrays;
import java.util.Collection;

import javax.net.ssl.SSLContext;
import javax.net.ssl.TrustManager;
import javax.security.auth.login.LoginException;

import org.cohorte.herald.xmpp.IBotListener;
import org.osgi.service.log.LogService;

import rocks.xmpp.core.Jid;
import rocks.xmpp.core.XmppException;
import rocks.xmpp.core.session.SessionStatusEvent;
import rocks.xmpp.core.session.SessionStatusListener;
import rocks.xmpp.core.session.TcpConnectionConfiguration;
import rocks.xmpp.core.session.XmppSession;
import rocks.xmpp.core.stanza.MessageEvent;
import rocks.xmpp.core.stanza.MessageListener;
import rocks.xmpp.core.stanza.model.AbstractMessage.Type;
import rocks.xmpp.core.stanza.model.client.Message;
import rocks.xmpp.core.stanza.model.client.Presence;
import rocks.xmpp.core.stream.model.ClientStreamElement;
import rocks.xmpp.extensions.muc.ChatRoom;
import rocks.xmpp.extensions.muc.ChatService;
import rocks.xmpp.extensions.muc.InvitationEvent;
import rocks.xmpp.extensions.muc.InvitationListener;
import rocks.xmpp.extensions.muc.MultiUserChatManager;
import rocks.xmpp.extensions.muc.OccupantEvent;
import rocks.xmpp.extensions.muc.OccupantListener;

/**
 * The XMPP bot implementation, based on Babbler
 *
 * @author Thomas Calmant
 */
public class Bot implements SessionStatusListener, InvitationListener,
        MessageListener {

    /** The listener */
    private final IBotListener pListener;

    /** The log service */
    private final LogService pLogger;

    /** The chat service */
    private ChatService pMucChatService;

    /** The MultiUserChat manager */
    private MultiUserChatManager pMucManager;

    /** The nick used in MultiUserChat rooms */
    private String pNickName;

    /** The XMPP session */
    private XmppSession pSession;

    /**
     * Sets up the bot
     *
     * @param aListener
     *            The event listener
     * @param aLogger
     *            The log service to use
     */
    public Bot(final IBotListener aListener, final LogService aLogger) {

        pListener = aListener;
        pLogger = aLogger;
    }

    /**
     * Connects to the server and logs in anonymously
     *
     * @param aHost
     *            XMPP server host
     * @param aPort
     *            XMPP server port
     * @throws IOException
     *             Error during connection or login
     */
    public void connect(final String aHost, final int aPort) throws IOException {

        // Prepare the XMPP session
        final TcpConnectionConfiguration tcpConfig;
        try {
            tcpConfig = TcpConnectionConfiguration.builder().hostname(aHost)
                    .port(aPort).sslContext(makeSSLContext()).build();

        } catch (final NoSuchAlgorithmException | KeyManagementException ex) {
            pLogger.log(LogService.LOG_ERROR, "Can't create the SSL context: "
                    + ex, ex);
            return;
        }
        pSession = new XmppSession(aHost, tcpConfig);

        // Prepare the MUC manager
        pMucManager = pSession.getExtensionManager(MultiUserChatManager.class);

        // Register to events
        pSession.addSessionStatusListener(this);
        pMucManager.addInvitationListener(this);
        pSession.addMessageListener(this);

        // Connect
        pSession.connect();

        // Log in
        try {
            pSession.loginAnonymously();
        } catch (final LoginException ex) {
            throw new IOException("Can't login anonymously: " + ex, ex);
        }

        // Send the initial presence
        pSession.send(new Presence());
    }

    /**
     * Disconnects and clears the XMPP session
     */
    public void disconnect() {

        try {
            pSession.close();
        } catch (final IOException ex) {
            pLogger.log(LogService.LOG_WARNING,
                    "Error closing the XMPP session:" + ex, ex);
        }

        pMucChatService = null;
        pMucManager = null;
        pSession = null;
    }

    /**
     * Returns the JID used by this bot
     *
     * @return The (real) JID of this bot
     */
    public Jid getJid() {

        return pSession.getConnectedResource();
    }

    /*
     * (non-Javadoc)
     *
     * @see
     * rocks.xmpp.stanza.StanzaListener#handle(rocks.xmpp.stanza.StanzaEvent)
     */
    @Override
    public void handle(final MessageEvent aEvent) {

        // Extract message information
        final Message msg = aEvent.getMessage();
        final Type msgType = msg.getType();
        if (msgType == null) {
            // Ignore messages without type
            return;
        }

        if (getJid().equals(msg.getFrom())) {
            // Ignore loop back messages
            return;
        }

        switch (msgType) {
        case GROUPCHAT:
            // MUC room chat
            if (msg.getFrom().getResource().equals(pNickName)) {
                // Loop back message: ignore
                return;
            }
            break;

        case NORMAL:
        case CHAT:
            // Basic chat
            break;

        default:
            // Ignore other kinds of message
            return;
        }

        try {
            // Call back the listener
            pListener.onMessage(msg);

        } catch (final RuntimeException ex) {
            // Log possible exceptions here, as they won't be handled by the
            // caller
            pLogger.log(LogService.LOG_ERROR, "Error handling XMPP message: "
                    + ex, ex);
        }
    }

    /**
     * Sends a join message to the monitor
     *
     * @param aNick
     *            MUC nick name
     * @param aMonitorJid
     *            JID of a monitor bot
     * @param aKey
     *            Key to send to the monitor bot
     * @param aGroups
     *            Groups to join
     */
    public void heraldJoin(final String aNick, final String aMonitorJid,
            final String aKey, final Collection<String> aGroups) {

        // Store the nick name
        pNickName = aNick;

        // Prepare the message
        final String groupStr = join(",", aGroups);
        final String messageContent = join(":", "invite", aKey, groupStr);
        final org.cohorte.herald.Message message = new org.cohorte.herald.Message(
                "bootstrap.invite", messageContent);

        // Send it
        sendMessage(Type.CHAT, aMonitorJid, message);
    }

    /*
     * (non-Javadoc)
     *
     * @see
     * rocks.xmpp.extension.muc.InvitationListener#invitationReceived(rocks.xmpp
     * .extension.muc.InvitationEvent)
     */
    @Override
    public void invitationReceived(final InvitationEvent aEvent) {

        if (pNickName == null) {
            // Update our nick name if necessary
            pNickName = pSession.getConnectedResource().getResource();
        }

        // Prepare the chat service
        if (pMucChatService == null) {
            pMucChatService = pMucManager.createChatService(new Jid(aEvent
                    .getRoomAddress().getDomain()));
        }

        // Join the room
        final Jid roomAddress = aEvent.getRoomAddress().asBareJid();
        final ChatRoom room = pMucChatService
                .createRoom(roomAddress.getLocal());

        // Add listeners
        room.addOccupantListener(new OccupantListener() {

            @Override
            public void occupantChanged(final OccupantEvent aEvent) {

                switch (aEvent.getType()) {
                case ENTERED:
                    // Occupant got in
                    pListener.onRoomIn(roomAddress, aEvent.getOccupant());
                    break;

                case BANNED:
                case EXITED:
                case KICKED:
                    // Occupant got away
                    pListener.onRoomOut(roomAddress, aEvent.getOccupant());
                    break;

                default:
                    // Ignore others
                    break;
                }
            }
        });

        try {
            // Enter the room
            room.enter(pNickName);

            // Did it: we have to notify the bot listener here,
            // as the OccupantListener avoids notifying this event
            pListener.onRoomIn(room.getAddress(), null);

        } catch (final XmppException ex) {
            pLogger.log(LogService.LOG_ERROR, "Error joining XMPP room: " + ex,
                    ex);
        }
    }

    /**
     * Acts like Python's join
     *
     * @param aSeparator
     *            Items separator
     * @param aItems
     *            Items to join
     * @return The joined string, or an empty one
     */
    private String join(final String aSeparator, final Collection<?> aItems) {

        // Join elements
        final StringBuilder joinedStr = new StringBuilder();
        for (final Object item : aItems) {
            if (item != null) {
                joinedStr.append(item).append(aSeparator);
            }
        }

        // Remove the last separator
        final int resultLen = joinedStr.length();
        if (resultLen > 0) {
            joinedStr.delete(resultLen - aSeparator.length(), resultLen);
        }

        return joinedStr.toString();
    }

    /**
     * Acts like Python's join
     *
     * @param aSeparator
     *            Items separator
     * @param aItems
     *            Items to join
     * @return The joined string, or an empty one
     */
    private String join(final String aSeparator, final Object... aItems) {

        return join(aSeparator, Arrays.asList(aItems));
    }

    /**
     * Prepares the {@link SSLContext} object to use in the XMPP connection, to
     * trust any certificate
     *
     * See
     * http://stackoverflow.com/questions/19723415/java-overriding-function-to
     * -disable-ssl-certificate-check
     *
     * @return An SSL context
     * @throws NoSuchAlgorithmException
     *             Can't create the SSLContext
     * @throws KeyManagementException
     *             Error initializing the SSLContext
     */
    private SSLContext makeSSLContext() throws NoSuchAlgorithmException,
            KeyManagementException {

        // Create a TLS context
        final SSLContext sc = SSLContext.getInstance("TLS");

        // Set our custom trust manager
        sc.init(null, new TrustManager[] { new TrustAllX509TrustManager() },
                new java.security.SecureRandom());

        return sc;
    }

    /**
     * Sends a packet using the active session
     *
     * @param aElement
     *            The element to send
     */
    public void send(final ClientStreamElement aElement) {

        pSession.send(aElement);
    }

    /**
     * Prepares and sends a message over XMPP. The content is sent as a string,
     * without serialization
     *
     * @param aMsgType
     *            Kind of message (chat or groupchat)
     * @param aTarget
     *            Target JID or MUC room
     * @param aMessage
     *            Herald message bean
     */
    private void sendMessage(final Type aMsgType, final String aTarget,
            final org.cohorte.herald.Message aMessage) {

        // Parse the target JID
        final Jid target = Jid.valueOf(aTarget);

        // Prepare the message
        final Message msg = new Message(target, aMsgType);
        msg.setFrom(getJid());
        msg.setBody(String.valueOf(aMessage.getContent()));
        msg.setSubject(aMessage.getSubject());
        msg.setThread(aMessage.getUid());

        // Send it
        pSession.send(msg);
    }

    /*
     * (non-Javadoc)
     * 
     * @see
     * rocks.xmpp.core.session.SessionStatusListener#sessionStatusChanged(rocks
     * .xmpp.core.session.SessionStatusEvent)
     */
    @Override
    public void sessionStatusChanged(final SessionStatusEvent aEvent) {

        switch (aEvent.getStatus()) {
        case AUTHENTICATED:
            // Session started
            pListener.onSessionStart(pSession);
            break;

        case CLOSING:
            // Session ended
            pListener.onSessionEnd(pSession);
            break;

        default:
            // Ignore other states
            break;
        }
    }
}
