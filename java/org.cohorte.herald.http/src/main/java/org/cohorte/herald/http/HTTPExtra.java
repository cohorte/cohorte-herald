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
 * Stores extra information for HTTP replies
 *
 * @author Thomas Calmant
 */
public class HTTPExtra {

    /** Sender host */
    private final String pHost;

    /** UID of the message we reply to */
    private final String pParentUid;

    /** Path to the sender's servlet */
    private final String pPath;

    /** Sender HTTP port */
    private final int pPort;

    /**
     * Sets up the bean
     */
    public HTTPExtra(final String aHost, final int aPort, final String aPath,
            final String aParentUid) {

        pHost = aHost;
        pPort = aPort;
        pPath = aPath;
        pParentUid = aParentUid;
    }

    /**
     * @return the host
     */
    public String getHost() {

        return pHost;
    }

    /**
     * @return the parentUid
     */
    public String getParentUid() {

        return pParentUid;
    }

    /**
     * @return the path
     */
    public String getPath() {

        return pPath;
    }

    /**
     * @return the port
     */
    public int getPort() {

        return pPort;
    }
}
