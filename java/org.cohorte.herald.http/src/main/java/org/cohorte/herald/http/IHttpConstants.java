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

package org.cohorte.herald.http;

/**
 * Constants used by the HTTP transport implementation
 *
 * @author Thomas Calmant
 */
public interface IHttpConstants {

    /** Access ID used by the HTTP transport implementation */
    String ACCESS_ID = "http";

    /** Name of the encoding charset */
    String CHARSET_UTF8 = "UTF-8";

    /** Name of the content type */
    String CONTENT_TYPE_JSON = "application/json";

    /** Name of the Multicast discovery component factory */
    String FACTORY_DISCOVERY_MULTICAST = "herald-http-discovery-multicast-factory";

    /** Name of the HTTP reception servlet factory */
    String FACTORY_SERVLET = "herald-http-servlet-factory";

    /** Name of the multicast group configuration property */
    String PROP_MULTICAST_GROUP = "multicast.group";

    /** Name of the multicast port configuration property */
    String PROP_MULTICAST_PORT = "multicast.port";

    /** The default/fixed path to the Herald servlet */
    String SERVLET_PATH = "/herald";
}
