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

import java.util.LinkedHashMap;
import java.util.Map;
import java.util.UUID;

import org.apache.felix.ipojo.annotations.Component;
import org.apache.felix.ipojo.annotations.Instantiate;
import org.apache.felix.ipojo.annotations.Invalidate;
import org.apache.felix.ipojo.annotations.Provides;
import org.apache.felix.ipojo.annotations.Requires;
import org.apache.felix.ipojo.annotations.ServiceProperty;
import org.apache.felix.ipojo.annotations.Validate;
import org.cohorte.herald.HeraldException;
import org.cohorte.herald.IConstants;
import org.cohorte.herald.IDirectory;
import org.cohorte.herald.IHerald;
import org.cohorte.herald.IMessageListener;
import org.cohorte.herald.MessageReceived;
import org.cohorte.remote.ExportEndpoint;
import org.cohorte.remote.IServiceExporter;
import org.jabsorb.ng.JSONRPCBridge;
import org.jabsorb.ng.JSONRPCResult;
import org.json.JSONException;
import org.json.JSONObject;
import org.osgi.framework.BundleContext;
import org.osgi.framework.BundleException;
import org.osgi.framework.Constants;
import org.osgi.framework.ServiceReference;
import org.osgi.service.log.LogService;

/**
 * Implementation of a Cohorte Remote Services exporter, based on Herald
 *
 * @author Thomas Calmant
 */
@Component
@Provides(specifications = { IServiceExporter.class, IMessageListener.class })
@Instantiate(name = "herald-rpc-exporter")
public class HeraldRpcExporter implements IServiceExporter, IMessageListener {

    /** Supported export configurations */
    @ServiceProperty(name = Constants.REMOTE_CONFIGS_SUPPORTED, value = "{"
            + IHeraldRpcConstants.EXPORT_CONFIG + "}")
    private String[] pConfigurations;

    /** The bundle context */
    private final BundleContext pContext;

    /** The Herald core directory */
    @Requires
    private IDirectory pDirectory;

    /** Exported services: Name -&gt; ExportEndpoint */
    private final Map<String, ExportEndpoint> pEndpoints = new LinkedHashMap<String, ExportEndpoint>();

    /** Herald message filters */
    @ServiceProperty(name = IConstants.PROP_FILTERS, value = "{"
            + IHeraldRpcConstants.SUBJECT_REQUEST + ","
            + IHeraldRpcConstants.SUBJECT_REPLY + "}")
    private String[] pFilters;

    /** The JSON-RPC bridge (Jabsorb) */
    private JSONRPCBridge pJsonRpcBridge;

    /** Local peer UID */
    private String pLocalUid;

    /** The logger */
    @Requires(optional = true)
    private LogService pLogger;

    /**
     * Sets up the component
     *
     * @param aContext
     *            The bundle context
     */
    public HeraldRpcExporter(final BundleContext aContext) {

        pContext = aContext;
    }

    /*
     * (non-Javadoc)
     *
     * @see
     * org.cohorte.remote.IServiceExporter#exportService(org.osgi.framework.
     * ServiceReference, java.lang.String, java.lang.String)
     */
    @Override
    public ExportEndpoint exportService(final ServiceReference<?> aReference,
            final String aName, final String aFramworkUid)
            throws BundleException, IllegalArgumentException {

        if (pEndpoints.containsKey(aName)) {
            pLogger.log(LogService.LOG_ERROR,
                    "Already use Herald-RPC endpoint name: " + aName);
            return null;
        }

        // Get the service
        final Object service = pContext.getService(aReference);

        // Prepare extra properties
        final Map<String, Object> extraProps = new LinkedHashMap<String, Object>();
        extraProps.put(IHeraldRpcConstants.PROP_HERALDRPC_PEER, pLocalUid);
        extraProps.put(IHeraldRpcConstants.PROP_HERALDRPC_SUBJECT,
                IHeraldRpcConstants.SUBJECT_REQUEST);

        // Prepare the endpoint bean
        final ExportEndpoint endpoint = new ExportEndpoint(UUID.randomUUID()
                .toString(), pLocalUid, pConfigurations, aName, aReference,
                extraProps);

        // Register the object in the Jabsorb bridge
        pJsonRpcBridge.registerObject(aName, service);

        // Store information
        pEndpoints.put(aName, endpoint);
        return endpoint;
    }

