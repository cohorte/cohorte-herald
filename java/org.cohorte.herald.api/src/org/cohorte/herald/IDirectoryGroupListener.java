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
 * A listener of directory group events
 *
 * @author Thomas Calmant
 */
public interface IDirectoryGroupListener {

    /**
     * A new directory group has been added
     * 
     * @param aGroup
     *            The group name
     */
    void groupSet(String aGroup);

    /**
     * A directory group has been deleted
     * 
     * @param aGroup
     *            The group name
     */
    void groupUnset(String aGroup);
}
