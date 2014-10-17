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

package org.cohorte.herald.xmpp;

import org.cohorte.herald.Peer;
import org.cohorte.herald.UnknownPeer;
import org.xmpp.Jid;

/**
 * Specification of the XMPP transport directory
 *
 * @author Thomas Calmant
 */
public interface IXmppDirectory {

    /**
     * Returns the peer associated to the given JID
     *
     * @param aJid
     *            The (full) JID of a peer
     * @return A peer bean
     * @throws UnknownPeer
     *             Unknown peer
     */
    Peer fromJID(Jid aJid) throws UnknownPeer;
}
