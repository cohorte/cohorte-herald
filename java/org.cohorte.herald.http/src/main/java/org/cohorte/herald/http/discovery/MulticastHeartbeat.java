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
package org.cohorte.herald.http.discovery;

import java.io.IOException;
import java.io.UnsupportedEncodingException;
import java.net.InetAddress;
import java.net.InetSocketAddress;
import java.net.SocketException;
import java.nio.BufferUnderflowException;
import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import java.util.Collection;
import java.util.HashMap;
import java.util.LinkedHashSet;
import java.util.Map;
import java.util.Map.Entry;

import org.apache.felix.ipojo.annotations.Component;
import org.apache.felix.ipojo.annotations.Invalidate;
import org.apache.felix.ipojo.annotations.Property;
import org.apache.felix.ipojo.annotations.Requires;
import org.apache.felix.ipojo.annotations.Validate;
import org.cohorte.herald.HeraldException;
import org.cohorte.herald.IConstants;
import org.cohorte.herald.IDirectory;
import org.cohorte.herald.ITransport;
import org.cohorte.herald.Message;
import org.cohorte.herald.Peer;
import org.cohorte.herald.UnknownPeer;
import org.cohorte.herald.http.HTTPAccess;
import org.cohorte.herald.http.HTTPExtra;
import org.cohorte.herald.http.IHttpConstants;
import org.cohorte.herald.http.impl.IHttpReceiver;
import org.cohorte.herald.transport.IDiscoveryConstants;
import org.cohorte.herald.utils.Event;
import org.cohorte.remote.multicast.utils.IPacketListener;
import org.cohorte.remote.multicast.utils.MulticastHandler;
import org.osgi.service.log.LogService;

/**
 * Discovery of Herald peers based on multicast
 *
 * @author Thomas Calmant
 */
@Component(name = IHttpConstants.FACTORY_DISCOVERY_MULTICAST)
public class MulticastHeartbeat implements IPacketListener {

	/** UDP Packet: Peer heart beat */
	private static final byte PACKET_TYPE_HEARTBEAT = 1;

	/** UDP Packet: Last beat of a peer */
	private static final byte PACKET_TYPE_LASTBEAT = 2;

	/** Maximum time without peer notification : 30 seconds */
	private static final long PEER_TTL = 30000;

	/** The Herald directory */
	@Requires
	private IDirectory pDirectory;

	/** The heart beat thread */
	private Thread pHeartThread;

	/** The HTTP transport implementation */
	@Requires(filter = "(" + IConstants.PROP_ACCESS_ID + "=" + IHttpConstants.ACCESS_ID + ")")
	private ITransport pHttpTransport;

	/** Local peer bean */
	private Peer pLocalPeer;

	/** The logger */
	@Requires(optional = true)
	private LogService pLogger;

	/** The multicast receiver */
	private MulticastHandler pMulticast;

	/** The multicast group */
	@Property(name = "multicast.group", value = "239.0.0.1")
	// ff05::5
	private String pMulticastGroup;

	/** The multicast port */
	@Property(name = "multicast.port", value = "42000")
	private int pMulticastPort;

	/** Peer UID -&gt; Last seen time (LST) */
	private final Map<String, Long> pPeerLST = new HashMap<String, Long>();

	/** The HTTP reception part */
	@Requires
	private IHttpReceiver pReceiver;

	/** The loop-stop event */
	private final Event pStopEvent = new Event();

	/** The TTL thread */
	private Thread pTTLThread;

	/**
	 * Grab the description of a peer using the Herald servlet
	 *
	 * @param aHostAddress
	 *            Address which sent the heart beat
	 * @param aPort
	 *            Port of the Herald HTTP server
	 * @param aPath
	 *            Path to the Herald HTTP servlet
	 */
	private void discoverPeer(final String aHostAddress, final int aPort, final String aPath) {

		// Prepare extra information like for a reply
		final HTTPExtra extra = new HTTPExtra(aHostAddress, aPort, aPath, null);

		try {
			// Fire the message, using the HTTP transport directly
			// Peer registration will be done after it responds
			pHttpTransport.fire(null,
					new Message(IDiscoveryConstants.SUBJECT_DISCOVERY_STEP_1, pDirectory.getLocalPeer().dump()), extra);

		} catch (final HeraldException ex) {
			pLogger.log(LogService.LOG_ERROR, "Error contacting peer: " + ex, ex);
		}
	}

