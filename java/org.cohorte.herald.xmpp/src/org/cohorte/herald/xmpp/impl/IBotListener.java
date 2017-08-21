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

import rocks.xmpp.core.session.XmppSession;
import rocks.xmpp.core.stanza.model.client.Message;

/**
 * Specification of a bot listener
 *
 * @author Thomas Calmant
 */
public interface IBotListener {

    /**
     * An XMPP message has been received
     *
     * @param aMessage
     *            The received message
     */
    void onMessage(Message aMessage);

    /**
     * The XMPP session has ended
     *
     * @param aSession
     *            The XMPP session
     */
    void onSessionEnd(XmppSession aSession);

    /**
     * The XMPP session has started, client is authenticated
     *
     * @param aSession
     *            The XMPP session
     */
    void onSessionStart(XmppSession aSession);
}
