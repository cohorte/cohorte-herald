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
 * Represents a message received by a transport
 *
 * @author Thomas Calmant
 */
public class MessageReceived extends Message {

    /** The access ID of the transport which received this message */
    private String pAccess;

    /** Extra configuration for the transport in case of reply */
    private Object pExtra;


    /**
     * Sets up the received message bean
     *
     * @param aUid
     *            Message UID
     * @param aSubject
     *            Subject of the message
     * @param aContent
     *            Content of the message
     * @param aSenderUid
     *            UID of the sending peer
     * @param aReplyTo
     *            UID of the message this one replies to
     * @param aAccessId
     *            Access ID of the transport which received this message
     * @param aTimestamp
     *            Message creation time stamp
     * @param aExtra
     *            Extra configuration for the transport in case of reply
     */
    public MessageReceived(final String aUid, final String aSubject,
            final Object aContent, final String aSenderUid,
            final String aReplyTo, final String aAccessId,
            final Long aTimestamp, final Object aExtra) {

        super(aSubject, aContent, aUid, aTimestamp);
        pHeaders.put(Message.MESSAGE_HEADER_SENDER_UID, aSenderUid);
        pHeaders.put(Message.MESSAGE_HEADER_REPLIES_TO, aReplyTo);
        pAccess = aAccessId;
        pExtra = aExtra;
    }

    /**
     * Sets up the received message bean
     *
     * @param aUid
     *            Message UID
     * @param aSubject
     *            Subject of the message
     * @param aContent
     *            Content of the message
     * @param aSenderUid
     *            UID of the sending peer
     * @param aReplyTo
     *            UID of the message this one replies to
     * @param aAccessId
     *            Access ID of the transport which received this message
     * @param aExtra
     *            Extra configuration for the transport in case of reply
     */
    public MessageReceived(final String aUid, final String aSubject,
            final Object aContent, final String aSenderUid,
            final String aReplyTo, final String aAccessId, final Object aExtra) {

        this(aUid, aSubject, aContent, aSenderUid, aReplyTo, aAccessId, null,
                aExtra);
    }

    /**
     * @return the access
     */
    public String getAccess() {
    	return pAccess;
    }

    /**
     * Sets the Access.
     * @param aAccess
     */
    public void setAccess(String aAccess) {
    	pAccess = aAccess;
    }
    
    /**
     * @return the extra configuration
     */
    public Object getExtra() {

        return pExtra;
    }
    
    /**
     * Sets the extra
     * @param aExtra
     */
    public void setExtra(Object aExtra) {
    	pExtra = aExtra;
    }
    
    /**
     * @return the replyTo
     */
    public String getReplyTo() {
    	Object repliesTo = pHeaders.get(Message.MESSAGE_HEADER_REPLIES_TO);
        return (repliesTo != null ? repliesTo.toString() : null);
    }

    /**
     * @return the sender
     */
    public String getSender() {
    	Object sender = pHeaders.get(Message.MESSAGE_HEADER_SENDER_UID);
        return (sender != null) ? sender.toString() : null;
    }
    
	
    
    
    /*
     * (non-Javadoc)
     * 
     * @see org.cohorte.herald.Message#toString()
     */
    @Override
    public String toString() {

        return "" + getSubject() + "(" + getUid() + ") from " + getSender();
    }
}
