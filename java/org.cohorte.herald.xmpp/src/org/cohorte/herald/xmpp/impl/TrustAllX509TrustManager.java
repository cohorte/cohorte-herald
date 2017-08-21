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

package org.cohorte.herald.xmpp.impl;

import java.security.cert.CertificateException;
import java.security.cert.X509Certificate;

import javax.net.ssl.X509TrustManager;

/**
 * A "Trust" manager, which trusts any given certificate.
 *
 * See http://stackoverflow.com/questions/19723415/java-overriding-function-to-
 * disable-ssl-certificate-check
 *
 * @author Thomas Calmant
 */
public class TrustAllX509TrustManager implements X509TrustManager {

    /*
     * (non-Javadoc)
     *
     * @see
     * javax.net.ssl.X509TrustManager#checkClientTrusted(java.security.cert.
     * X509Certificate[], java.lang.String)
     */
    @Override
    public void checkClientTrusted(final X509Certificate[] aChain,
            final String aAuthType) throws CertificateException {

    }

    /*
     * (non-Javadoc)
     *
     * @see
     * javax.net.ssl.X509TrustManager#checkServerTrusted(java.security.cert.
     * X509Certificate[], java.lang.String)
     */
    @Override
    public void checkServerTrusted(final X509Certificate[] aChain,
            final String aAuthType) throws CertificateException {

    }

    /*
     * (non-Javadoc)
     *
     * @see javax.net.ssl.X509TrustManager#getAcceptedIssuers()
     */
    @Override
    public X509Certificate[] getAcceptedIssuers() {

        return new X509Certificate[0];
    }
}
