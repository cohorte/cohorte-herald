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

import java.util.HashMap;
import java.util.Map;
import java.util.UUID;

/**
 * Represents a message to be sent
 *
 * @author Thomas Calmant
 */
public class Message {
	
	public static final int HERALD_SPECIFICATION_VERSION = 1;
	
	public static final String MESSAGE_HERALD_VERSION = "herald-version";
	public static final String MESSAGE_HEADERS = "headers";
    public static final String MESSAGE_HEADER_UID = "uid";
    public static final String MESSAGE_HEADER_TIMESTAMP = "timestamp";
	public static final String MESSAGE_HEADER_SENDER_UID = "sender-uid";
	public static final String MESSAGE_HEADER_TARGET_PEER = "target-peer";
	public static final String MESSAGE_HEADER_TARGET_GROUP = "target-group";
	public static final String MESSAGE_HEADER_REPLIES_TO = "replies-to";
	public static final String MESSAGE_SUBJECT = "subject";
	public static final String MESSAGE_CONTENT = "content";
	public static final String MESSAGE_METADATA = "metadata";
	
	/** Headers **/
	protected final Map<String, Object> pHeaders;
	
    /** Content of the message */
    private Object pContent;

    /** Subject of the message */
    private final String pSubject;

    /** Message metadata **/
    private final Map<String, Object> pMetadata;

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
    	pHeaders = new HashMap<String, Object>();
        pSubject = aSubject;
        pContent = aContent;
        pHeaders.put(MESSAGE_HERALD_VERSION, HERALD_SPECIFICATION_VERSION);
        pHeaders.put(MESSAGE_HEADER_UID, aUid.replace("-", "").toUpperCase());
        pHeaders.put(MESSAGE_HEADER_TIMESTAMP, aTimestamp);
        pMetadata = new HashMap<String, Object>();
    }

    /**
     * @return the content
     */
    public Object getContent() {

        return pContent;
    }

    /**
     * Sets the message content.
     * @param aContent new content
     */
	public void setContent(Object aContent) {
		pContent = aContent;
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
    	Object timestamp = pHeaders.get(MESSAGE_HEADER_TIMESTAMP);
        return (timestamp != null ? new Long(timestamp.toString()) : null);
    }

    /**
     * @return the uid
     */
    public String getUid() {
    	Object uid = pHeaders.get(MESSAGE_HEADER_UID);
        return (uid != null ? uid.toString() : null);
    }   
	
	/**
	 * Gets the list of message headers
	 * @return
	 */
	public Map<String, Object> getHeaders() {
		return pHeaders;
	}
	
	/**
	 * Adding a header.
	 * If key already exists, its value will be updated!.
	 * 
	 * @param key
	 * @param value
	 */
	public void addHeader(String key, Object value) {
		pHeaders.put(key, value);
	}
	
	/**
	 * Gets a header value.
	 * 
	 * @param key
	 * @return
	 */
	public Object getHeader(String key) {		
		return pHeaders.get(key);
	}
	
	/**
	 * Gets the list of metadata associated to this message
	 * @return Dictionary of metadata
	 */
	public Map<String, Object> getMetadata() {
		return pMetadata;
	}
	
	/**
	 * Adding a metadata.
	 * If key already exists, its value will be updated!.
	 * 
	 * @param key
	 * @param value
	 */
	public void addMetadata(String key, Object value) {
		pMetadata.put(key, value);
	}
	
	/**
	 * Gets a metadata value.
	 * 
	 * @param key
	 * @return
	 */
	public Object getMetadata(String key) {		
		return pMetadata.get(key);
	}
	
    /*
     * (non-Javadoc)
     * 
     * @see java.lang.Object#toString()
     */
    @Override
    public String toString() {

        return "" + pSubject + " (" + getUid() + ")";
    }
}
