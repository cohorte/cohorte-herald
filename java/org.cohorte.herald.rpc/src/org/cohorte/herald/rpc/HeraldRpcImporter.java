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

import java.util.Arrays;
import java.util.Hashtable;
import java.util.LinkedHashMap;
import java.util.LinkedList;
import java.util.List;
import java.util.Map;

import org.apache.felix.ipojo.annotations.Component;
import org.apache.felix.ipojo.annotations.Instantiate;
import org.apache.felix.ipojo.annotations.Provides;
import org.apache.felix.ipojo.annotations.Requires;
import org.apache.felix.ipojo.annotations.ServiceProperty;
import org.cohorte.herald.IHerald;
import org.cohorte.remote.IImportEndpointListener;
import org.cohorte.remote.ImportEndpoint;
import org.cohorte.remote.utilities.BundleClass;
import org.cohorte.remote.utilities.BundlesClassLoader;
import org.jabsorb.ng.client.Client;
import org.osgi.framework.BundleContext;
import org.osgi.framework.Constants;
import org.osgi.framework.ServiceRegistration;
import org.osgi.service.log.LogService;

/**
 * Implementation of a Cohorte Remote Services importer, based on Herald
 *
 * @author Thomas Calmant
 */
@Component
@Provides(specifications = IImportEndpointListener.class)
@Instantiate(name = "herald-rpc-importer")
public class HeraldRpcImporter implements IImportEndpointListener {

    /** Endpoint UID -&gt; Jabsorb Client */
    private final Map<String, Client> pClients = new LinkedHashMap<>();

    /** Supported export configurations */
    @ServiceProperty(name = Constants.REMOTE_CONFIGS_SUPPORTED, value = "{"
            + IHeraldRpcConstants.EXPORT_CONFIG + "}")
    private String[] pConfigurations;

    /** The bundle context */
    private final BundleContext pContext;

    /** The Herald core service */
    @Requires
    private IHerald pHerald;

    /** The logger */
    @Requires(optional = true)
    private LogService pLogger;

    /** Endpoint UID -&gt; Service proxy */
    private final Map<String, Object> pProxies = new LinkedHashMap<>();

    /** Imported services: Endpoint UID -&gt; ServiceRegistration */
    private final Map<String, ServiceRegistration<?>> pRegistrations = new LinkedHashMap<>();

    /**
     * Component constructed
     *
     * @param aContext
     *            The bundle context
     */
    public HeraldRpcImporter(final BundleContext aContext) {

        pContext = aContext;
    }

    /*
     * (non-Javadoc)
     * 
     * @see
     * org.cohorte.remote.IImportEndpointListener#endpointAdded(org.cohorte.
     * remote.ImportEndpoint)
     */
    @Override
    public synchronized void endpointAdded(final ImportEndpoint aEndpoint) {

        // Check if the export configurations match a known one
        boolean supportedConfig = false;
        final String[] configurations = aEndpoint.getConfigurations();
        for (final String config : configurations) {
            for (final String handledConfig : pConfigurations) {
                if (handledConfig.equals(config)) {
                    supportedConfig = true;
                    break;
                }
            }
        }
        if (!supportedConfig) {
            // Unknown export configuration, ignore
            return;
        }

        // Check if endpoint is known
        if (pRegistrations.containsKey(aEndpoint.getUid())) {
            return;
        }

        // Extract properties
        final String peerUid = (String) aEndpoint.getProperties().get(
                IHeraldRpcConstants.PROP_HERALDRPC_PEER);
        if (peerUid == null || peerUid.isEmpty()) {
            pLogger.log(LogService.LOG_ERROR, "No peer UID found in properties");
            return;
        }

        final String subject = (String) aEndpoint.getProperties().get(
                IHeraldRpcConstants.PROP_HERALDRPC_SUBJECT);
        if (subject == null || subject.isEmpty()) {
            pLogger.log(LogService.LOG_ERROR,
                    "No Herald subject found in properties");
            return;
        }

        // Prepare a bundle class loader
        final BundlesClassLoader classLoader = new BundlesClassLoader(pContext);

        // Load interface classes
        final Class<?>[] classes;
        try {
            classes = loadInterfaces(aEndpoint.getSpecifications());

        } catch (final ClassNotFoundException ex) {
            pLogger.log(LogService.LOG_ERROR,
                    "No specification class could be loaded: " + ex, ex);
            return;
        }

        // Prepare the client and the proxy
        final Client client = new Client(new ClientSession(pHerald, peerUid,
                subject));
        final Object service = client.openProxy(aEndpoint.getName(),
                classLoader, classes);

        // Register the service
        final ServiceRegistration<?> svcReg = pContext.registerService(
                aEndpoint.getSpecifications(), service,
                new Hashtable<String, Object>(aEndpoint.getProperties()));

        // Store references
        pClients.put(aEndpoint.getUid(), client);
        pProxies.put(aEndpoint.getUid(), service);
        pRegistrations.put(aEndpoint.getUid(), svcReg);
    }

