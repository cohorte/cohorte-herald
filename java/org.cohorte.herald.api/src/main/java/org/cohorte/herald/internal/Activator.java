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
package org.cohorte.herald.internal;

import org.cohorte.herald.eventapi.DefaultEventFactory;
import org.cohorte.herald.eventapi.IEventFactory;
import org.osgi.framework.BundleActivator;
import org.osgi.framework.BundleContext;
import org.osgi.framework.ServiceReference;
import org.osgi.framework.ServiceRegistration;

/**
 * The Herald API bundle activator.
 *
 * Registers the default event factory, if necessary
 *
 * @author Thomas Calmant
 */
public class Activator implements BundleActivator {

	/** The service registration */
	private ServiceRegistration<IEventFactory> pRegistration;

	/*
	 * (non-Javadoc)
	 * 
	 * @see
	 * org.osgi.framework.BundleActivator#start(org.osgi.framework.BundleContext
	 * )
	 */
	@Override
	public void start(final BundleContext aContext) throws Exception {

		// Check if the service already exists
		// (provided by Cohorte, for example)
		final ServiceReference<?> svcRef = aContext
				.getServiceReference(IEventFactory.class);
		if (svcRef == null) {
			// The service doesn't exist yet: provide it
			pRegistration = aContext.registerService(IEventFactory.class,
					new DefaultEventFactory(), null);
		}
	}

	/*
	 * (non-Javadoc)
	 * 
	 * @see
	 * org.osgi.framework.BundleActivator#stop(org.osgi.framework.BundleContext)
	 */
	@Override
	public void stop(final BundleContext aContext) throws Exception {
		if (pRegistration != null) {
			pRegistration.unregister();
			pRegistration = null;
		}
	}
}
