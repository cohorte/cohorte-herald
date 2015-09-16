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

import java.util.ArrayList;
import java.util.Collection;
import java.util.HashMap;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.LinkedList;
import java.util.List;
import java.util.Map;
import java.util.Map.Entry;
import java.util.Set;

import org.apache.felix.ipojo.annotations.Component;
import org.apache.felix.ipojo.annotations.Instantiate;
import org.apache.felix.ipojo.annotations.Provides;
import org.apache.felix.ipojo.annotations.Requires;
import org.apache.felix.ipojo.annotations.ServiceProperty;
import org.cohorte.herald.Access;
import org.cohorte.herald.HeraldException;
import org.cohorte.herald.IConstants;
import org.cohorte.herald.IDirectory;
import org.cohorte.herald.IDirectoryListener;
import org.cohorte.herald.IHerald;
import org.cohorte.herald.IMessageListener;
import org.cohorte.herald.Message;
import org.cohorte.herald.MessageReceived;
import org.cohorte.herald.NoTransport;
import org.cohorte.herald.Peer;
import org.cohorte.herald.UnknownPeer;
import org.cohorte.remote.ExportEndpoint;
import org.cohorte.remote.IExportEndpointListener;
import org.cohorte.remote.IExportsDispatcher;
import org.cohorte.remote.IImportsRegistry;
import org.cohorte.remote.ImportEndpoint;
import org.osgi.service.log.LogService;

/**
 * Remote services discovery and notification, using Herald
 *
 * @author Thomas Calmant
 */
@Component
@Provides(specifications = { IMessageListener.class, IDirectoryListener.class,
		IExportEndpointListener.class })