    /*
     * (non-Javadoc)
     * 
     * @see
     * org.cohorte.remote.IImportEndpointListener#endpointRemoved(org.cohorte
     * .remote.ImportEndpoint)
     */
    @Override
    public synchronized void endpointRemoved(final ImportEndpoint aEndpoint) {

        final String uid = aEndpoint.getUid();
        final ServiceRegistration<?> svcReg = pRegistrations.remove(uid);
        if (svcReg == null) {
            // Unknown endpoint
            pLogger.log(LogService.LOG_DEBUG, "Unknown endpoint: " + uid);
            return;
        }
        svcReg.unregister();

        // Clean up storage
        pClients.remove(uid).closeProxy(pProxies.remove(uid));
    }

    /*
     * (non-Javadoc)
     * 
     * @see
     * org.cohorte.remote.IImportEndpointListener#endpointUpdated(org.cohorte
     * .remote.ImportEndpoint, java.util.Map)
     */
    @Override
    public synchronized void endpointUpdated(final ImportEndpoint aEndpoint,
            final Map<String, Object> aOldProperties) {

        final ServiceRegistration<?> svcReg = pRegistrations.get(aEndpoint
                .getUid());
        if (svcReg == null) {
            // Unknown endpoint
            return;
        }

        // Update service properties
        svcReg.setProperties(new Hashtable<String, Object>(aEndpoint
                .getProperties()));
    }

    /**
     * Tries to load remote service interfaces
     *
     * @param aSpecifications
     *            Remote service interfaces
     * @return An array of interfaces classes, or null
     * @throws ClassNotFoundException
     *             No specification class found
     */
    private Class<?>[] loadInterfaces(final String[] aSpecifications)
            throws ClassNotFoundException {

        // Invalid parameter
        if (aSpecifications == null || aSpecifications.length == 0) {
            pLogger.log(LogService.LOG_ERROR, "No/Empty interface list");
            return null;
        }

        // Keep track of unknown classes
        final List<String> unknownClasses = new LinkedList<String>();

        // Find all accessible classes
        final List<Class<?>> classes = new LinkedList<Class<?>>();
        for (final String interfaceName : aSpecifications) {
            if (interfaceName == null || interfaceName.isEmpty()) {
                // Invalid interface name
                continue;
            }

            // Finding the class using Class.forName(interfaceName) won't work.
            // Only look into active bundles (not resolved ones)
            final BundleClass foundClass = BundleClass.findClassInBundles(
                    pContext.getBundles(), interfaceName, false);
            if (foundClass != null) {
                // Found an interface
                final Class<?> interfaceClass = foundClass.getLoadedClass();
                classes.add(interfaceClass);

            } else {
                // Unknown class name
                unknownClasses.add(interfaceName);
            }
        }

        // No interface found at all
        if (classes.isEmpty()) {
            final String specificationsString = Arrays
                    .toString(aSpecifications);
            pLogger.log(LogService.LOG_ERROR, "No interface found in: "
                    + specificationsString);
            throw new ClassNotFoundException(specificationsString);
        }

        // Some interfaces are missing
        if (!unknownClasses.isEmpty()) {
            pLogger.log(LogService.LOG_WARNING, "Some interfaces are missing: "
                    + unknownClasses);
        }

        // Return the classes array
        return classes.toArray(new Class<?>[0]);
    }
}
