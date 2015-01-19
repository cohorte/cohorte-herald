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

import javax.net.ssl.SSLContext;
import javax.net.ssl.TrustManager;
import javax.security.auth.login.LoginException;

import org.osgi.service.log.LogService;

import rocks.xmpp.core.Jid;
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

/**
 * The XMPP bot implementation, based on Babbler
 *
 * @author Thomas Calmant
 */
public class Bot implements SessionStatusListener, MessageListener {

    /** The listener */
    private final IBotListener pListener;

    /** The log service */
    private final LogService pLogger;

    /** The nick used in MultiUserChat rooms */
    private final String pNickName;

    /** The XMPP session */
    private XmppSession pSession;

    /**
     * Sets up the bot
     *
     * @param aListener
     *            The event listener
     * @param aLogger
     *            The log service to use
     * @param aNickName
     *            The nickname used in MultiUserChat rooms
     */
    public Bot(final IBotListener aListener, final LogService aLogger,
            final String aNickName) {

        pListener = aListener;
        pLogger = aLogger;
        pNickName = aNickName;
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

        // Register to events
        pSession.addSessionStatusListener(this);
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

    /**
     * Returns the internal Babbler {@link XmppSession}
     *
     * @return The XMPP session
     */
    public XmppSession getSession() {

        return pSession;
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