@Instantiate(name = "herald-rpc-discovery")
public class HeraldDiscovery implements IMessageListener, IDirectoryListener,
		IExportEndpointListener {

	/** Default name of group to whom a discovery message is sent */
	private static final String DEFAULT_TARGET_GROUP = "all";

	/** Prefix to discovery subjects */
	private static final String SUBJECT_PREFIX = "herald/rpc/discovery";

	/** The Herald core directory */
	@Requires
	private IDirectory pDirectory;

	/** The remote services dispatcher */
	@Requires
	private IExportsDispatcher pDispatcher;

	/** Herald message filters */
	@ServiceProperty(name = IConstants.PROP_FILTERS, value = "{"
			+ SUBJECT_PREFIX + "/*}")
	private String[] pFilters;

	/** The herald core service */
	@Requires
	private IHerald pHerald;

	/** The logger */
	@Requires(optional = true)
	private LogService pLogger;

	/** Imported services registry */
	@Requires
	private IImportsRegistry pRegistry;

	/**
	 * Converts an ExportEndpoint bean to a map
	 *
	 * @param aEndpoint
	 *            The bean to convert
	 * @return The map describing the bean
	 */
	private Map<String, Object> dumpEndpoint(final ExportEndpoint aEndpoint) {

		final Map<String, Object> dump = new LinkedHashMap<>();

		// Copy some values as is
		dump.put("uid", aEndpoint.getUid());
		dump.put("configurations", aEndpoint.getConfigurations());
		dump.put("name", aEndpoint.getName());
		dump.put("specifications", aEndpoint.getExportedSpecs());

		// Send import-side properties
		dump.put("properties", aEndpoint.makeImportProperties());
		dump.put("peer", pDirectory.getLocalUid());
		return dump;
	}

	/**
	 * Converts a list of ExportEndpoint beans to a list of dictionaries
	 *
	 * @param aEndpoints
	 *            A list of endpoints
	 * @return A list of dictionaries
	 */
	private List<Map<String, Object>> dumpEndpoints(
			final ExportEndpoint[] aEndpoints) {

		final List<Map<String, Object>> result = new LinkedList<>();
		for (final ExportEndpoint endpoint : aEndpoints) {
			result.add(dumpEndpoint(endpoint));
		}

		return result;
	}

	/*
	 * (non-Javadoc)
	 *
	 * @see
	 * org.cohorte.remote.IExportEndpointListener#endpointRemoved(org.cohorte
	 * .remote.ExportEndpoint)
	 */
	@Override
	public void endpointRemoved(final ExportEndpoint aEndpoint) {

		final Map<String, String> content = new LinkedHashMap<>();
		content.put("uid", aEndpoint.getUid());
		final String group = getTargetGroup(aEndpoint);
		sendMessage("remove", content, group);
	}

	/*
	 * (non-Javadoc)
	 *
	 * @see
	 * org.cohorte.remote.IExportEndpointListener#endpointsAdded(org.cohorte
	 * .remote.ExportEndpoint[])
	 */
	@Override
	public void endpointsAdded(final ExportEndpoint[] aEndpoints) {
		final Map<String, Set<ExportEndpoint>> bins = new HashMap<String, Set<ExportEndpoint>>();
		for (final ExportEndpoint ep : aEndpoints) {
			final String group = getTargetGroup(ep);
			Set<ExportEndpoint> bin = bins.get(group);
			if (bin == null) {
				bin = new HashSet<ExportEndpoint>();
				bins.put(group, bin);
			}
			bin.add(ep);
		}

		for (final Entry<String, Set<ExportEndpoint>> entry : bins.entrySet()) {
			sendMessage(
					"add",
					dumpEndpoints(entry.getValue().toArray(
							new ExportEndpoint[0])), entry.getKey());
		}
	}

	/*
	 * (non-Javadoc)
	 *
	 * @see
	 * org.cohorte.remote.IExportEndpointListener#endpointUpdated(org.cohorte
	 * .remote.ExportEndpoint, java.util.Map)
	 */
	@Override
	public void endpointUpdated(final ExportEndpoint aEndpoint,
			final Map<String, Object> aOldProperties) {

		final Map<String, Object> content = new LinkedHashMap<>();
		content.put("uid", aEndpoint.getUid());
		content.put("properties", aEndpoint.makeImportProperties());
		final String group = getTargetGroup(aEndpoint);
		sendMessage("update", content, group);
	}

	/**
	 * Select endpoints relevant to a peer
	 *
	 * @param aPeer
	 *            the Peer bean
	 * @param aEndpoints
	 *            the original set of endpoints
	 * @return relevant endpoints, that is endpoints sharing the same group as
	 *         one of the peer's, or "all"
	 */
	private ExportEndpoint[] filterEndpoints(final Peer aPeer,
			final ExportEndpoint[] aEndpoints) {
		final Collection<String> groups = aPeer.getGroups();
		final List<ExportEndpoint> valid = new ArrayList<ExportEndpoint>();
		for (final ExportEndpoint ep : aEndpoints) {
			final String target_group = getTargetGroup(ep);
			if (target_group == null || groups.contains(target_group)) {
				valid.add(ep);
			}
		}

		return valid.toArray(new ExportEndpoint[0]);
	}

	/**
	 * Returns an endpoint's target group, or {@code DEFAULT_TARGET_GROUP} if no
	 * such property exists.
	 *
	 * @param ep
	 * @return
	 */
	private String getTargetGroup(final ExportEndpoint ep) {
		if (ep.getProperties().containsKey(IConstants.PROP_TARGET_GROUP)) {
			return (String) ep.getProperties()
					.get(IConstants.PROP_TARGET_GROUP);
		}
		return DEFAULT_TARGET_GROUP;
	}

	/*
	 * (non-Javadoc)
	 *
	 * @see
	 * org.cohorte.herald.IMessageListener#heraldMessage(org.cohorte.herald.
	 * IHerald, org.cohorte.herald.MessageReceived)
	 */
	@SuppressWarnings("unchecked")
	@Override
	public void heraldMessage(final IHerald aHerald,
			final MessageReceived aMessage) throws HeraldException {

		// Extra the kind of message
		final String subject = aMessage.getSubject();
		final int kindIndex = subject.lastIndexOf("/");
		final String kind = subject.substring(kindIndex + 1);

		try {
			switch (kind) {
			case "contact": {
				pLogger.log(LogService.LOG_DEBUG,
						"Contact established with peer " + aMessage.getSender()
								+ ".");

				// Register the endpoints
				registerEndpoints((List<Map<String, Object>>) aMessage
						.getContent());

				final ExportEndpoint[] endpoints = filterEndpoints(
						pDirectory.getPeer(aMessage.getSender()),
						pDispatcher.getEndpoints());

				// In case of contact: reply with our dump
				final List<Map<String, Object>> dump = dumpEndpoints(endpoints);
				aHerald.reply(aMessage, dump, SUBJECT_PREFIX + "/add");
				break;
			}

			case "add": {
				try {
					// Check if the sender is known
					pDirectory.getPeer(aMessage.getSender());

					// Peer is known: load the endpoints
					registerEndpoints((List<Map<String, Object>>) aMessage
							.getContent());
				} catch (final UnknownPeer ex) {
					// Peer is unknown: ignore the message
				}
				break;
			}

			case "remove": {
				// The message only contains the UID of the endpoint
				pRegistry.remove((String) toMap(aMessage.getContent()).get(
						"uid"));
				break;
			}

			case "update": {
				// Convert message to map
				final Map<String, Object> content = toMap(aMessage.getContent());
				final String endpointUid = (String) content.get("uid");
				final Map<String, Object> newProperties = (Map<String, Object>) content
						.get("properties");

				// Update the endpoint
				pRegistry.update(endpointUid, newProperties);
				break;
			}

			default:
				// Unknown kind
				pLogger.log(LogService.LOG_DEBUG,
						"Unknown kind of discovery event: " + kind);
				break;
			}
		} catch (final ClassCastException ex) {
			pLogger.log(LogService.LOG_ERROR, "Bad content of discovery '"
					+ kind + "': " + ex, ex);
		}
	}

	/**
	 * Loads an endpoint map generated by {@link #dumpEndpoint(ExportEndpoint)}
	 *
	 * @param aDump
	 *            The result of {@link #dumpEndpoint(ExportEndpoint)}
	 * @return The corresponding {@link ImportEndpoint} bean
	 */
	@SuppressWarnings("unchecked")
	private ImportEndpoint loadEndpoint(final Map<String, Object> aDump) {

		final String uid = (String) aDump.get("uid");
		final String name = (String) aDump.get("name");
		final String frameworkUid = (String) aDump.get("peer");
		final String[] configurations = toStringArray(aDump
				.get("configurations"));
		final String[] specs = toStringArray(aDump.get("specifications"));
		final Map<String, Object> properties = (Map<String, Object>) aDump
				.get("properties");

		return new ImportEndpoint(uid, frameworkUid, configurations, name,
				specs, properties);
	}

	/*
	 * (non-Javadoc)
	 *
	 * @see
	 * org.cohorte.herald.IDirectoryListener#peerRegistered(org.cohorte.herald
	 * .Peer)
	 */
	@Override
	public void peerRegistered(final Peer aPeer) {
		pLogger.log(LogService.LOG_DEBUG, "Registering peer " + aPeer.getName()
				+ "'s endpoints...");
		final ExportEndpoint[] endpoints = filterEndpoints(aPeer,
				pDispatcher.getEndpoints());

		sendMessage(aPeer, "contact", dumpEndpoints(endpoints));
	}

	/*
	 * (non-Javadoc)
	 *
	 * @see
	 * org.cohorte.herald.IDirectoryListener#peerUnregistered(org.cohorte.herald
	 * .Peer)
	 */
	@Override
	public void peerUnregistered(final Peer aPeer) {

		// A peer has gone away
		pRegistry.lostFramework(aPeer.getUid());
	}

	/*
	 * (non-Javadoc)
	 *
	 * @see
	 * org.cohorte.herald.IDirectoryListener#peerUpdated(org.cohorte.herald.
	 * Peer, java.lang.String, org.cohorte.herald.Access,
	 * org.cohorte.herald.Access)
	 */
	@Override
	public void peerUpdated(final Peer aPeer, final String aAccessId,
			final Access aData, final Access aPrevious) {

		// Do nothing
	}

	/**
	 * Registers a list of endpoints
	 *
	 * @param aMessageContent
	 *            A list of maps describing endpoints
	 */
	private void registerEndpoints(final List<Map<String, Object>> aEndpoints) {

		for (final Map<String, Object> endpointDict : aEndpoints) {
			final ImportEndpoint endpoint = loadEndpoint(endpointDict);
			pRegistry.add(endpoint);
		}
	}

	/**
	 * Sends a message to the given peer
	 *
	 * @param aKind
	 *            Kind of discovery message
	 * @param aData
	 *            Content of the message
	 */
	private void sendMessage(final Peer aPeer, final String aKind,
			final Object aData) {

		try {
			pHerald.fire(aPeer,
					new Message(SUBJECT_PREFIX + "/" + aKind, aData));

		} catch (final NoTransport ex) {
			pLogger.log(LogService.LOG_ERROR, "Error sending message to peer: "
					+ aPeer + ": " + ex);
		}
	}

	/**
	 * Sends a message to a group of peers
	 *
	 * @param aKind
	 *            Kind of discovery message
	 * @param aData
	 *            Content of the message
	 *
	 * @param group
	 *            Group's name
	 */
	private void sendMessage(final String aKind, final Object aData,
			final String aGroup) {

		try {
			pHerald.fireGroup(aGroup, new Message(SUBJECT_PREFIX + "/" + aKind,
					aData));

		} catch (final NoTransport ex) {
			pLogger.log(LogService.LOG_ERROR,
					"Error sending message to other peers: " + ex);
		}
	}

	/**
	 * Casts the given object to a map, if possible
	 *
	 * @param aObject
	 *            The object to cast
	 * @return The object, casted as a map
	 * @throws ClassCastException
	 *             The object is not a map
	 */
	@SuppressWarnings("unchecked")
	private Map<String, Object> toMap(final Object aObject)
			throws ClassCastException {

		return (Map<String, Object>) aObject;
	}

	/**
	 * Converts the given object to an array of strings
	 *
	 * @param aData
	 *            Object to convert
	 * @return A string array, or null
	 * @throws ClassCastException
	 *             Can't convert the object
	 */
	private String[] toStringArray(final Object aData) {

		if (aData instanceof String[]) {
			// Nothing to do
			return (String[]) aData;

		} else if (aData instanceof Object[]) {
			// Simply convert the array
			final Object[] source = (Object[]) aData;
			final String[] result = new String[source.length];
			for (int i = 0; i < source.length; i++) {
				result[i] = (String) source[i];
			}
			return result;

		} else if (aData instanceof Collection) {
			// Cast all elements of the collection
			final Collection<?> source = (Collection<?>) aData;
			final String[] result = new String[source.size()];
			int i = 0;
			for (final Object data : source) {
				result[i++] = (String) data;
			}
			return result;

		} else if (aData == null) {
			// Keep null as is
			return null;
		} else {
			// Unknown: let Java try to do the job
			return (String[]) aData;
		}

	}
}
