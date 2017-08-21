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
 * Implementation of EventData from Pelix
 *
 * @author Thomas Calmant
 */
public class EventData<T> {

	/** Data associated to the event */
	private T pData;

	/** Internal event */
	private final IEvent pEvent;

	/** Exception associated to the event */
	private EventException pException;

	/**
	 * Default constructor
	 */
	public EventData() {

		this(new JavaEvent());
	}

	/**
	 * Construct the EventData object with a custom event
	 *
	 * @param aEvent
	 *            The underlying event
	 */
	public EventData(final IEvent aEvent) {

		pEvent = aEvent;
		pData = null;
		pException = null;
	}

	/**
	 * Construct the EventData object with an event made by the given factory
	 *
	 * @param aEventFactory
	 *            An event factory
	 */
	public EventData(final IEventFactory aEventFactory) {

		this(aEventFactory.createEvent());
	}

	/**
	 * Clear the event
	 */
	public synchronized void clear() {

		pEvent.clear();
		pData = null;
		pException = null;
	}

	/**
	 * @return the data
	 */
	public T getData() {

		return pData;
	}

	/**
	 * @return The exception that forced the event up (if any)
	 */
	public Throwable getError() {

		if (pException != null) {
			return pException.getCause();
		}

		return null;
	}

	/**
	 * Checks if the event has been set
	 *
	 * @return
	 */
	public boolean isSet() {

		return pEvent.isSet();
	}

	/**
	 * Forces the event to be set, and let the {@link #waitEvent(Long)} method
	 * throw the given exception
	 *
	 * @param aThrowable
	 *            The given which forced the event to be set
	 */
	public synchronized void raiseException(final Throwable aThrowable) {

		pData = null;
		pException = new EventException(aThrowable);
		pEvent.set();
	}

	/**
	 * Sets the event, without data
	 */
	public void set() {

		set(null);
	}

	/**
	 * Sets the event, with data
	 *
	 * @param aData
	 *            Data to associate to the event
	 */
	public synchronized void set(final T aData) {

		pData = aData;
		pException = null;
		pEvent.set();
	}

	/**
	 * Waits for the Event to be set
	 *
	 * @throws EventException
	 *             Contains the exception that forced the event up (if any)
	 */
	public boolean waitEvent() throws EventException {

		return waitEvent(null);
	}

	/**
	 * Waits for the Event to be set
	 *
	 * @param aTimeout
	 *            Wait timeout (in milliseconds)
	 * @return The state of the event
	 * @throws EventException
	 *             Contains the exception that forced the event up (if any)
	 */
	public boolean waitEvent(final Long aTimeout) throws EventException {
		final boolean result;
		if (aTimeout == null || aTimeout < 0) {
			result = pEvent.waitEvent(-1);
		} else {
			result = pEvent.waitEvent(aTimeout);
		}
		if (pException != null) {
			throw pException;
		}

		return result;
	}
}
