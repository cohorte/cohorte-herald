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
import java.io.InputStream;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.MalformedURLException;
import java.net.URL;
import java.util.Collection;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.Map;
import java.util.Map.Entry;
import java.util.Set;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.TimeUnit;

import org.apache.felix.ipojo.annotations.Component;
import org.apache.felix.ipojo.annotations.Instantiate;
import org.apache.felix.ipojo.annotations.Invalidate;
import org.apache.felix.ipojo.annotations.Provides;
import org.apache.felix.ipojo.annotations.Requires;
import org.apache.felix.ipojo.annotations.ServiceController;
import org.apache.felix.ipojo.annotations.ServiceProperty;
import org.apache.felix.ipojo.annotations.Validate;
import org.cohorte.herald.HeraldException;
import org.cohorte.herald.IConstants;
import org.cohorte.herald.IDirectory;
import org.cohorte.herald.ITransport;
import org.cohorte.herald.InvalidPeerAccess;
import org.cohorte.herald.Message;
import org.cohorte.herald.Peer;
import org.cohorte.herald.Target;
import org.cohorte.herald.core.utils.MessageUtils;
import org.cohorte.herald.http.HTTPAccess;
import org.cohorte.herald.http.HTTPExtra;
import org.cohorte.herald.http.IHttpConstants;
import org.cohorte.herald.utils.PelixFuture;
import org.cohorte.herald.utils.PelixFuture.Callable;
import org.cohorte.herald.utils.PelixFuture.Callback;
import org.jabsorb.ng.JSONSerializer;
import org.jabsorb.ng.serializer.MarshallException;
import org.osgi.service.log.LogService;

/**
 * HTTP sender for Herald
 *
 * @author Thomas Calmant
 */
@Component
@Provides(specifications = ITransport.class)
@Instantiate(name = "herald-http-transport")
public class HttpTransport implements ITransport {

	/** Access ID property */
	@ServiceProperty(name = IConstants.PROP_ACCESS_ID, value = IHttpConstants.ACCESS_ID)
	private String pAccessId;

	/** The service controller */
	@ServiceController
	private boolean pController;

	/** Herald core directory */
	@Requires
	private IDirectory pDirectory;

	/** The thread pool */
	private ExecutorService pExecutor;

	/** Local peer UID */
	private String pLocalUid;

	/** The log service */
	@Requires(optional = true)
	private LogService pLogger;

	/** HTTP Reception component */
	@Requires
	private IHttpReceiver pReceiver;

	/** The Jabsorb serializer */
	private JSONSerializer pSerializer;

	/*
	 * (non-Javadoc)
	 * 
	 * @see org.cohorte.herald.ITransport#fire(org.cohorte.herald.Peer,
	 * org.cohorte.herald.Message)
	 */
	@Override
	public void fire(final Peer aPeer, final Message aMessage)
			throws HeraldException {

		fire(aPeer, aMessage, null);
	}

	/*
	 * (non-Javadoc)
	 * 
	 * @see org.cohorte.herald.ITransport#fire(org.cohorte.herald.Peer,
	 * org.cohorte.herald.Message, java.lang.Object)
	 */
	@Override
	public void fire(final Peer aPeer, final Message aMessage,
			final Object aExtra) throws HeraldException {

		// Compute parent UID, in case of reply
		String parentUid = null;
		if (aExtra instanceof HTTPExtra) {
			parentUid = ((HTTPExtra) aExtra).getParentUid();
		}

		// Try to compute the URL to access the peer
		final URL url = getAccessUrl(aPeer, aExtra);

		// Send the HTTP request (blocking)
		final Map<String, String> headers = makeHeaders(aMessage, parentUid, aPeer, null);
		String content;
		try {
			content = makeContent(aMessage);

		} catch (final MarshallException ex) {
			throw new HeraldException(new Target(aPeer),
					"Error marshalling the message content", ex);
		}

		sendRequest(aPeer, url, headers, content);
	}

