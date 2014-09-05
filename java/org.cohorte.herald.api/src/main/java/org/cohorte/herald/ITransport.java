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

import org.cohorte.herald.exceptions.HeraldException;

/**
 * Specification of a transport implementation service
 *
 * @author Thomas Calmant
 */
public interface ITransport {

    /**
     * Fires a message to a peer
     *
     * @param aPeer
     *            The peer to send the message to
     * @param aMessage
     *            Message to send
     * @throws HeraldException
     *             Error sending the request or error on the server side
     */
    void fire(Peer aPeer, Message aMessage) throws HeraldException;

    /**
     * Fires a message to a peer
     *
     * @param aPeer
     *            The peer to send the message to
     * @param aMessage
     *            Message to send
     * @param aExtra
     *            Extra information used in case of a reply
     * @throws HeraldException
     *             Error sending the request or error on the server side
     */
    void fire(Peer aPeer, Message aMessage, Object aExtra)
            throws HeraldException;

    /**
     * Fires a message to a group of peers
     *
     * @param aGroup
     *            Name of a group
     * @param aPeers
     *            Peers to communicate with
     * @param aMessage
     *            Message to send
     * @return The list of reached peers (if available), never null
     */
    Collection<Peer> fireGroup(String aGroup, Collection<Peer> aPeers,
            Message aMessage);
}
