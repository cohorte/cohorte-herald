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

package org.cohorte.herald.http;

import org.cohorte.herald.Access;

/**
 * Description of an HTTP access
 *
 * @author Thomas Calmant
 */
public class HTTPAccess extends Access {

    /**
     * Creates a bean from the result {@link #dump()}
     *
     * @param aDump
     *            The result of {@link #dump()}
     * @return The created bean, or null
     */
    public static HTTPAccess load(final Object aDump) {

        if (aDump instanceof Object[] && ((Object[]) aDump).length == 3) {

            final Object[] dump = (Object[]) aDump;
            final String host = (String) dump[0];
            final int port = (Integer) dump[1];
            final String path = (String) dump[2];
            return new HTTPAccess(host, port, path);
        }

        // Unreadable content
        return null;
    }

    /** The host name */
    private final String pHost;

    /** Path to the Herald servlet */
    private final String pPath;

    /** HTTP server port */
    private final int pPort;

    /**
     * Sets up the access
     *
     * @param aHost
     *            HTTP server host
     * @param aPort
     *            HTTP server port
     * @param aServlet
     *            Path to the Herald service
     */
    public HTTPAccess(final String aHost, final int aPort, final String aPath) {

        pHost = aHost;
        pPort = aPort;

        if (!aPath.startsWith("/")) {
            pPath = "/" + aPath;
        } else {
            pPath = aPath;
        }
    }

    /*
     * (non-Javadoc)
     *
     * @see java.lang.Comparable#compareTo(java.lang.Object)
     */
    @Override
    public int compareTo(final Access aOther) {

        if (aOther instanceof HTTPAccess) {
            // Compare on forged URL
            return toString().compareTo(aOther.toString());
        }

        // Can't compare
        return 0;
    }

    /*
     * (non-Javadoc)
     *
     * @see org.cohorte.herald.Access#dump()
     */
    @Override
    public Object dump() {

        return new Object[] { pHost, pPort, pPath };
    }

    /*
     * (non-Javadoc)
     *
     * @see java.lang.Object#equals(java.lang.Object)
     */
    @Override
    public boolean equals(final Object aObj) {

        if (aObj instanceof HTTPAccess) {
            final HTTPAccess other = (HTTPAccess) aObj;
            return pHost.equals(other.pHost) && pPort == other.pPort;
        }

        return false;
    }

    /*
     * (non-Javadoc)
     *
     * @see org.cohorte.herald.Access#getAccessId()
     */
    @Override
    public String getAccessId() {

        return IHttpConstants.ACCESS_ID;
    }

    /**
     * Retrieves the host address of the associated peer
     *
     * @return the host
     */
    public String getHost() {

        return pHost;
    }

    /**
     * Retrieves the path to the Herald service. The returned path always has a
     * starting slash.
     *
     * @return the path
     */
    public String getPath() {

        return pPath;
    }

    /**
     * Retrieves the host port of the associated peer
     *
     * @return the port
     */
    public int getPort() {

        return pPort;
    }

    /*
     * (non-Javadoc)
     *
     * @see java.lang.Object#hashCode()
     */
    @Override
    public int hashCode() {

        // Hash code is based on string representation
        return toString().hashCode();
    }

    /*
     * (non-Javadoc)
     *
     * @see java.lang.Object#toString()
     */
    @Override
    public String toString() {

        return "http://" + pHost + ":" + pPort + pPath;
    }
}
