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

package org.cohorte.herald.xmpp.impl;

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
import org.cohorte.herald.UnknownPeer;
import org.cohorte.herald.xmpp.IXmppConstants;
import org.cohorte.herald.xmpp.IXmppDirectory;
import org.cohorte.herald.xmpp.XmppAccess;
import org.xmpp.Jid;

/**
 * Herald XMPP transport directory
 *
 * @author Thomas Calmant
 */
@Component
@Provides(specifications = { ITransportDirectory.class, IXmppDirectory.class })
@Instantiate(name = "herald-xmpp-directory")
public class XmppDirectory implements ITransportDirectory, IXmppDirectory {

    /** The access ID property */
    @ServiceProperty(name = IConstants.PROP_ACCESS_ID,
            value = IXmppConstants.ACCESS_ID)
    private String pAccessId;

    /** The Herald core directory */
    @Requires
    private IDirectory pDirectory;

    /** Group name -&gt; MUC room JID */
    private final Map<String, Jid> pGroups = new LinkedHashMap<>();

    /** JID -&gt; Peer */
    private final Map<Jid, Peer> pJidPeer = new LinkedHashMap<>();

    /*
     * (non-Javadoc)
     *
     * @see org.cohorte.herald.xmpp.IXmppDirectory#fromJID(org.xmpp.Jid)
     */
    @Override
    public Peer fromJID(final Jid aJid) throws UnknownPeer {

        try {
            final Peer peer = pJidPeer.get(aJid);
            if (peer == null) {
                throw new UnknownPeer("XMPP:" + aJid);
            }

        } catch (final IllegalArgumentException ex) {
            throw new UnknownPeer("XMPP:" + aJid);
        }

        return null;
    }

    /**
     * Component invalidated
     */
    @Invalidate
    public void invalidate() {

        // Clean up
        pJidPeer.clear();
        pGroups.clear();
    }

    /*
     * (non-Javadoc)
     *
     * @see org.cohorte.herald.ITransportDirectory#loadAccess(java.lang.Object)
     */
    @Override
    public Access loadAccess(final Object aData) {

        return XmppAccess.load(aData);
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

        if (aData instanceof XmppAccess && !aPeer.isLocal()) {
            pJidPeer.put(((XmppAccess) aData).getJid(), aPeer);
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

        if (aData instanceof XmppAccess) {
            pJidPeer.remove(((XmppAccess) aData).getJid());
        }
    }

    /**
     * Component validated
     */
    @Validate
    public void validate() {

        // Early clean up
        pJidPeer.clear();
        pGroups.clear();
    }
}
