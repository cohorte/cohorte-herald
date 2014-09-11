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

import java.util.LinkedHashMap;
import java.util.Map;

import org.apache.felix.ipojo.annotations.Component;
import org.apache.felix.ipojo.annotations.Instantiate;
import org.apache.felix.ipojo.annotations.Invalidate;
import org.apache.felix.ipojo.annotations.Provides;
import org.apache.felix.ipojo.annotations.Requires;
import org.apache.felix.ipojo.annotations.ServiceProperty;
import org.apache.felix.ipojo.annotations.Validate;
import org.cohorte.herald.Access;
import org.cohorte.herald.IConstants;
import org.cohorte.herald.IDirectory;
import org.cohorte.herald.ITransportDirectory;
import org.cohorte.herald.Peer;
import org.cohorte.herald.exceptions.ValueError;
import org.cohorte.herald.http.HTTPAccess;
import org.cohorte.herald.http.IHttpConstants;

/**
 * HTTP Directory for Herald
 *
 * @author Thomas Calmant
 */
@Component
@Provides(specifications = IHttpDirectory.class)
@Instantiate(name = "herald-http-directory")
public class HttpDirectory implements ITransportDirectory, IHttpDirectory {

    /** Access ID property */
    @ServiceProperty(name = IConstants.PROP_ACCESS_ID,
            value = IHttpConstants.ACCESS_ID)
    private String pAccessId;

    /** Herald core directory */
    @Requires
    private IDirectory pDirectory;

    /** Peer UID -&gt; Peer access */
    private final Map<String, HTTPAccess> pUidAddress = new LinkedHashMap<>();

    /*
     * (non-Javadoc)
     *
     * @see
     * org.cohorte.herald.http.impl.IHttpDirectory#checkAccess(java.lang.String,
     * java.lang.String, int)
     */
    @Override
    public boolean checkAccess(final String aPeerUid, final String aHost,
            final int aPort) throws ValueError {

        final HTTPAccess access = pUidAddress.get(aPeerUid);
        if (access == null) {
            throw new ValueError("Unknown peer: " + aPeerUid);
        }

        if (access.getPort() == aPort) {
            // Validation is based upon the port only (to avoid IPv4/v6
            // differences)
            return true;
        }

        // Invalid port
        throw new ValueError("Given port (" + aPort + ") doesn't match peer "
                + aPeerUid + " (" + access.getPort() + ")");
    }

    /**
     * Component invalidated
     */
    @Invalidate
    public void invalidate() {

        // Clean up
        pUidAddress.clear();
    }

    /*
     * (non-Javadoc)
     *
     * @see org.cohorte.herald.ITransportDirectory#loadAccess(java.lang.Object)
     */
    @Override
    public Access loadAccess(final Object aData) {

        return HTTPAccess.load(aData);
    }

    /*
     * (non-Javadoc)
     *
     * @see
     * org.cohorte.herald.ITransportDirectory#peerAccessSet(org.cohorte.herald
     * .Peer, org.cohorte.herald.Access)
     */
    @Override
    public void peerAccessSet(final Peer aPeer, final Access aData) {

        if (!aPeer.equals(pDirectory.getLocalPeer())
                && aData instanceof HTTPAccess) {
            pUidAddress.put(aPeer.getUid(), (HTTPAccess) aData);
        }
    }

    /*
     * (non-Javadoc)
     *
     * @see
     * org.cohorte.herald.ITransportDirectory#peerAccessUnset(org.cohorte.herald
     * .Peer, org.cohorte.herald.Access)
     */
    @Override
    public void peerAccessUnset(final Peer aPeer, final Access aData) {

        pUidAddress.remove(aPeer.getUid());
    }

    /**
     * Component validated
     */
    @Validate
    public void validate() {

        pUidAddress.clear();
    }
}
