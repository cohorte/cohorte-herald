package org.cohorte.herald.local.discovery;

import org.apache.felix.ipojo.annotations.Component;
import org.apache.felix.ipojo.annotations.Requires;
import org.osgi.service.log.LogService;

/**
 * DirectCallback component instantiation helper
 *
 * @see composition "" witch instanciate
 *      "herald-local-discovery-forkercaller-starter"
 *
 * @author ogattaz
 * @author Thomas Calmant
 */
@Component
public class DirectCallbackStarter {

	/** The logger */
	@Requires(optional = true)
	private LogService pLogger;

}
