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

package org.cohorte.herald.xmpp;

import org.cohorte.herald.Access;
import org.xmpp.Jid;

/**
 * Description of the XMPP access to a peer
 *
 * @author Thomas Calmant
 */
public class XmppAccess extends Access {

    /**
     * Creates a bean from the result {@link #dump()}
     *
     * @param aDump
     *            The result of {@link #dump()}
     * @return The created bean, or null
     */
    public static XmppAccess load(final Object aDump) {

        if (aDump instanceof String) {
            try {
                // Parse the JID and prepare the bean
                final Jid jid = Jid.valueOf(aDump.toString());
                return new XmppAccess(jid);

            } catch (final IllegalArgumentException ex) {
                // Bad JID
                return null;
            }
        }

        // Unhandled kind of dump
        return null;
    }

    /** The JID of the peer */
    private final Jid pJid;

    /**
     * Stores the JID of the peer
     *
     * @param aJid
     *            A JID
     */
    public XmppAccess(final Jid aJid) {

        pJid = aJid.asBareJid();
    }

    /**
     * Compares accesses according to their JIDs
     *
     * @see Jid#compareTo(Jid)
     * @see java.lang.Comparable#compareTo(java.lang.Object)
     */
    @Override
    public int compareTo(final Access aOther) {

        if (aOther instanceof XmppAccess) {
            // Compare JIDs
            return pJid.compareTo(((XmppAccess) aOther).pJid);
        }

        // Can't compare
        return 0;
    }

    /**
     * Returns the bare JID as a string
     *
     * @see org.cohorte.herald.Access#dump()
     */
    @Override
    public Object dump() {

        return pJid.toString();
    }

    /*
     * (non-Javadoc)
     * 
     * @see java.lang.Object#equals(java.lang.Object)
     */
    @Override
    public boolean equals(final Object aObj) {

        if (aObj instanceof XmppAccess) {
            return pJid.equals(((XmppAccess) aObj).pJid);
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

        return IXmppConstants.ACCESS_ID;
    }

    /**
     * @return the jid
     */
    public Jid getJid() {

        return pJid;
    }

    /*
     * (non-Javadoc)
     *
     * @see java.lang.Object#hashCode()
     */
    @Override
    public int hashCode() {

        return pJid.hashCode();
    }

    /*
     * (non-Javadoc)
     * 
     * @see java.lang.Object#toString()
     */
    @Override
    public String toString() {

        return "XMPP:" + pJid;
    }
}