	/**
	 * Extracts a string from the given buffer
	 *
	 * @param aBuffer
	 *            A bytes buffer
	 * @return The read string, or null
	 */
	private String extractString(final ByteBuffer aBuffer) {

		// Get the length
		final int length = getUnsignedShort(aBuffer);

		// Get the bytes
		final byte[] buffer = new byte[length];
		try {
			aBuffer.get(buffer);

		} catch (final BufferUnderflowException ex) {
			pLogger.log(LogService.LOG_ERROR, "Missing data: " + ex, ex);
			return null;
		}

		// Return the string form
		try {
			return new String(buffer, IHttpConstants.CHARSET_UTF8);

		} catch (final UnsupportedEncodingException ex) {
			pLogger.log(LogService.LOG_ERROR, "Unsupported encoding: " + ex, ex);
			return null;
		}
	}

	/**
	 * Gets the next <strong>unsigned</strong> short in the byte buffer
	 *
	 * @param aBuffer
	 *            The byte buffer to read from
	 * @return The unsigned short, boxed in an integer
	 */
	private int getUnsignedShort(final ByteBuffer aBuffer) {

		// Get the short, box it to an int then only keep the short value and
		// ignore the sign bit
		return aBuffer.getShort() & 0xffff;
	}

	/*
	 * (non-Javadoc)
	 *
	 * @see
	 * org.cohorte.remote.multicast.utils.IPacketListener#handleError(java.lang
	 * .Exception)
	 */
	@Override
	public boolean handleError(final Exception aException) {

		pLogger.log(LogService.LOG_WARNING, "Error while receiving a UDP packet: " + aException, aException);

		// Continue if the exception is not "important"
		return !(aException instanceof SocketException || aException instanceof NullPointerException);
	}

	/**
	 * Handle the heart beat of a peer
	 *
	 * @param aPeerUid
	 *            The UID of the peer
	 * @param aApplicationId
	 *            The ID of the application
	 * @param aHostAddress
	 *            The address we received the beat from
	 * @param aPort
	 *            The HTTP port of the peer
	 * @param aPath
	 *            The path to the Herald servlet
	 */
	private void handleHeartbeat(final String aPeerUid, final String aApplicationId, final String aHostAddress,
			final int aPort, final String aPath) {

		if (pLocalPeer.getUid().equals(aPeerUid) || !pLocalPeer.getApplicationId().equals(aApplicationId)) {
			// Ignore local and foreign heart beats
			return;
		}

		final Long previousLST;
		synchronized (pPeerLST) {
			// Update the peer LST
			previousLST = pPeerLST.put(aPeerUid, System.currentTimeMillis());
		}
		
		if (previousLST == null) {
			// Peer wasn't known
			discoverPeer(aHostAddress, aPort, aPath);
		}
	}

	/**
	 * Handle the last beat of a peer
	 *
	 * @param aPeerUid
	 *            The UID of the peer going away
	 * @param aApplicationId
	 *            The ID of application of the peer going away
	 */
	private void handleLastbeat(final String aPeerUid, final String aApplicationId) {

		if (pLocalPeer.getUid().equals(aPeerUid) || !pLocalPeer.getApplicationId().equals(aApplicationId)) {
			// Ignore local and foreign heart beats
			return;
		}

		synchronized (pPeerLST) {
			// Forget about the peer
			pPeerLST.remove(aPeerUid);

			try {
				// Update the directory
				final Peer peer = pDirectory.getPeer(aPeerUid);
				peer.unsetAccess(IHttpConstants.ACCESS_ID);

			} catch (final UnknownPeer ex) {
				// Unknown peer: ignore
			}
		}
	}

