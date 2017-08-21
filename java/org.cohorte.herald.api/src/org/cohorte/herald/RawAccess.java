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
 * Raw access storage: stores raw data as long as the access transport directory
 * is missing.
 *
 * <strong>DO NOT use for transport implementations</strong>
 *
 * @author Thomas Calmant
 */
public final class RawAccess extends Access {

    /** Access ID */
    private final String pAccessId;

    /** Raw data */
    private final Object pRawData;

    /**
     * Sets up the access
     *
     * @param aAccessId
     *            Access ID associated to the data
     * @param aRawData
     *            Raw data to store
     */
    public RawAccess(final String aAccessId, final Object aRawData) {

        pAccessId = aAccessId;
        pRawData = aRawData;
    }

    /*
     * (non-Javadoc)
     * 
     * @see java.lang.Comparable#compareTo(java.lang.Object)
     */
    @Override
    public int compareTo(final Access aOther) {

        // Can't compare raw data
        return 0;
    }

    /*
     * (non-Javadoc)
     * 
     * @see org.cohorte.herald.Access#dump()
     */
    @Override
    public Object dump() {

        // Return the raw data as is
        return pRawData;
    }

    /*
     * (non-Javadoc)
     * 
     * @see org.cohorte.herald.Access#getAccessId()
     */
    @Override
    public String getAccessId() {

        return pAccessId;
    }

    /**
     * @return the stored data
     */
    public Object getRawData() {

        return pRawData;
    }
}
