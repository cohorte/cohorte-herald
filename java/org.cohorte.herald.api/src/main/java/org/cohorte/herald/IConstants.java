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
 * Defines the constants used in Herald
 *
 * @author Thomas Calmant
 */
public interface IConstants {

    /**
     * Default application ID
     */
    String DEFAULT_APPLICATION_ID = "<herald-legacy>";

    /**
     * ID of the application the local peer is part of. Peers of other
     * applications will be ignored.
     */
    String FWPROP_APPLICATION_ID = "herald.application.id";

    /**
     * Framework property: Human-readable name of the node hosting the peer.
     * Defaults to the node UID.
     */
    String FWPROP_NODE_NAME = "herald.node.name";

    /**
     * Framework property: UID of the node hosting the peer. Defaults to the
     * peer UID.
     */
    String FWPROP_NODE_UID = "herald.node.uid";

    /**
     * Framework property: The comma-separated list of groups the peer belongs
     * to
     */
    String FWPROP_PEER_GROUPS = "herald.peer.groups";

    /**
     * Framework property: Human-readable name of the peer. Default to the peer
     * UID.
     */
    String FWPROP_PEER_NAME = "herald.peer.name";

    /**
     * Framework property: UID of the peer
     */
    String FWPROP_PEER_UID = "herald.peer.uid";

    /**
     * Unique name of the kind of access a transport implementation handles
     */
    String PROP_ACCESS_ID = "herald.access.id";

    /**
     * A set of filename patterns to filter messages
     */
    String PROP_FILTERS = "herald.filters";
}
