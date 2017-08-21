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

package org.cohorte.herald.utils;

import org.cohorte.herald.eventapi.IEvent;
import org.cohorte.herald.eventapi.IEventFactory;
import org.cohorte.herald.eventapi.JavaEvent;

/**
 * Same as Python's Timer class, but executes the requested method again and
 * again, until cancel() is called.
 *
 * @author Thomas Calmant
 */
public class LoopTimer extends Thread {

	/** The event to wait for to get out of the loop */
	private final IEvent pFinished;

	/** Time to wait between calls (in milliseconds) */
	private final long pInterval;

	/** The object to run in the loop */
	private final Runnable pRunnable;

	/**
	 * Sets up the timer
	 *
	 * @param aInterval
	 *            Time to wait between calls (in milliseconds)
	 * @param aRunnable
	 *            The object to run in the loop
	 * @param aName
	 *            Name of the loop thread
	 */
	public LoopTimer(final long aInterval, final Runnable aRunnable) {

		this(aInterval, aRunnable, "LoopTimer");
	}

	/**
	 * Sets up the timer
	 *
	 * @param aInterval
	 *            Time to wait between calls (in milliseconds)
	 * @param aRunnable
	 *            The object to run in the loop
	 * @param aName
	 *            Name of the loop thread
	 */
	public LoopTimer(final long aInterval, final Runnable aRunnable,
			final String aName) {

		this(aInterval, aRunnable, aName, new JavaEvent());
	}

	/**
	 * Sets up the timer
	 *
	 * @param aInterval
	 *            Time to wait between calls (in milliseconds)
	 * @param aRunnable
	 *            The object to run in the loop
	 * @param aName
	 *            Name of the loop thread
	 * @param aEvent
	 *            The event to use to get out of the loop
	 */
	public LoopTimer(final long aInterval, final Runnable aRunnable,
			final String aName, final IEvent aEvent) {

		super(aName);
		pInterval = aInterval;
		pRunnable = aRunnable;
		pFinished = aEvent;
	}

	/**
	 * Sets up the timer
	 *
	 * @param aInterval
	 *            Time to wait between calls (in milliseconds)
	 * @param aRunnable
	 *            The object to run in the loop
	 * @param aName
	 *            Name of the loop thread
	 */
	public LoopTimer(final long aInterval, final Runnable aRunnable,
			final String aName, final IEventFactory aEventFactory) {

		this(aInterval, aRunnable, aName, aEventFactory.createEvent());
	}

	/**
	 * Cancels/stops the loop timer
	 */
	public void cancel() {

		pFinished.set();
	}

	/*
	 * (non-Javadoc)
	 * 
	 * @see java.lang.Thread#run()
	 */
	@Override
	public void run() {

		while (!pFinished.waitEvent(pInterval)) {
			pRunnable.run();
		}
	}
}
