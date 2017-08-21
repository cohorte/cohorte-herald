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
package org.cohorte.herald.http.discovery;

import java.util.Dictionary;
import java.util.Hashtable;

import org.apache.felix.ipojo.ComponentInstance;
import org.apache.felix.ipojo.ConfigurationException;
import org.apache.felix.ipojo.Factory;
import org.apache.felix.ipojo.InstanceManager;
import org.apache.felix.ipojo.MissingHandlerException;
import org.apache.felix.ipojo.UnacceptableConfiguration;
import org.apache.felix.ipojo.annotations.Component;
import org.apache.felix.ipojo.annotations.Invalidate;
import org.apache.felix.ipojo.annotations.Requires;
import org.apache.felix.ipojo.annotations.Validate;
import org.cohorte.herald.http.IHttpConstants;
import org.osgi.framework.BundleContext;
import org.osgi.service.log.LogService;

/**
 * Multicast broadcaster component instantiation helper
 *
 * @author Thomas Calmant
 * 
 * MOD_BD_20160914 remove @Instanciate as this component is now only created when using http transport, 
 * 					not when we have local discovery.
 */
@Component(name= "herald-http-discovery-multicast-starter-factory")
public class MulticastStarter {

    /**
     * Default multicast group: IPv4 site multicast
     *
     * @see http://en.wikipedia.org/wiki/Multicast
     */
    private static final String DEFAULT_GROUP = "239.0.0.1";

    /**
     * Default component instance name
     */
    private static final String DEFAULT_NAME = "herald-http-discovery-multicast";

    /**
     * Default listening port (must be opened in firewall, UDP mode)
     */
    private static final String DEFAULT_PORT = "42000";

    /**
     * Default value for discover or not local peers 
     */
    private static final String DEFAULT_DISCOVER_LOCAL_PEERS = "false";
    
    /**
     * Multicast group component property
     */
    private static final String PROP_GROUP = "multicast.group";

    /**
     * Multicast port component property
     */
    private static final String PROP_PORT = "multicast.port";

    /**
     * Discover or not local peers (of the same node)
     */
    private static final String PROP_DISCOVER_LOCAL_PEERS = "discover.local.peers";
    
    /**
     * Multicast group system property
     */
    private static final String SYSPROP_GROUP = "herald.multicast.group";

    /**
     * Component name system property
     */
    private static final String SYSPROP_NAME = "herald.multicast.component.name";

    /**
     * Multicast port system property
     */
    private static final String SYSPROP_PORT = "herald.multicast.port";
    
    /**
     * Discover local peers system property
     */
    private static final String SYSPROP_DISCOVER_LOCAL_PEERS = "herald.discover.local.peers";

    /** The bundle context, to access framework properties */
    private final BundleContext pContext;

    /** The multicast component instance */
    private ComponentInstance pInstance;

    /** The logger */
    @Requires(optional = true)
    private LogService pLogger;

    /** The multicast component factory */
    @Requires(filter = "(factory.name="
            + IHttpConstants.FACTORY_DISCOVERY_MULTICAST + ")")
    private Factory pMulticastFactory;

    /**
     * Sets up members
     *
     * @param aContext
     *            The bundle context
     */
    public MulticastStarter(final BundleContext aContext) {

        pContext = aContext;
    }

    /**
     * Gets a bundle context / system / default property
     *
     * @param aKey
     *            Property name
     * @param aDefault
     *            Value to return if absent of context and system properties
     * @return The found / default value
     */
    private String getProperty(final String aKey, final String aDefault) {

        String value = pContext.getProperty(aKey);
        if (value == null) {
            // In Equinox, we also have to check system properties
            value = System.getProperty(aKey);
        }

        if (value == null) {
            // No value found
            return aDefault;
        }

        return value;
    }

    /**
     * Component gone
     */
    @Invalidate
    public void invalidate() {

        // Kill'em all
        stopComponent();
    }

    /**
     * Starts the multicast broadcaster iPOJO component according to system
     * properties
     */
    private void startComponent() {

        if (pInstance != null) {
            pLogger.log(LogService.LOG_ERROR, "Can't run component twice");
            return;
        }

        // Set up properties
        final Dictionary<String, String> props = new Hashtable<>();
        props.put(Factory.INSTANCE_NAME_PROPERTY,
                getProperty(SYSPROP_NAME, DEFAULT_NAME));
        props.put(PROP_GROUP, getProperty(SYSPROP_GROUP, DEFAULT_GROUP));
        props.put(PROP_PORT, getProperty(SYSPROP_PORT, DEFAULT_PORT));
        props.put(PROP_DISCOVER_LOCAL_PEERS, 
        		getProperty(SYSPROP_DISCOVER_LOCAL_PEERS, DEFAULT_DISCOVER_LOCAL_PEERS));
        try {
            // Create the instance
            pInstance = pMulticastFactory.createComponentInstance(props);

            String logStr = "Herald Multicast discovery instantiated: "
                    + pInstance;
            if (pInstance instanceof InstanceManager) {
                // Try to grab more details
                final InstanceManager instMan = (InstanceManager) pInstance;
                final Object realComponent = instMan.getPojoObject();
                logStr += " - " + realComponent;
            }
            pLogger.log(LogService.LOG_DEBUG, logStr);

        } catch (UnacceptableConfiguration | MissingHandlerException
                | ConfigurationException ex) {
            // What a Terrible Failure
            pLogger.log(LogService.LOG_ERROR,
                    "Multicast broadcaster instantiation error: " + ex, ex);
        }
    }

    /**
     * Kills the multicast broadcaster, if any
     */
    private void stopComponent() {

        if (pInstance == null) {
            pLogger.log(LogService.LOG_WARNING,
                    "No multicast broadcaster instantiated (nice try)");
            return;
        }

        pInstance.dispose();
        pInstance = null;
    }

    /**
     * Component validated
     */
    @Validate
    public void validate() {

        // Let's roll
        startComponent();
    }
}
