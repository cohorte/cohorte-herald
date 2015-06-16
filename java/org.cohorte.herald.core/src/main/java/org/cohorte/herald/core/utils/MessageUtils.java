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
			json.put(Message.MESSAGE_HERALD_VERSION, Message.HERALD_SPECIFICATION_VERSION);
			
			JSONObject headers = new JSONObject();
			for (String key : aMsg.getHeaders().keySet()) {
				headers.put(key, aMsg.getHeaders().get(key));
			}			
			json.put(Message.MESSAGE_HEADERS, headers);
			
			json.put(Message.MESSAGE_SUBJECT, aMsg.getSubject());
			
			if (aMsg.getContent() != null) {
				if (aMsg.getContent() instanceof String) {
					json.put(Message.MESSAGE_CONTENT, aMsg.getContent());
				} else {
					JSONObject content = new JSONObject(pSerializer.toJSON(aMsg.getContent()));
					json.put(Message.MESSAGE_CONTENT, content);
				}
			}
			
		} catch (JSONException e) {			
			e.printStackTrace();
			return null;
		}
		
		return json.toString();
	}
	
	 public static MessageReceived fromJSON(String json) throws UnmarshallException {
		 try {
	    	JSONObject wParsedMsg = new JSONObject(json);	    	
	    	{
	    		try {
	    			int heraldVersion = wParsedMsg.getInt(Message.MESSAGE_HERALD_VERSION);
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
