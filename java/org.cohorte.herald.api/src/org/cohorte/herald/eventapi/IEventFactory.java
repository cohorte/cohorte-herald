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

package org.cohorte.herald.eventapi;

/**
 * Specification of an Event object factory
 *
 * @author Thomas Calmant
 */
public interface IEventFactory {

	/**
	 * Creates an object implementing the IEvent interface
	 *
	 * @return An event
	 */
	IEvent createEvent();

	/**
	 * Sleeps for the given number of milliseconds
	 *
	 * @param aMilliseconds
	 *            The number of milliseconds to wait
	 */
	void sleep(long aMilliseconds);
}
