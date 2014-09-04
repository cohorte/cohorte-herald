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

import org.cohorte.herald.exceptions.HeraldTimeout;
import org.cohorte.herald.exceptions.NoListener;
import org.cohorte.herald.exceptions.NoTransport;
import org.cohorte.herald.exceptions.UnknownPeer;

/**
 * Specification of the Herald core services
 *
 * @author Thomas Calmant
 */
public interface IHerald {

    /**
     * Fires (and forget) a message to the given peer
     *
     * @param aPeer
     *            The peer to send the message to
     * @param aMessage
     *            The message to send
     * @return The UID of the message
     * @throws NoTransport
     *             No transport found to send the message
     */
    String fire(Peer aPeer, Message aMessage) throws NoTransport;

    /**
     * Fires (and forget) a message to the given peer
     *
     * @param aPeerUid
     *            The UID of the peer to send the message to
     * @param aMessage
     *            The message to send
     * @return The UID of the message
     * @throws NoTransport
     *             No transport found to send the message
     * @throws UnknownPeer
     *             Unknown peer UID
     */
    String fire(String aPeerUid, Message aMessage) throws NoTransport,
            UnknownPeer;

    /**
     * Fires (and forget) the given message to the given group of peers
     *
     * @param aGroupName
     *            The name of a group of peers
     * @param aMessage
     *            The message to send
     * @return The list of peers the message has been sent to
     * @throws NoTransport
     *             No transport found to send the message
     */
    Collection<Peer> fireGroup(String aGroupName, Message aMessage)
            throws NoTransport;

    /**
     * Tells Herald to forget informations about the given message UIDs.
     *
     * This can be used to clean up references to a component being invalidated.
     *
     * @param aMessageUid
     *            The UID of the message to forget
     * @return True if there was a reference about this message
     */
    boolean forget(final String aMessageUid);

    /**
     * Posts a message. The given methods will be called back as soon as a
     * result is given, or in case of error
     *
     * @param aPeer
     *            The peer to send the message to
     * @param aMessage
     *            The message to send
     * @param aCallback
     *            Object to call back when a reply is received
     * @param aErrback
     *            Object to call back when an error occurs
     * @return The UID of the message
     * @throws NoTransport
     *             No transport found to send the message
     */
    String post(Peer aPeer, Message aMessage, IPostCallback aCallback,
            IPostErrback aErrback) throws NoTransport;

    /**
     * Posts a message. The given methods will be called back as soon as a
     * result is given, or in case of error
     *
     * @param aPeer
     *            The peer to send the message to
     * @param aMessage
     *            The message to send
     * @param aCallback
     *            Object to call back when a reply is received
     * @param aErrback
     *            Object to call back when an error occurs
     * @param aTimeout
     *            Time after which the message will be forgotten
     * @return The UID of the message
     * @throws NoTransport
     *             No transport found to send the message
     */
    String post(Peer aPeer, Message aMessage, IPostCallback aCallback,
            IPostErrback aErrback, Long aTimeout) throws NoTransport;

    /**
     * Posts a message. The given methods will be called back as soon as a
     * result is given, or in case of error
     *
     * @param aPeer
     *            The peer to send the message to
     * @param aMessage
     *            The message to send
     * @param aCallback
     *            Object to call back when a reply is received
     * @param aErrback
     *            Object to call back when an error occurs
     * @param aTimeout
     *            Time after which the message will be forgotten
     * @param aForgetOnFirst
     *            Forget the message after the first answer
     * @return The UID of the message
     * @throws NoTransport
     *             No transport found to send the message
     */
    String post(Peer aPeer, Message aMessage, IPostCallback aCallback,
            IPostErrback aErrback, Long aTimeout, boolean aForgetOnFirst)
            throws NoTransport;

    /**
     * Posts a message. The given methods will be called back as soon as a
     * result is given, or in case of error
     *
     * @param aPeerUid
     *            The UID of the peer to send the message to
     * @param aMessage
     *            The message to send
     * @param aCallback
     *            Object to call back when a reply is received
     * @param aErrback
     *            Object to call back when an error occurs
     * @return The UID of the message
     * @throws NoTransport
     *             No transport found to send the message
     */
    String post(String aPeerUid, Message aMessage, IPostCallback aCallback,
            IPostErrback aErrback) throws UnknownPeer, NoTransport;

