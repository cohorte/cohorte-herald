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

/**
 * Specification of the non-service methods Herald core must implement
 *
 * @author Thomas Calmant
 */
public interface IHeraldInternal {

    /**
     * Handles a message received from a transport implementation.
     *
     * Unlocks/calls back the senders of the message this one responds to.
     *
     * @param aMessage
     *            A {@link MessageReceived} bean forged by a transport
     */
    void handleMessage(MessageReceived aMessage);

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
     * @throws HeraldException
     *             Error sending the reply
     */
    void reply(MessageReceived aMessage, Object aContent, String aSubject)
            throws HeraldException;
}
