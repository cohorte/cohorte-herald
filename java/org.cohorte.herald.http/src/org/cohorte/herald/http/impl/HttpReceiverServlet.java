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

package org.cohorte.herald.http.impl;

import java.io.IOException;
import java.util.Map;

import javax.servlet.ServletException;
import javax.servlet.http.HttpServlet;
import javax.servlet.http.HttpServletRequest;
import javax.servlet.http.HttpServletResponse;

import org.cohorte.herald.Message;
import org.cohorte.herald.MessageReceived;
import org.cohorte.herald.ValueError;
import org.cohorte.herald.core.utils.MessageUtils;
import org.cohorte.herald.http.HTTPExtra;
import org.cohorte.herald.http.IHttpConstants;
import org.jabsorb.ng.serializer.MarshallException;
import org.jabsorb.ng.serializer.UnmarshallException;
import org.osgi.service.log.LogService;

/**
 * The Herald HTTP reception servlet
 *
 * @author Thomas Calmant
 */
public class HttpReceiverServlet extends HttpServlet {

    /** Serial version UID */
    private static final long serialVersionUID = 1L;

    /** The parent HTTP receiver service */
    private final HttpReceiver pReceiver;

    /**
     * Sets up members
     *
     * @param aHttpReceiver
     *            The parent HTTP receiver service
     */
    public HttpReceiverServlet(final HttpReceiver aHttpReceiver) {

        pReceiver = aHttpReceiver;
    }

    /*
     * (non-Javadoc)
     * 
     * @see
     * javax.servlet.http.HttpServlet#doGet(javax.servlet.http.HttpServletRequest
     * , javax.servlet.http.HttpServletResponse)
     */
    @Override
    protected void doGet(final HttpServletRequest aReq,
            final HttpServletResponse aResp) throws ServletException,
            IOException {

        final Map<String, Object> peerDump = pReceiver.getLocalPeer().dump();
        int status;
        String strData;
        try {
            strData = pReceiver.serialize(peerDump);
            status = HttpServletResponse.SC_OK;

        } catch (final MarshallException ex) {
            pReceiver.log(LogService.LOG_DEBUG, "Error converting peer dump: "
                    + ex, ex);
            strData = "Error converting Peer dump: " + ex;
            status = HttpServletResponse.SC_INTERNAL_SERVER_ERROR;
        }

        // Convert the String to bytes
        final byte[] data = strData.getBytes(IHttpConstants.CHARSET_UTF8);

        // Set headers
        aResp.setStatus(status);
        aResp.setCharacterEncoding(IHttpConstants.CHARSET_UTF8);
        aResp.setContentType(IHttpConstants.CONTENT_TYPE_JSON);
        aResp.setContentLength(data.length);

        // Send reply
        aResp.getOutputStream().write(data);
        aResp.getOutputStream().flush();
    }

    /*
     * (non-Javadoc)
     * 
     * @see
     * javax.servlet.http.HttpServlet#doPost(javax.servlet.http.HttpServletRequest
     * , javax.servlet.http.HttpServletResponse)
     */
    @Override
    protected void doPost(final HttpServletRequest aReq,
            final HttpServletResponse aResp) throws ServletException,
            IOException {
    	try {
	        final String contentType = aReq.getContentType();
	        if (contentType != null
	                && !IHttpConstants.CONTENT_TYPE_JSON
	                        .equalsIgnoreCase(contentType)) {
	            pReceiver.log(LogService.LOG_WARNING, "Bad content type: "
	                    + contentType);
	            aResp.sendError(HttpServletResponse.SC_PRECONDITION_FAILED,
	                    "Unhandled content type");
	            return;
	        }
	
	        // Parse the content
	        final byte[] rawData = pReceiver.inputStreamToBytes(aReq
	                .getInputStream());
	
	        String charsetName = aReq.getCharacterEncoding();
	        if (charsetName == null) {
	            charsetName = IHttpConstants.CHARSET_UTF8;
	        }
	        final String strData = new String(rawData, charsetName);
	        
	        try {
	            
	        	final MessageReceived rcv_msg;
	        	//final Object content;
	        	if(!strData.isEmpty())
	        	{	
	        		rcv_msg = MessageUtils.fromJSON(strData);
	        		if (rcv_msg != null) {
	        			// content = rcv_msg.getContent();
	        		//else {
	        			//content = null;	        			
	        		}
	        	} else {
	        		rcv_msg = null;
	        		//content = null;
	        	}	        	        	
	        	
	        	// Extract headers
		        //String subject = null;
		        String msgUid = null;
		        //String replyTo = null;
		        String senderUid = null;
		        String senderPath = null;
		        //Long timestamp = null;
		
		        HTTPExtra extra = null; 
		        
		        if (rcv_msg != null) {
		        	//subject = rcv_msg.getSubject();
			        msgUid = rcv_msg.getUid();
			        //replyTo = rcv_msg.getReplyTo();
			        senderUid = rcv_msg.getSender();
			        Object wPath = rcv_msg.getHeader(IHttpConstants.MESSAGE_HEADER_PATH);
			        senderPath = (wPath != null) ? wPath.toString() : null;
			        //timestamp = rcv_msg.getTimestamp();		        
			
			        // Get sender port
			        int port;
			        try {
			        	Object wPort = rcv_msg.getHeader(IHttpConstants.MESSAGE_HEADER_PORT);
			            port = (wPort != null) ? new Integer(wPort.toString()).intValue() : 80;
			        } catch (final NumberFormatException ex) {
			            port = 80;
			        }
			
			        // Store sender information
			        final String host = aReq.getRemoteAddr();
			        extra = new HTTPExtra(host, port, senderPath, msgUid);
			
			        try {
			            // Check sender access
			            if (!pReceiver.checkAccess(senderUid, host, port)) {
			                // Check failed: invalid UID
			                senderUid = "<invalid>";
			            }
			        } catch (final ValueError ex) {
			            // Unknown peer: keep the sender UID as is
			        }	
			        
			        rcv_msg.addHeader(Message.MESSAGE_HEADER_SENDER_UID, senderUid);
			        rcv_msg.setAccess(IHttpConstants.ACCESS_ID);
			        rcv_msg.setExtra(extra);
		        }	        	
	
	            // Let Herald handle the message
	            pReceiver.handleMessage(rcv_msg);
	
	            // Send response
	            aResp.setStatus(HttpServletResponse.SC_OK);
	            aResp.setContentLength(0);
	
	        } catch (final UnmarshallException ex) {
	            // Error parsing the message
	            pReceiver.log(LogService.LOG_ERROR,
	                    "Error parsing message content: " + ex, ex);
	
	            // Send the error
	            aResp.sendError(HttpServletResponse.SC_INTERNAL_SERVER_ERROR,
	                    "Error parsing message content: " + ex);
	        }
    	} catch(Throwable ex)
        {
            pReceiver.log(LogService.LOG_ERROR, "Error on do_Post : "
                    + ex, ex);
        }
    }
}
