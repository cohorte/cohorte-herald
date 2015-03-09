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

package org.cohorte.herald.rpc;

import java.util.Map;

import org.cohorte.herald.HeraldException;
import org.cohorte.herald.IHerald;
import org.cohorte.herald.Message;
import org.jabsorb.ng.client.ClientError;
import org.jabsorb.ng.client.ISession;
import org.json.JSONObject;

/**
 * The Herald Client session implementation for Jabsorb
 *
 * @author Thomas Calmant
 */
public class ClientSession implements ISession {

    /** The Herald core service */
    private IHerald pHerald;

    /** The targeted Peer UID */
    private String pPeerUid;

    /** The request message subject */
    private String pSubject;

    /**
     * Sets up members
     *
     * @param aHerald
     *            The Herald core service
     */
    public ClientSession(final IHerald aHerald, final String aPeerUid,
            final String aSubject) {

        pHerald = aHerald;
        pPeerUid = aPeerUid;
        pSubject = aSubject;
    }

    /*
     * (non-Javadoc)
     * 
     * @see org.jabsorb.ng.client.ISession#close()
     */
    @Override
    public void close() {

        // Clean up
        pHerald = null;
        pPeerUid = null;
        pSubject = null;
    }

    /*
     * (non-Javadoc)
     * 
     * @see org.jabsorb.ng.client.ISession#sendAndReceive(org.json.JSONObject)
     */
    @Override
    public JSONObject sendAndReceive(final JSONObject aMessage) {

        Object result;
        try {
            // Send the request as a string
            result = pHerald
                    .send(pPeerUid,
                            new Message(pSubject, JSONObject.quote(aMessage
                                    .toString())));

        } catch (final HeraldException ex) {
            // Error sending the message
            throw new ClientError("Error sending RPC request: " + ex, ex);
        }

        if (result instanceof String) {
            try {
                return new JSONObject((String) result);
            } catch(org.json.JSONException e) {
                throw new ClientError("Cannot create a JSONObject from the String : " + result);
            }
        }

        // The reply has already been converted to a map
        else if (!(result instanceof Map)) {
            // Bad result
            throw new ClientError("Bad result content: not a map > " + result.toString() + " -- type=" + result.getClass());
        }

        return new JSONObject((Map<?, ?>) result);
    }
}