	/*
	 * (non-Javadoc)
	 * 
	 * @see org.cohorte.herald.ITransport#fireGroup(java.lang.String,
	 * java.util.Collection, org.cohorte.herald.Message)
	 */
	@Override
	public Collection<Peer> fireGroup(final String aGroup,
			final Collection<Peer> aPeers, final Message aMessage)
			throws HeraldException {

		// Prepare the message
		final Map<String, String> headers = makeHeaders(aMessage, null, null, aGroup);
		final String content;
		try {
			content = makeContent(aMessage);

		} catch (final MarshallException ex) {
			throw new HeraldException(
					new Target(aGroup, Target.toUids(aPeers)),
					"Error marshalling the message content", ex);
		}

		// Keep track of the peers we reached
		final Set<Peer> accessedPeers = new LinkedHashSet<>();
		final CountDownLatch countdown = new CountDownLatch(aPeers.size());

		final Callback<Object, Peer> peerResult = new Callback<Object, Peer>() {

			/*
			 * (non-Javadoc)
			 * 
			 * @see
			 * org.cohorte.herald.utils.PelixFuture.Callback#run(java.lang.Object
			 * , java.lang.Throwable, java.lang.Object)
			 */
			@Override
			public void run(final Object aResult, final Throwable aThrowable,
					final Peer aPeer) {

				if (aThrowable == null) {
					// No error
					accessedPeers.add(aPeer);

				} else {
					// Log the error
					pLogger.log(LogService.LOG_DEBUG,
							"Error posting a message to " + aPeer + ": "
									+ aThrowable, aThrowable);
				}

				// Update the count down in any case
				countdown.countDown();
			}
		};

		// Send a request to each peer
		for (final Peer peer : aPeers) {
			try {
				// Compute the access URL
				final URL url = getAccessUrl(peer, null);

				// Prepare the future call
				final PelixFuture<Object, Peer> future = new PelixFuture<Object, Peer>();
				future.setCallback(peerResult, peer);
				future.setMethod(new Callable<Object>() {

					@Override
					public Object run() throws Exception {

						sendRequest(peer, url, headers, content);
						return null;
					}
				});

				// Call it from the thread pool
				pExecutor.execute(future);

			} catch (final InvalidPeerAccess ex) {
				// No HTTP access description
				pLogger.log(LogService.LOG_DEBUG, "No "
						+ IHttpConstants.ACCESS_ID + " access found for "
						+ peer);
			}
		}

		// Wait 10 sec. max for answers
		try {
			if (!countdown.await(10, TimeUnit.SECONDS)) {
				pLogger.log(LogService.LOG_WARNING,
						"Not all peers have been reached after 10 seconds.");
			}
		} catch (final InterruptedException ex) {
			pLogger.log(LogService.LOG_WARNING,
					"Interrupted while waiting for peers to receive the message");
		}

		// Return a copy of the access peers set
		return new LinkedHashSet<Peer>(accessedPeers);
	}

	/**
	 * Computes the URL to access the Herald servlet on the given peer
	 *
	 * @param aPeer
	 *            A peer bean
	 * @param aExtra
	 *            Optional extra information, given for replies
	 * @return A {@link URL} object
	 * @throws InvalidPeerAccess
	 *             Couldn't compute the access to the peer
	 */
	private URL getAccessUrl(final Peer aPeer, final Object aExtra)
			throws InvalidPeerAccess {

		String host = null;
		int port = 0;
		String path = null;

		if (aExtra instanceof HTTPExtra) {
			// Try to use extra information
			final HTTPExtra extraAccess = (HTTPExtra) aExtra;
			host = extraAccess.getHost();
			port = extraAccess.getPort();
			path = extraAccess.getPath();
		}

		if (aPeer != null && (host == null || host.isEmpty())) {
			// Use the peer description, if any
			final HTTPAccess peerAccess = (HTTPAccess) aPeer
					.getAccess(IHttpConstants.ACCESS_ID);
			host = peerAccess.getHost();
			port = peerAccess.getPort();
			path = peerAccess.getPath();
		}

		// If we have nothing at this point, we can't compute an access
		if (host == null || host.isEmpty()) {
			throw new InvalidPeerAccess(new Target(aPeer), "No "
					+ IHttpConstants.ACCESS_ID + " access found");
		}

		// No port given, remove it from the URL
		if (port == 0) {
			port = -1;
		}

		try {
			// Forge the URL
			return new URL("http", host, port, path);

		} catch (final MalformedURLException ex) {
			throw new InvalidPeerAccess(new Target(aPeer),
					"Invalid access URL: " + ex);
		}
	}

	/**
	 * Component invalidated
	 */
	@Invalidate
	public void invalidate() {

		// Stop the thread pool
		pExecutor.shutdownNow();

		// Clean up
		pExecutor = null;
		pLocalUid = null;
		pSerializer = null;
	}

	/**
	 * Converts the given object into a JSON string
	 *
	 * @param aContent
	 *            The object to convert
	 * @return The corresponding JSON string
	 * @throws MarshallException
	 *             Error converting the object
	 */
	private String makeContent(final Message aMsg) throws MarshallException {
		return MessageUtils.toJSON(aMsg);		
	}

