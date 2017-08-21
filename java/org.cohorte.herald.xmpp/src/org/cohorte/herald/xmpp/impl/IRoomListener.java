/**
 * Copyright 2015 isandlaTech
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

import rocks.xmpp.core.Jid;
import rocks.xmpp.extensions.muc.Occupant;

/**
 * Specifies a room creation and events listener
 *
 * @author Thomas Calmant
 */
public interface IRoomListener {

    /**
     * A room has been correctly created or joined
     *
     * @param aRoomJid
     *            Bare JID of the room
     * @param aNick
     *            Nick used in the room
     */
    void onRoomCreated(Jid aRoomJid, String aNick);

    /**
     * Error creating a room
     *
     * @param aRoomJid
     *            Bare JID of the room
     * @param aNick
     *            Nick used in the room
     * @param aCondition
     *            Category of error
     * @param aDescription
     *            Description of the error
     */
    void onRoomError(Jid aRoomJid, String aNick, String aCondition,
            String aDescription);

    /**
     * Someone entered a room
     *
     * @param aRoomJid
     *            The JID of the room
     * @param aOccupant
     *            The new occupant
     */
    void onRoomIn(Jid aRoomJid, Occupant aOccupant);

    /**
     * Someone exited a room
     *
     * @param aRoomJid
     *            The JID of the room
     * @param aOccupant
     *            The occupant
     */
    void onRoomOut(Jid aRoomJid, Occupant aOccupant);
}
