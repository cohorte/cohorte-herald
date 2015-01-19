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

import java.util.UUID;

/**
 * Represents a message to be sent
 *
 * @author Thomas Calmant
 */
public class Message {

    /** Content of the message */
    private final Object pContent;

    /** Subject of the message */
    private final String pSubject;

    /** Time stamp of the message (date of creation) */
    private final Long pTimestamp;

    /** Message UID */
    private final String pUid;

    /**
     * Sets up a message without content
     *
     * @param aSubject
     *            Subject of the message
     */
    public Message(final String aSubject) {

        this(aSubject, null);
    }

    /**
     * Sets up the message to be sent
     *
     * @param aSubject
     *            Subject of the message
     * @param aContent
     *            Content of the message
     */
    public Message(final String aSubject, final Object aContent) {

        this(aSubject, aContent, UUID.randomUUID().toString(), System
                .currentTimeMillis());
    }

    /**
     * Internal setup of the message bean
     *
     * @param aSubject
     *            Subject of the message
     * @param aContent
     *            Content of the message
     * @param aUid
     *            UID of the message
     * @param aTimestamp
     *            Time stamp of the message
     */
    protected Message(final String aSubject, final Object aContent,
            final String aUid, final Long aTimestamp) {

        pSubject = aSubject;
        pContent = aContent;
        pUid = aUid.replace("-", "").toUpperCase();
        pTimestamp = aTimestamp;
    }

    /**
     * @return the content
     */
    public Object getContent() {

        return pContent;
    }

    /**
     * @return the subject
     */
    public String getSubject() {

        return pSubject;
    }

    /**
     * @return the time stamp (can be null)
     */
    public Long getTimestamp() {

        return pTimestamp;
    }

    /**
     * @return the uid
     */
    public String getUid() {

        return pUid;
    }

    /*
     * (non-Javadoc)
     * 
     * @see java.lang.Object#toString()
     */
    @Override
    public String toString() {

        return "" + pSubject + " (" + pUid + ")";
    }
}
