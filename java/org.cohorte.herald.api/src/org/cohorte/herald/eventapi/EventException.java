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

package org.cohorte.herald.eventapi;

/**
 * An exception occurred while waiting for an {@link EventData}
 *
 * @author Thomas Calmant
 */
public class EventException extends Exception {

	/** Serial version UID */
	private static final long serialVersionUID = 1L;

	/**
	 * Sets up the exception
	 */
	public EventException(final Throwable aCause) {

		super("Event exception: " + aCause, aCause);
	}
}