	/*
	 * (non-Javadoc)
	 *
	 * @see
	 * org.cohorte.remote.multicast.utils.IPacketListener#handlePacket(java.
	 * net.InetSocketAddress, byte[])
	 */
	@Override
	public void handlePacket(final InetSocketAddress aSender, final byte[] aContent) {

		// Make a little endian byte array reader, to extract the packet content
		final ByteBuffer buffer = ByteBuffer.wrap(aContent);
		buffer.order(ByteOrder.LITTLE_ENDIAN);

		final byte packetType = buffer.get();
		switch (packetType) {
		case PACKET_TYPE_HEARTBEAT: {
			// Extract content
			final int port = getUnsignedShort(buffer);
			final String path = extractString(buffer);
			final String peerUid = extractString(buffer);
			final String applicationId = extractString(buffer);

			// Handle the packet
			handleHeartbeat(peerUid, applicationId, aSender.getAddress().getHostAddress(), port, path);
			break;
		}

		case PACKET_TYPE_LASTBEAT: {
			// Handle the last beat of a peer
			final String peerUid = extractString(buffer);
			final String applicationId = extractString(buffer);
			handleLastbeat(peerUid, applicationId);
			break;
		}

		default:
			pLogger.log(LogService.LOG_DEBUG, "Unknown packet type=" + (int) packetType);
			break;
		}
	}

	/**
	 * Loop sending heart beats every 20 seconds
	 */
	private void heartLoop() {

		// Prepare the packet
		byte[] beat;
		try {
			beat = makeHeartbeat();

		} catch (final UnsupportedEncodingException ex) {
			// Should never happen
			pLogger.log(LogService.LOG_ERROR, "Error encoding strings: " + ex, ex);
			return;
		}

		do {
			try {
				pMulticast.send(beat);

			} catch (final IOException ex) {
				pLogger.log(LogService.LOG_ERROR, "Error sending heart beat: " + ex, ex);
			}
		} while (!pStopEvent.waitEvent(20000L));
	}

	/**
	 * Component invalidated
	 */
	@Invalidate
	public void invalidate() {

		// Stop threads
		pStopEvent.set();

		// Wait a second for threads to stop
		try {
			pHeartThread.join(1000);
			pTTLThread.join(1000);
		} catch (final InterruptedException e) {
			// Join interrupted
		}

		// Stop the multicast listener
		if (pMulticast != null) {
			try {
				// Send a last beat message
				final byte[] lastBeat = makeLastbeat();
				pMulticast.send(lastBeat);
			} catch (final IOException ex) {
				pLogger.log(LogService.LOG_WARNING, "Error sending last beat packet: " + ex, ex);
			}

			try {
				// Stop listening to packets
				pMulticast.stop();

			} catch (final IOException ex) {
				pLogger.log(LogService.LOG_WARNING, "Error stopping the multicast listener: " + ex, ex);
			}
		}

		// Clean up
		pPeerLST.clear();
		pLocalPeer = null;
		pMulticast = null;
		pHeartThread = null;
		pTTLThread = null;
	}

	/**
	 * Loop that validates the LST of all peers and removes those who took to
	 * long to respond
	 */
	private void lstLoop() {

		// Instantiate the collection only once
		final Collection<String> toDelete = new LinkedHashSet<>();

		do {
			synchronized (pPeerLST) {
				final long loopStart = System.currentTimeMillis();

				for (final Entry<String, Long> entry : pPeerLST.entrySet()) {
					final String peerUid = entry.getKey();
					final Long lastSeen = entry.getValue();

					if (lastSeen == null) {
						// No LST for this peer, ignore it
						pLogger.log(LogService.LOG_WARNING, "Invalid LST for " + peerUid);

					} else if (loopStart - lastSeen > PEER_TTL) {
						// TTL reached
						toDelete.add(peerUid);
						pLogger.log(LogService.LOG_DEBUG, "Peer " + peerUid + " reached TTL.");
					}
				}

				for (final String peerUid : toDelete) {
					// Unregister those peers
					pPeerLST.remove(peerUid);
					pDirectory.unregister(peerUid);
				}
			}

			// Clean up and wait for next loop
			toDelete.clear();

		} while (!pStopEvent.waitEvent(1000L));
	}

