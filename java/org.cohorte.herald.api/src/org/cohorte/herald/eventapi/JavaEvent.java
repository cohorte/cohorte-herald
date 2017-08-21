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

import java.util.concurrent.TimeUnit;
import java.util.concurrent.locks.Condition;
import java.util.concurrent.locks.Lock;
import java.util.concurrent.locks.ReentrantLock;

/**
 * Java implementation of an event
 *
 * @author Thomas Calmant
 */
public class JavaEvent implements IEvent {

	/** Internal condition */
	private final Condition pCondition;

	/** State flag */
	private boolean pFlag;

	/** The lock associated to the condition */
	private final Lock pLock;

	/**
	 * Sets up the event
	 */
	public JavaEvent() {

		pLock = new ReentrantLock();
		pCondition = pLock.newCondition();
		pFlag = false;
	}

	/*
	 * (non-Javadoc)
	 * 
	 * @see org.cohorte.herald.eventapi.IEvent#clear()
	 */
	@Override
	public void clear() {
		pLock.lock();
		pFlag = false;
		pLock.unlock();
	}

	/*
	 * (non-Javadoc)
	 * 
	 * @see org.cohorte.herald.eventapi.IEvent#isSet()
	 */
	@Override
	public boolean isSet() {
		return pFlag;
	}

	/*
	 * (non-Javadoc)
	 * 
	 * @see org.cohorte.herald.eventapi.IEvent#set()
	 */
	@Override
	public void set() {
		pLock.lock();
		try {
			// Set the flag up and notify everybody
			pFlag = true;
			pCondition.signalAll();

		} finally {
			// Unlock in any case
			pLock.unlock();
		}
	}

	/*
	 * (non-Javadoc)
	 * 
	 * @see org.cohorte.herald.eventapi.IEvent#waitEvent()
	 */
	@Override
	public boolean waitEvent() {
		return waitEvent(-1);
	}

	/*
	 * (non-Javadoc)
	 * 
	 * @see org.cohorte.herald.eventapi.IEvent#waitEvent(long)
	 */
	@Override
	public boolean waitEvent(final long aTimeout) {
		pLock.lock();
		try {
			if (!pFlag) {
				// Wait only if the flag is not yet set
				if (aTimeout < 0) {
					pCondition.await();
				} else {
					pCondition.await(aTimeout, TimeUnit.MILLISECONDS);
				}
			}
			return pFlag;

		} catch (final InterruptedException ex) {
			// We've been interrupted, return immediately
			return pFlag;

		} finally {
			// Unlock in any case
			pLock.unlock();
		}
	}
}
