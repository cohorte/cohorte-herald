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

import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.net.HttpURLConnection;
import java.net.MalformedURLException;
import java.net.URL;
import java.util.Map;

import javax.servlet.ServletException;

import org.apache.felix.ipojo.annotations.Bind;
import org.apache.felix.ipojo.annotations.Component;
import org.apache.felix.ipojo.annotations.Instantiate;
import org.apache.felix.ipojo.annotations.Invalidate;
import org.apache.felix.ipojo.annotations.Provides;
import org.apache.felix.ipojo.annotations.Requires;
import org.apache.felix.ipojo.annotations.ServiceController;
import org.apache.felix.ipojo.annotations.ServiceProperty;
import org.apache.felix.ipojo.annotations.Unbind;
import org.apache.felix.ipojo.annotations.Validate;
import org.cohorte.herald.HeraldException;
import org.cohorte.herald.IDirectory;
import org.cohorte.herald.IHeraldInternal;
import org.cohorte.herald.MessageReceived;
import org.cohorte.herald.Peer;
import org.cohorte.herald.ValueError;
import org.cohorte.herald.http.HTTPAccess;
import org.cohorte.herald.http.HTTPExtra;
import org.cohorte.herald.http.IHttpConstants;
import org.cohorte.herald.transport.IContactHook;
import org.cohorte.herald.transport.IDiscoveryConstants;
import org.cohorte.herald.transport.PeerContact;
import org.jabsorb.ng.JSONSerializer;
import org.jabsorb.ng.serializer.MarshallException;
import org.jabsorb.ng.serializer.UnmarshallException;
import org.osgi.service.http.HttpService;
import org.osgi.service.http.NamespaceException;
import org.osgi.service.log.LogService;

/**
 * The Herald HTTP reception service
 *
 * @author Thomas Calmant
 */
@Component
@Provides(specifications = IHttpReceiver.class)
@Instantiate(name = "herald-http-receiver")
public class HttpReceiver implements IHttpReceiver, IContactHook {

    /** HTTP service port property */
    private static final String HTTP_SERVICE_PORT = "org.osgi.service.http.port";

    /** HTTPService dependency ID */
    private static final String IPOJO_ID_HTTP = "http.service";

    /** The peer contact utility */
    private PeerContact pContact;

    /** Service controller */
    @ServiceController(value = false)
    private boolean pController;

    /** Herald directory */
    @Requires
    private IDirectory pDirectory;

    /** Herald core service (internal: always on) */
    @Requires
    private IHeraldInternal pHerald;

    /** HTTP directory */
    @Requires
    private IHttpDirectory pHttpDirectory;

    /** HTTP service port */
    private int pHttpPort;

    /** HTTP service, injected by iPOJO */
    @Requires(id = IPOJO_ID_HTTP, filter = "(" + HTTP_SERVICE_PORT + "=*)")
    private HttpService pHttpService;

    /** The log service */
    @Requires(optional = true)
    private LogService pLogger;

    /** The Jabsorb serializer */
    private JSONSerializer pSerializer;

    /** The path to the reception servlet */
    @ServiceProperty(name = "servlet.path", value = IHttpConstants.SERVLET_PATH)
    private String pServletPath;

    /**
     * HTTP service ready
     *
     * @param aHttpService
     *            The bound service
     * @param aServiceProperties
     *            The HTTP service properties
     */
    @Bind(id = IPOJO_ID_HTTP)
    private void bindHttpService(final HttpService aHttpService,
            final Map<?, ?> aServiceProperties) {

        final Object rawPort = aServiceProperties.get(HTTP_SERVICE_PORT);

        if (rawPort instanceof Number) {
            // Get the integer
            pHttpPort = ((Number) rawPort).intValue();

        } else if (rawPort instanceof CharSequence) {
            // Parse the string
            pHttpPort = Integer.parseInt(rawPort.toString());

        } else {
            // Unknown port type
            pLogger.log(LogService.LOG_WARNING, "Couldn't read access port="
                    + rawPort);
            pHttpPort = -1;
        }

        pLogger.log(LogService.LOG_INFO, "HTTP Receiver bound to port="
                + pHttpPort);
    }

