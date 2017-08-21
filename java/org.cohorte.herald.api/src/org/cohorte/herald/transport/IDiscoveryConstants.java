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

package org.cohorte.herald.transport;

/**
 * Defines the Herald discovery constants
 *
 * @author Thomas Calmant
 */
public interface IDiscoveryConstants {

    /**
     * Prefix to all discovery messages
     */
    String SUBJECT_DISCOVERY_PREFIX = "herald/directory/discovery";

    /**
     * First message: Initial contact message, containing our dump
     */
    String SUBJECT_DISCOVERY_STEP_1 = SUBJECT_DISCOVERY_PREFIX + "/step1";

    /**
     * Second message: let the remote peer send its dump
     */
    String SUBJECT_DISCOVERY_STEP_2 = SUBJECT_DISCOVERY_PREFIX + "/step2";

    /**
     * Third message: the remote peer acknowledge, notify our listeners
     */
    String SUBJECT_DISCOVERY_STEP_3 = SUBJECT_DISCOVERY_PREFIX + "/step3";
}
