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

package org.cohorte.herald.rpc;

/**
 * Herald RPC constants definition
 *
 * @author Thomas Calmant
 */
public interface IHeraldRpcConstants {

    /** The exported configuration : herald-jabsorbrpc */
    String EXPORT_CONFIG = "herald-jabsorbrpc";

    /** UID of the peer exporting a service */
    String PROP_HERALDRPC_PEER = "herald.rpc.peer";

    /** Subject to contact the exporter */
    String PROP_HERALDRPC_SUBJECT = "herald.rpc.subject";

    /** Subject to use for replies */
    String SUBJECT_REPLY = "herald/rpc/jabsorbrpc/reply";

    /** Subject to use for requests */
    String SUBJECT_REQUEST = "herald/rpc/jabsorbrpc";
}
