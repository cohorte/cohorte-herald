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

package org.cohorte.herald.pyapi;

/**
 * A Java interface to access members of the Event Python class
 *
 * @author Thomas Calmant
 */
public interface IEvent {

	/**
	 * Reset the internal flag to false. Subsequently, threads calling wait()
	 * will block until set() is called to set the internal flag to true again.
	 */
	void clear();

	/**
	 * Return true if and only if the internal flag is true.
	 *
	 * @return true if the internal flag is true
	 */
	boolean isSet();

	/**
	 * Set the internal flag to true. All threads waiting for it to become true
	 * are awakened. Threads that call wait() once the flag is true will not
	 * block at all.
	 */
	void set();

	/**
	 * Block until the internal flag is true. If the internal flag is true on
	 * entry, return immediately. Otherwise, block until another thread calls
	 * set() to set the flag to true, or until the optional timeout occurs.
	 *
	 * This method returns the internal flag on exit, so it will always return
	 * True except if a timeout is given and the operation times out.
	 *
	 * @return The state of the internal flag
	 */
	boolean waitEvent();

	/**
	 * Block until the internal flag is true. If the internal flag is true on
	 * entry, return immediately. Otherwise, block until another thread calls
	 * set() to set the flag to true, or until the optional timeout occurs.
	 *
	 * This method returns the internal flag on exit, so it will always return
	 * True except if a timeout is given and the operation times out.
	 *
	 * @param aTimeout
	 *            Maximum time to wait for an event (in milliseconds)
	 * @return The state of the internal flag
	 */
	boolean waitEvent(long aTimeout);
}
