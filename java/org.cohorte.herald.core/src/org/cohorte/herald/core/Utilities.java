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

package org.cohorte.herald.core;

import java.util.Map;

/**
 * Utility methods for the Herald core implementation
 *
 * @author Thomas Calmant
 */
public final class Utilities {

    /**
     * Mimics Python's map.setdefault behavior: stores the "default" value in
     * the map if the key doesn't exist
     *
     * @param aMap
     *            The map to update
     * @param aKey
     *            The key to look for
     * @param aDefault
     *            The value to store and return if the key doesn't exist
     * @return The value associated to the key, or the default one
     */
    public static <K, T, V extends T> T setDefault(final Map<K, T> aMap,
            final K aKey, final V aDefault) {

        if (!aMap.containsKey(aKey)) {
            aMap.put(aKey, aDefault);
            return aDefault;
        }

        return aMap.get(aKey);
    }

    /**
     * Hidden constructor
     */
    private Utilities() {

    }
}
