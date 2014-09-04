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

package org.cohorte.herald;

/**
 * Abstract class representing the description of an access to a peer
 *
 * @author Thomas Calmant
 */
public abstract class Access implements Comparable<Access> {

    /**
     * Dumps the content of the access to an easily convertible type (Map,
     * String, Integer, ...)
     *
     * @return The primitive representation of the bean
     */
    public abstract Object dump();

    /*
     * (non-Javadoc)
     * 
     * @see java.lang.Object#equals(java.lang.Object)
     */
    @Override
    public abstract boolean equals(final Object aObj);

    /**
     * Returns the access ID associated to this kind of access
     *
     * @return An access ID
     */
    public abstract String getAccessId();

    /*
     * (non-Javadoc)
     * 
     * @see java.lang.Object#hashCode()
     */
    @Override
    public abstract int hashCode();
}
