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
 * Specifies a delayed peer registration notification class
 *
 * @author Thomas Calmant
 */
public interface IDelayedNotification {

    /**
     * Returns the peer being registered
     *
     * @return the peer being registered
     */
    Peer getPeer();

    /**
     * Notifies listeners about the registration of the peer. Does nothing if
     * the peer was already registered.
     *
     * @return True if the listeners have been notified, else false
     */
    boolean notifyListeners();
}