    /**
     * Posts a message. The given methods will be called back as soon as a
     * result is given, or in case of error
     *
     * @param aPeerUid
     *            The UID of the peer to send the message to
     * @param aMessage
     *            The message to send
     * @param aCallback
     *            Object to call back when a reply is received
     * @param aErrback
     *            Object to call back when an error occurs
     * @param aTimeout
     *            Time after which the message will be forgotten
     * @return The UID of the message
     * @throws NoTransport
     *             No transport found to send the message
     */
    String post(String aPeerUid, Message aMessage, IPostCallback aCallback,
            IPostErrback aErrback, Long aTimeout) throws UnknownPeer,
            NoTransport;

    /**
     * Posts a message. The given methods will be called back as soon as a
     * result is given, or in case of error
     *
     * @param aPeerUid
     *            The UID of the peer to send the message to
     * @param aMessage
     *            The message to send
     * @param aCallback
     *            Object to call back when a reply is received
     * @param aErrback
     *            Object to call back when an error occurs
     * @param aTimeout
     *            Time after which the message will be forgotten
     * @param aForgetOnFirst
     *            Forget the message after the first answer
     * @return The UID of the message
     * @throws NoTransport
     *             No transport found to send the message
     */
    String post(String aPeerUid, Message aMessage, IPostCallback aCallback,
            IPostErrback aErrback, Long aTimeout, boolean aForgetOnFirst)
            throws UnknownPeer, NoTransport;

    /**
     * Replies to a message. The subject will be the one of the original
     * message, prefixed with "reply/"
     *
     * @param aMessage
     *            Message to reply to
     * @param aContent
     *            Content of the response
     */
    void reply(MessageReceived aMessage, Object aContent);

    /**
     * Replies to a message. If no subject is given, it will be the one of the
     * original message, prefixed with "reply/"
     *
     * @param aMessage
     *            Message to reply to
     * @param aContent
     *            Content of the response
     * @param aSubject
     *            Subject of the response message
     */
    void reply(MessageReceived aMessage, Object aContent, String aSubject);

    /**
     * Sends a message, and waits for its reply
     *
     * @param aPeer
     *            The peer to send the message to
     * @param aMessage
     *            The message to send
     * @return The UID of the message
     * @throws NoTransport
     *             No transport found to send the message
     * @throws NoListener
     *             Message received, but nobody was registered to listen to it
     */
    MessageReceived send(Peer aPeer, Message aMessage) throws NoTransport,
            NoListener;

    /**
     * Sends a message, and waits for its reply
     *
     * @param aPeer
     *            The peer to send the message to
     * @param aMessage
     *            The message to send
     * @param aTimeout
     *            Maximum time to wait for an answer
     * @return The UID of the message
     * @throws NoTransport
     *             No transport found to send the message
     * @throws NoListener
     *             Message received, but nobody was registered to listen to it
     * @throws HeraldTimeout
     *             Timeout raised before getting an answer
     */
    MessageReceived send(Peer aPeer, Message aMessage, Long aTimeout)
            throws NoTransport, NoListener, HeraldTimeout;

    /**
     * Sends a message, and waits for its reply
     *
     * @param aPeerUid
     *            The UID of the peer to send the message to
     * @param aMessage
     *            The message to send
     * @return The UID of the message
     * @throws NoTransport
     *             No transport found to send the message
     * @throws NoListener
     *             Message received, but nobody was registered to listen to it
     * @throws UnknownPeer
     *             Unknown peer UID
     */
    MessageReceived send(String aPeerUid, Message aMessage) throws UnknownPeer,
            NoTransport, NoListener;

    /**
     * Sends a message, and waits for its reply
     *
     * @param aPeerUid
     *            The UID of the peer to send the message to
     * @param aMessage
     *            The message to send
     * @param aTimeout
     *            Maximum time to wait for an answer
     * @return The UID of the message
     * @throws NoTransport
     *             No transport found to send the message
     * @throws NoListener
     *             Message received, but nobody was registered to listen to it
     * @throws HeraldTimeout
     *             Timeout raised before getting an answer
     * @throws UnknownPeer
     *             Unknown peer UID
     */
    MessageReceived send(String aPeerUid, Message aMessage, Long aTimeout)
            throws UnknownPeer, NoTransport, NoListener, HeraldTimeout;
}
