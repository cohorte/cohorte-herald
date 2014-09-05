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

package org.cohorte.herald.core;

import org.cohorte.herald.IHerald;
import org.cohorte.herald.IPostCallback;
import org.cohorte.herald.IPostErrback;
import org.cohorte.herald.MessageReceived;
import org.cohorte.herald.exceptions.HeraldException;

/**
 * A bean that describes parameters of a post() call
 *
 * @author Thomas Calmant
 */
public class WaitingPost {

    /** Object to call back when an answer is received */
    private final IPostCallback pCallback;

    /** Message deadline */
    private Long pDeadline;

    /** Object to call back on error */
    private final IPostErrback pErrback;

    /** Flag to forget message on first answer */
    private final boolean pForgetOnFirst;

    /**
     * Sets up members
     *
     * @param aCallback
     *            Object to call back when an answer is received
     * @param aErrback
     *            Object to call back on error
     * @param aTimeout
     *            Time to wait before forgetting this post, in milliseconds
     * @param aForgetOnFirst
     *            Flag to forget message on first answer
     */
    public WaitingPost(final IPostCallback aCallback,
            final IPostErrback aErrback, final Long aTimeout,
            final boolean aForgetOnFirst) {

        pCallback = aCallback;
        pErrback = aErrback;
        pForgetOnFirst = aForgetOnFirst;

        if (aTimeout != null) {
            pDeadline = System.currentTimeMillis() + aTimeout;
        }
    }

    /**
     * Tries to call the callback of the post message.
     *
     * @param aHerald
     *            Herald service instance
     * @param aMessage
     *            Received answer message
     */
    public void callback(final IHerald aHerald, final MessageReceived aMessage) {

        if (pCallback != null) {
            pCallback.heraldCallback(aHerald, aMessage);
        }
    }

    /**
     * Tries to call the error callback of the post message.
     *
     * @param aHerald
     *            Herald service instance
     * @param aException
     *            The exception associated to the error
     */
    public void errback(final IHerald aHerald, final HeraldException aException) {

        if (pErrback != null) {
            pErrback.heraldErrback(aHerald, aException);
        }
    }

    /**
     * Checks if the deadline has been reached
     *
     * @return True if this message can be forgotten
     */
    public boolean isDead() {

        if (pDeadline != null) {
            return pDeadline > System.currentTimeMillis();
        }
        return false;
    }

    /**
     * Flag to determine if this post must be forgotten after its first reply
     *
     * @return the flag value
     */
    public boolean isForgetOnFirst() {

        return pForgetOnFirst;
    }
}