    /**
     * Checks if the peer UID matches cached information (see
     * {@link IHttpDirectory#checkAccess(String, String, int)}
     *
     * @param aPeerUid
     *            The UID of peer
     * @param aHost
     *            The checked host
     * @param aPort
     *            The checked port
     * @return True if the peer matches the given information
     * @throws ValueError
     *             Unknown peer UID
     */
    public boolean checkAccess(final String aPeerUid, final String aHost,
            final int aPort) throws ValueError {

        return pHttpDirectory.checkAccess(aPeerUid, aHost, aPort);
    }

    /**
     * Converts a JSON string to a Java Object
     *
     * @param aJsonString
     *            The input JSON string
     * @return A Java object (can be an array...)
     * @throws UnmarshallException
     *             Error loading the Java object
     */
    public Object deserialize(final String aJsonString)
            throws UnmarshallException {

        return pSerializer.fromJSON(aJsonString);
    }

    /*
     * (non-Javadoc)
     * 
     * @see org.cohorte.herald.http.impl.IHttpReceiver#getAccessInfo()
     */
    @Override
    public HTTPAccess getAccessInfo() {

        // No host
        return new HTTPAccess(null, pHttpPort, pServletPath);
    }

    /**
     * Returns the local peer bean
     *
     * @return The local peer bean
     */
    public Peer getLocalPeer() {

        return pDirectory.getLocalPeer();
    }

    /*
     * (non-Javadoc)
     * 
     * @see
     * org.cohorte.herald.http.impl.IHttpReceiver#grabPeer(java.lang.String,
     * int, java.lang.String)
     */
    @SuppressWarnings("unchecked")
    @Override
    public Map<String, Object> grabPeer(final String aHostAddress,
            final int aPort, final String aPath) {

        // Compute the URL to the peer
        final URL url;
        try {
            url = new URL("http", aHostAddress, aPort, aPath);

        } catch (final MalformedURLException ex) {
            // Bad URL
            pLogger.log(LogService.LOG_ERROR,
                    "Error computing Peer access URL: " + ex);
            return null;
        }

        // Open the HTTP connection
        HttpURLConnection httpConnection = null;
        try {
            httpConnection = (HttpURLConnection) url.openConnection();

            // POST message
            httpConnection.setRequestMethod("GET");

            // Connect
            httpConnection.connect();

            // Read content
            final int responseCode = httpConnection.getResponseCode();
            if (responseCode != HttpURLConnection.HTTP_OK) {
                // Error
                pLogger.log(LogService.LOG_ERROR, "Error on peer's side: "
                        + responseCode);
                return null;
            }

            // Read the response
            final byte[] rawData = inputStreamToBytes(httpConnection
                    .getInputStream());

            // Convert bytes to string, using the best encoding
            String charsetName = httpConnection.getContentEncoding();
            if (charsetName == null) {
                charsetName = IHttpConstants.CHARSET_UTF8;
            }
            final String data = new String(rawData, charsetName);

            // Parse it
            final Object dump = deserialize(data);
            if (dump instanceof Map) {
                // It's map, as expected: return it
                return (Map<String, Object>) dump;
            }

        } catch (final IOException ex) {
            // Error connection to the peer
            pLogger.log(LogService.LOG_ERROR, "Error connecting to the peer: "
                    + ex, ex);

        } catch (final UnmarshallException ex) {
            // Bad string
            pLogger.log(LogService.LOG_ERROR,
                    "Error parsing peer description: " + ex, ex);

        } finally {
            // Clean up
            if (httpConnection != null) {
                httpConnection.disconnect();
            }
        }

        // Something bad or wrong occurred
        return null;
    }

    /**
     * Lets Herald handle the received message
     *
     * @param aMessage
     *            The received message
     */
    public void handleMessage(final MessageReceived aMessage) {

        if (aMessage.getSubject().startsWith(
                IDiscoveryConstants.SUBJECT_DISCOVERY_PREFIX)) {
            // Discovery message
            try {
                pContact.handleDiscoveryMessage(pHerald, aMessage);

            } catch (final HeraldException ex) {
                // Error replying to final a discovered peer
                pLogger.log(LogService.LOG_ERROR,
                        "Error replying to a discovered peer: " + ex, ex);
            }

        } else {
            // Standard message
            pHerald.handleMessage(aMessage);
        }
    }

