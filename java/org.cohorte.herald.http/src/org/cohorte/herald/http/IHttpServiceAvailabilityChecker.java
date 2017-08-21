/**
 * Copyright 2016 Cohorte Technologies (ex. isandlaTech)
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
 * Checks if the Http Service is available (jetty server fully started)
 * 
 * @author bassem debbabi
 */
public interface IHttpServiceAvailabilityChecker {
	
	/**
	 * Gets the valid Http Port associated to the Http Service.
	 * 
	 * @return
	 */
	int getPort();
}