    /*
     * (non-Javadoc)
     *
     * @see org.cohorte.remote.IServiceExporter#handles(java.lang.String[])
     */
    @Override
    public boolean handles(final String[] aConfigurations) {

        if (aConfigurations == null) {
            // null = "match all"
            return true;
        }

        // Look for a match in configurations
        for (final String config : aConfigurations) {
            for (final String handledConfig : pConfigurations) {
                if (handledConfig.equals(config)) {
                    // Got a match
                    return true;
                }
            }
        }

        // No match
        return false;
    }

    /*
     * (non-Javadoc)
     *
     * @see
     * org.cohorte.herald.IMessageListener#heraldMessage(org.cohorte.herald.
     * IHerald, org.cohorte.herald.MessageReceived)
     */
    @Override
    public void heraldMessage(final IHerald aHerald,
            final MessageReceived aMessage) {

        // Check content type
        final Object rawContent = aMessage.getContent();
        if (!(rawContent instanceof String)) {
            // Didn't got a string
            pLogger.log(LogService.LOG_ERROR,
                    "Herald Jabsorb-RPC message content is not a string");
        }

        // Convert the content of the message (request map) to a JSONObject
        final JSONObject jsonReq;
        try {
            jsonReq = new JSONObject((String) rawContent);
        } catch (final JSONException ex) {
            pLogger.log(LogService.LOG_ERROR,
                    "Error parsing the Jabsorb-RPC request: " + ex, ex);
            return;
        }

        // Call the method, without context
        final JSONRPCResult result = pJsonRpcBridge
                .call(new Object[0], jsonReq);

        // Convert the result as a JSON string containing the JSON object
        final String strResult = JSONObject.quote(result.toString());

        // Send the result
        try {
            aHerald.reply(aMessage, strResult,
                    IHeraldRpcConstants.SUBJECT_REPLY);

        } catch (final HeraldException ex) {
            pLogger.log(LogService.LOG_ERROR, "Error sending RPC result: " + ex);
        }
    }

    /**
     * Component invalidated
     */
    @Invalidate
    public void invalidate() {

        // Destroy end points
        final ExportEndpoint[] endpoints = pEndpoints.values().toArray(
                new ExportEndpoint[0]);
        for (final ExportEndpoint endpoint : endpoints) {
            try {
                // Release the service, unregister the endpoint
                unexportService(endpoint);

            } catch (final Exception ex) {
                // Just log the error
                pLogger.log(LogService.LOG_WARNING,
                        "Error unregistering service: " + ex, ex);
            }
        }

        // Clean up
        pLocalUid = null;
        pJsonRpcBridge = null;
    }

    /*
     * (non-Javadoc)
     *
     * @see
     * org.cohorte.remote.IServiceExporter#unexportService(org.cohorte.remote
     * .ExportEndpoint)
     */
    @Override
    public void unexportService(final ExportEndpoint aEndpoint) {

        // Pop the endpoint
        if (pEndpoints.remove(aEndpoint.getName()) != null) {
            // Destroy the endpoint
            pJsonRpcBridge.unregisterObject(aEndpoint.getName());

            // Release the service
            pContext.ungetService(aEndpoint.getReference());

        } else {
            // Unknown endpoint
            pLogger.log(LogService.LOG_WARNING, "Unknown endpoint: "
                    + aEndpoint);
        }
    }

    /*
     * (non-Javadoc)
     *
     * @see org.cohorte.remote.IServiceExporter#updateExport(org.cohorte.remote.
     * ExportEndpoint, java.lang.String, java.util.Map)
     */
    @Override
    public void updateExport(final ExportEndpoint aEndpoint,
            final String aNewName, final Map<String, Object> aOldProperties)
            throws IllegalArgumentException {

        final ExportEndpoint knownEndpoint = pEndpoints.get(aNewName);
        if (knownEndpoint != null && !knownEndpoint.equals(aEndpoint)) {
            // Name already taken by another endpoint: reject it
            throw new IllegalArgumentException("New name of " + aEndpoint
                    + " is already in use: " + aNewName);
        }

        // Update storage
        pEndpoints.put(aNewName, pEndpoints.remove(aEndpoint.getName()));

        // Update the endpoint
        aEndpoint.setName(aNewName);
    }

    /**
     * Component validated
     */
    @Validate
    public void validate() {

        pLocalUid = pDirectory.getLocalUid();
        pJsonRpcBridge = new JSONRPCBridge();
    }
}
