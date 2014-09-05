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

import java.util.Collection;

import org.apache.felix.ipojo.annotations.Component;
import org.apache.felix.ipojo.annotations.Instantiate;
import org.apache.felix.ipojo.annotations.Provides;
import org.apache.felix.ipojo.annotations.Requires;
import org.apache.felix.ipojo.annotations.ServiceController;
import org.apache.felix.ipojo.annotations.ServiceProperty;
import org.cohorte.herald.IConstants;
import org.cohorte.herald.IDirectory;
import org.cohorte.herald.IHeraldInternal;
import org.cohorte.herald.ITransport;
import org.cohorte.herald.Message;
import org.cohorte.herald.Peer;
import org.cohorte.herald.exceptions.HeraldException;
import org.cohorte.herald.http.IHttpConstants;

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
    @ServiceProperty(name = IConstants.PROP_ACCESS_ID,
            value = IHttpConstants.ACCESS_ID)
    private String pAccessId;

    /** Service controller */
    @ServiceController(value = false)
    private boolean pController;

    /** Herald core directory */
    @Requires
    private IDirectory pDirectory;

    /** Herald core service (internal: always on) */
    @Requires
    private IHeraldInternal pHerald;

    /** HTTP directory */
    @Requires
    private IHttpDirectory pHttpDirectory;

    /** HTTP Reception component */
    @Requires
    private IHttpReceiver pReceiver;

    /*
     * (non-Javadoc)
     * 
     * @see org.cohorte.herald.ITransport#fire(org.cohorte.herald.Peer,
     * org.cohorte.herald.Message)
     */
    @Override
    public void fire(final Peer aPeer, final Message aMessage)
            throws HeraldException {

        // TODO Auto-generated method stub

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

        // TODO Auto-generated method stub

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

        // TODO Auto-generated method stub
        return null;
    }

}
