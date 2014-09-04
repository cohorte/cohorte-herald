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

package org.cohorte.herald.exceptions;

import org.cohorte.herald.Target;

/**
 * Base class for all exceptions in Herald
 *
 * @author Thomas Calmant
 */
public class HeraldException extends Exception {

    /** Serialization version UID */
    private static final long serialVersionUID = 1L;

    /** Targeted peer(s) */
    private final Target pTarget;

    /**
     * Sets up the exception
     *
     * @param aTarget
     *            Targeted peer(s)
     * @param aText
     *            Description of the error
     * @param aCause
     *            Cause of the error
     */
    public HeraldException(final Target aTarget, final String aText) {

        this(aTarget, aText, null);
    }

    /**
     * Sets up the exception
     *
     * @param aTarget
     *            Targeted peer(s)
     * @param aText
     *            Description of the error
     * @param aCause
     *            Cause of the error
     */
    public HeraldException(final Target aTarget, final String aText,
            final Throwable aCause) {

        super(aText, aCause);
        pTarget = aTarget;
    }

    /**
     * @return the targeted peer(s) or null
     */
    public Target getTarget() {

        return pTarget;
    }
}
