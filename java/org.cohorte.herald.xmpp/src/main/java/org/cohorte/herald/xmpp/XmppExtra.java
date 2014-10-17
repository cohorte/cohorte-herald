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

import org.xmpp.Jid;

/**
 * XMPP access extra information
 *
 * @author Thomas Calmant
 */
public class XmppExtra {

    /** UID of the message to reply to */
    private final String pParentUid;

    /** JID of the sender to reply to */
    private final Jid pSenderJid;

    /**
     * Sets up the XMPP message extra information
     *
     * @param aSenderJid
     *            JID of the sender of the message
     * @param aMessageUid
     *            UID of the message
     */
    public XmppExtra(final Jid aSenderJid, final String aMessageUid) {

        pParentUid = aMessageUid;
        pSenderJid = aSenderJid;
    }

    /**
     * @return the parentUid
     */
    public String getParentUid() {

        return pParentUid;
    }

    /**
     * @return the senderJid
     */
    public Jid getSenderJid() {

        return pSenderJid;
    }
}