    /**
     * Converts an input stream into a byte array
     *
     * @param aInputStream
     *            An input stream
     * @return The input stream content, null on error
     * @throws IOException
     *             Something went wrong
     */
    public byte[] inputStreamToBytes(final InputStream aInputStream)
            throws IOException {

        if (aInputStream == null) {
            return null;
        }

        final ByteArrayOutputStream outStream = new ByteArrayOutputStream();
        final byte[] buffer = new byte[8192];
        int read = 0;

        do {
            read = aInputStream.read(buffer);
            if (read > 0) {
                outStream.write(buffer, 0, read);
            }

        } while (read > 0);

        outStream.close();
        return outStream.toByteArray();
    }

    /**
     * Component invalidated
     */
    @Invalidate
    public void invalidate() {

        pContact.clear();
        pContact = null;
    }

    /**
     * Logs an entry using the injected log service
     *
     * @param aLogLevel
     *            Log level
     * @param aMessage
     *            Message to log
     */
    public void log(final int aLogLevel, final String aMessage) {

        log(aLogLevel, aMessage, null);
    }

    /**
     * Logs an entry using the injected log service
     *
     * @param aLogLevel
     *            Log level
     * @param aMessage
     *            Message to log
     * @param aThrowable
     *            The exception associated to the log
     */
    public void log(final int aLogLevel, final String aMessage,
            final Throwable aThrowable) {

        pLogger.log(aLogLevel, aMessage, aThrowable);
    }

    /**
     * Converts an object to a JSON dump (using Jabsorb)
     *
     * @param aData
     *            The data to serialize
     * @return The JSON representation of the object, as a string
     * @throws MarshallException
     *             Error converting the object
     */
    public String serialize(final Object aData) throws MarshallException {

        return pSerializer.toJSON(aData);
    }

    /**
     * HTTP service gone
     */
    @Unbind(id = IPOJO_ID_HTTP)
    private void unbindHttpService() {

        // Forget the port
        pHttpPort = 0;
    }

    /*
     * (non-Javadoc)
     *
     * @see
     * org.cohorte.herald.transport.IContactHook#updateDescription(org.cohorte
     * .herald.MessageReceived, java.util.Map)
     */
    @Override
    public Map<String, Object> updateDescription(
            final MessageReceived aMessage,
            final Map<String, Object> aDescription) {

        if (aMessage.getAccess().equals(IHttpConstants.ACCESS_ID)) {
            // Forge the access to the HTTP server using extra information
            final HTTPExtra extra = (HTTPExtra) aMessage.getExtra();
            final HTTPAccess updatedAccess = new HTTPAccess(extra.getHost(),
                    extra.getPort(), extra.getPath());

            // Update the remote peer description with its HTTP access
            @SuppressWarnings("unchecked")
            final Map<String, Object> accessDump = (Map<String, Object>) aDescription
                    .get("accesses");
            accessDump.put(IHttpConstants.ACCESS_ID, updatedAccess.dump());
        }

        return aDescription;
    }

    /**
     * Component validated
     */
    @Validate
    public void validate() {

        // Disable the service
        pController = false;

        // Setup the peer contact
        pContact = new PeerContact(pDirectory, this, pLogger);

        // Prepare the JSON serializer
        pSerializer = new JSONSerializer();
        try {
            pSerializer.registerDefaultSerializers();
        } catch (final Exception ex) {
            pLogger.log(LogService.LOG_ERROR,
                    "Error setting up the JSON serializer: " + ex, ex);
            return;
        }

        // Prepare and register the servlet
        final HttpReceiverServlet servlet = new HttpReceiverServlet(this);
        try {
            pHttpService.registerServlet(pServletPath, servlet, null, null);

        } catch (final ServletException ex) {
            pLogger.log(LogService.LOG_ERROR,
                    "Error registering the Herald HTTP Receiver servlet:" + ex,
                    ex);
            return;

        } catch (final NamespaceException ex) {
            pLogger.log(LogService.LOG_ERROR,
                    "Herald HTTP Receiver servlet name is already taken:" + ex,
                    ex);
            return;
        }

        // Register our local access
        pDirectory.getLocalPeer().setAccess(IHttpConstants.ACCESS_ID,
                new HTTPAccess("localhost", pHttpPort, pServletPath));

        // Activate our server
        pController = true;
    }
}
