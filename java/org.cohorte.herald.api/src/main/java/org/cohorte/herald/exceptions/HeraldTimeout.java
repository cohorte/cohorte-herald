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

package org.cohorte.herald.exceptions;

import org.cohorte.herald.Message;
import org.cohorte.herald.Target;

/**
 * A timeout has been reached
 *
 * @author Thomas Calmant
 */
public class HeraldTimeout extends HeraldException {

    /** Serialization version UID */
    private static final long serialVersionUID = 1L;

    /** The request which got no reply */
    private final Message pMessage;

    /**
     * Sets up the exception
     *
     * @param aTarget
     *            Targeted peer(s)
     * @param aText
     *            Description of the error
     * @param aMessage
     *            The request which got no reply
     */
    public HeraldTimeout(final Target aTarget, final String aText,
            final Message aMessage) {

        super(aTarget, aText);
        pMessage = aMessage;
    }

    /**
     * @return The request which got no reply
     */
    public Message getRequestedMessage() {

        return pMessage;
    }
}
