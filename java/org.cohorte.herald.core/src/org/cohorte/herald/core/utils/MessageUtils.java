package org.cohorte.herald.core.utils;

import java.util.Iterator;

import org.cohorte.herald.Message;
import org.cohorte.herald.MessageReceived;
import org.jabsorb.ng.JSONSerializer;
import org.jabsorb.ng.serializer.MarshallException;
import org.jabsorb.ng.serializer.UnmarshallException;
import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;


public class MessageUtils {
	
	/** The Jabsorb serializer */
	private static JSONSerializer pSerializer = new JSONSerializer();
	
	static {
		try {
			pSerializer.registerDefaultSerializers();
		} catch (Exception e) {
			// TODO Auto-generated catch block
			e.printStackTrace();
		}
	}
	
	public static String toJSON(Message aMsg) throws MarshallException {
		JSONObject json = new JSONObject();
		try {						
			// headers
			JSONObject headers = new JSONObject();
			for (String key : aMsg.getHeaders().keySet()) {
				headers.put(key, aMsg.getHeaders().get(key));
			}					
			json.put(Message.MESSAGE_HEADERS, headers);
			// subject
			json.put(Message.MESSAGE_SUBJECT, aMsg.getSubject());
			// content
			if (aMsg.getContent() != null) {
				if (aMsg.getContent() instanceof String) {
					json.put(Message.MESSAGE_CONTENT, aMsg.getContent());
				} else {
					JSONObject content = new JSONObject(pSerializer.toJSON(aMsg.getContent()));
					json.put(Message.MESSAGE_CONTENT, content);
				}
			}
			// metadata
			JSONObject metadata = new JSONObject();
			for (String key : aMsg.getMetadata().keySet()) {
				metadata.put(key, aMsg.getMetadata().get(key));
			}			
			json.put(Message.MESSAGE_METADATA, metadata);
			
		} catch (JSONException e) {			
			e.printStackTrace();
			return null;
		}
		
		return json.toString();
	}
	
	@SuppressWarnings("unchecked")
	public static MessageReceived fromJSON(String json) throws UnmarshallException {
		 try {
	    	JSONObject wParsedMsg = new JSONObject(json);	    	
	    	{
	    		try {
	    			// check if valid herald message (respects herald specification version)
	    			int heraldVersion = -1;
	    			JSONObject jHeader = wParsedMsg.getJSONObject(Message.MESSAGE_HEADERS); 
	    			if (jHeader != null) {
	    				if (jHeader.has(Message.MESSAGE_HERALD_VERSION)) {
	    					heraldVersion = jHeader.getInt(Message.MESSAGE_HERALD_VERSION);
	    				}
	    			}	    			
	    			if (heraldVersion != Message.HERALD_SPECIFICATION_VERSION) {
	    				throw new JSONException("Herald specification of the received message is not supported!");	    				
	    			}
	    			
	    			MessageReceived wMsg = new MessageReceived(
	    					wParsedMsg.getJSONObject(Message.MESSAGE_HEADERS).getString(Message.MESSAGE_HEADER_UID), 
	    					wParsedMsg.getString(Message.MESSAGE_SUBJECT), 
	    					null, 
	    					null, 
	    					null, 
	    					null, 
	    					null, 
	    					null);
	    			// content
	    			Object cont = wParsedMsg.opt(Message.MESSAGE_CONTENT);
	    			if (cont != null) {
	    				if (cont instanceof JSONObject || cont instanceof JSONArray) {
		    				wMsg.setContent(pSerializer.fromJSON(cont.toString()));		    				
		    			} else
		    				wMsg.setContent(cont);
	    			} else {
	    				wMsg.setContent(null);
	    			}
	    			// headers 
	    			Iterator<String> wKeys;
	    			if (wParsedMsg.getJSONObject(Message.MESSAGE_HEADERS) != null) {
	    				wKeys = wParsedMsg.getJSONObject(Message.MESSAGE_HEADERS).keys();
	    				while(wKeys.hasNext()) {
	    					String key = wKeys.next();
	    					wMsg.addHeader(key, wParsedMsg.getJSONObject(Message.MESSAGE_HEADERS).get(key));
	    				}
	    			}
	    			
	    			// metadata 
	    			Iterator<String> wKeys2;
	    			if (wParsedMsg.getJSONObject(Message.MESSAGE_METADATA) != null) {
	    				wKeys2 = wParsedMsg.getJSONObject(Message.MESSAGE_METADATA).keys();
	    				while(wKeys2.hasNext()) {
	    					String key = wKeys2.next();
	    					wMsg.addMetadata(key, wParsedMsg.getJSONObject(Message.MESSAGE_METADATA).get(key));
	    				}
	    			}
					
	    			return wMsg;
				} catch (JSONException e) {
					e.printStackTrace();
					return null;
				}
	    	}
		} catch (Exception e) {
			e.printStackTrace();
			return null;
		}
	 }	 
}