	/**
	 * Prepares the heart beat UDP packet
	 *
	 * Format : Little endian
	 * <ul>
	 * <li>Kind of beat (1 byte)</li>
	 * <li>Herald HTTP server port (2 bytes)</li>
	 * <li>Herald HTTP servlet path length (2 bytes)</li>
	 * <li>Herald HTTP servlet path (variable, UTF-8)</li>
	 * <li>Peer UID length (2 bytes)</li>
	 * <li>Peer UID (variable, UTF-8)</li>
	 * <li>Application ID length (2 bytes)</li>
	 * <li>Application ID (variable, UTF-8)</li>
	 * </ul>
	 *
	 * @return The heart beat packet content (byte array)
	 * @throws UnsupportedEncodingException
	 *             UTF-8 charset is not support
	 */
	private byte[] makeHeartbeat() throws UnsupportedEncodingException {

		// Get local information
		final HTTPAccess access = pReceiver.getAccessInfo();
		final String localUid = pLocalPeer.getUid();
		final String localAppId = pLocalPeer.getApplicationId();

		// Convert strings
		final byte[] uid = localUid.getBytes(IHttpConstants.CHARSET_UTF8);
		final byte[] appId = localAppId.getBytes(IHttpConstants.CHARSET_UTF8);
		final byte[] path = access.getPath().getBytes(IHttpConstants.CHARSET_UTF8);

		// Compute packet size (see method's documentation)
		final int packetSize = 1 + 2 + 2 + uid.length + 2 + path.length + 2 + appId.length;

		// Setup the buffer
		final ByteBuffer buffer = ByteBuffer.allocate(packetSize);
		buffer.order(ByteOrder.LITTLE_ENDIAN);

		// Kind (1 byte)
		buffer.put(PACKET_TYPE_HEARTBEAT);

		// HTTP server port
		buffer.putShort((short) access.getPort());

		// HTTP servlet path
		buffer.putShort((short) path.length);
		buffer.put(path);

		// Peer UID
		buffer.putShort((short) uid.length);
		buffer.put(uid);

		// Application ID
		buffer.putShort((short) appId.length);
		buffer.put(appId);
		return buffer.array();
	}

	/**
	 * Prepares the last beat UDP packet (when the peer is going away)
	 *
	 * Format : Little endian
	 * <ul>
	 * <li>Kind of beat (1 byte)</li>
	 * <li>Peer UID length (2 bytes)</li>
	 * <li>Peer UID (variable, UTF-8)</li>
	 * <li>Application ID length (2 bytes)</li>
	 * <li>Application ID (variable, UTF-8)</li>
	 * </ul>
	 *
	 * @return The last beat packet content (byte array)
	 * @throws UnsupportedEncodingException
	 *             UTF-8 charset is not support
	 */
	private byte[] makeLastbeat() throws UnsupportedEncodingException {

		// Get local information
		final String localUid = pLocalPeer.getUid();
		final String localAppId = pLocalPeer.getApplicationId();

		// Convert strings
		final byte[] uid = localUid.getBytes(IHttpConstants.CHARSET_UTF8);
		final byte[] appId = localAppId.getBytes(IHttpConstants.CHARSET_UTF8);

		// Compute packet size (see method's documentation)
		final int packetSize = 1 + 2 + uid.length + 2 + appId.length;

		// Setup the buffer
		final ByteBuffer buffer = ByteBuffer.allocate(packetSize);
		buffer.order(ByteOrder.LITTLE_ENDIAN);

		// Kind (1 byte)
		buffer.put(PACKET_TYPE_LASTBEAT);

		// Peer UID
		buffer.putShort((short) uid.length);
		buffer.put(uid);

		// Application ID
		buffer.putShort((short) appId.length);
		buffer.put(appId);
		return buffer.array();
	}

	/**
	 * Component validated
	 */
	@Validate
	public void validate() {

		// Reset the stop event
		pStopEvent.clear();

		// Get the local peer
		pLocalPeer = pDirectory.getLocalPeer();

		// Start the multicast listener
		try {
			pMulticast = new MulticastHandler(this, InetAddress.getByName(pMulticastGroup), pMulticastPort);
			pMulticast.start();

		} catch (final IOException ex) {
			pLogger.log(LogService.LOG_ERROR,
					"Couldn't start the multicast receiver for group=" + pMulticastGroup + ": " + ex, ex);
			try {
				// Clean up
				pMulticast.stop();

			} catch (final IOException e) {
				// Ignore
				pLogger.log(LogService.LOG_WARNING, "Couldn't clean up the multicast receiver: " + ex);
			}

			pMulticast = null;
			return;
		}

		// Start threads
		pTTLThread = new Thread(new Runnable() {

			@Override
			public void run() {

				lstLoop();
			}
		}, "Herald-HTTP-LST");

		pHeartThread = new Thread(new Runnable() {

			@Override
			public void run() {

				heartLoop();
			}
		}, "Herald-HTTP-HeartBeat");

		pHeartThread.start();
		pTTLThread.start();
	}
}