	/**
	 * Prepares the headers to send in the HTTP request
	 *
	 * @param aMessage
	 *            Message to be sent
	 * @param aParentUid
	 *            UID of the message this one replies to (optional)
	 * @return The request headers as a map
	 */
	private Map<String, String> makeHeaders(final Message aMessage,
			final String aParentUid, final Peer aPeer, final String aGroup) {

		final Map<String, String> headers = new LinkedHashMap<>();

		final HTTPAccess localAccess = pReceiver.getAccessInfo();

		aMessage.addHeader(Message.MESSAGE_HEADER_SENDER_UID, pLocalUid);
		aMessage.addHeader(IHttpConstants.MESSAGE_HEADER_PORT, Integer.toString(localAccess.getPort()));
		aMessage.addHeader(IHttpConstants.MESSAGE_HEADER_PATH, localAccess.getPath());
		if (aPeer != null) 
			aMessage.addHeader(Message.MESSAGE_HEADER_TARGET_PEER, aPeer.getUid());
		if (aGroup != null)
			aMessage.addHeader(Message.MESSAGE_HEADER_TARGET_GROUP, aGroup);
		if (aParentUid != null && !aParentUid.isEmpty()) {
			aMessage.addHeader(Message.MESSAGE_HEADER_REPLIES_TO, aParentUid);
		}
		
		return headers;
	}

	/**
	 * Sends a POST request and reads the answer
	 *
	 * @param aPeer
	 *            The targeted peer
	 * @param aUrl
	 *            The URL to the targeted peer
	 * @param aHeaders
	 *            Request headers
	 * @param aContent
	 *            Body of the POST request
	 * @throws HeraldException
	 *             Error sending the request
	 */
	private void sendRequest(final Peer aPeer, final URL aUrl,
			final Map<String, String> aHeaders, final String aContent)
			throws HeraldException {

		// Open the connection
		HttpURLConnection httpConnection = null;
		try {
			httpConnection = (HttpURLConnection) aUrl.openConnection();

			// POST message
			httpConnection.setRequestMethod("POST");
			httpConnection.setUseCaches(false);
			httpConnection.setDoOutput(true);

			// Headers
			for (final Entry<String, String> header : aHeaders.entrySet()) {
				httpConnection.setRequestProperty(header.getKey(),
						header.getValue());
			}

			// Convert the content to bytes
			final byte[] rawContent;
			if (aContent == null) {
				rawContent = new byte[0];
			} else {
				rawContent = aContent.getBytes(IHttpConstants.CHARSET_UTF8);
			}

			// Also add content properties headers
			httpConnection.setRequestProperty("Content-Type",
					IHttpConstants.CONTENT_TYPE_JSON);
			httpConnection.setRequestProperty("Content-Encoding",
					IHttpConstants.CHARSET_UTF8);
			httpConnection.setRequestProperty("Content-Length",
					Integer.toString(rawContent.length));

			// After fields, before content
			httpConnection.connect();

			// Write the event in the request body, if any
			if (rawContent.length > 0) {
				final OutputStream outStream = httpConnection.getOutputStream();
				try {
					outStream.write(rawContent);
					outStream.flush();
				} finally {
					// Always be nice...
					outStream.close();
				}
			}

			// Flush the request
			final int responseCode = httpConnection.getResponseCode();
			if (responseCode != HttpURLConnection.HTTP_OK) {
				throw new HeraldException(new Target(aPeer),
						"HTTP request failed (server error): " + responseCode);
			}

		} catch (final IOException ex) {
			throw new HeraldException(new Target(aPeer),
					"HTTP request failed (socket error): " + ex);

		} finally {
			if (httpConnection != null) {
				// Read the whole response if needed
				InputStream inStream;
				try {
					inStream = httpConnection.getInputStream();
				} catch (IOException ex) {
					inStream = httpConnection.getErrorStream();
				}

				try {
					while (inStream.read() > 0) {
						// Don't care about the answer content
					}
				} catch (IOException ex) {
					// Log it ?
				} finally {
					try {
						// Close the stream
						inStream.close();
					} catch (IOException e) {
						// Log it ?
					}
				}
			}
		}
	}

	/**
	 * Component validated
	 */
	@Validate
	public void validate() {

		// Prepare the JSON serializer
		pSerializer = new JSONSerializer();
		try {
			pSerializer.registerDefaultSerializers();
		} catch (final Exception ex) {
			// Error setting up the serializer: abandon
			pLogger.log(LogService.LOG_ERROR,
					"Error setting up the JSON serializer: " + ex, ex);
			pController = false;
			return;
		}

		// Store the UID of the local peer
		pLocalUid = pDirectory.getLocalUid();

		// Start the thread pool
		pExecutor = Executors.newFixedThreadPool(5);

		// Everything is OK
		pController = true;
	}
}
