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

import java.util.concurrent.TimeUnit;
import java.util.concurrent.locks.Condition;
import java.util.concurrent.locks.Lock;
import java.util.concurrent.locks.ReentrantLock;

/**
 * Implementation of Python's threading.Event
 *
 * @author Thomas Calmant
 */
public class Event {

    /** Internal condition */
    private final Condition pCondition;

    /** State flag */
    private boolean pFlag;

    /** The lock associated to the condition */
    private final Lock pLock;

    /**
     * Sets up the event
     */
    public Event() {

        pLock = new ReentrantLock();
        pCondition = pLock.newCondition();
        pFlag = false;
    }

    /**
     * Resets the internal flag to false
     */
    public void clear() {

        pLock.lock();
        pFlag = false;
        pLock.unlock();
    }

    /**
     * Checks if the flag has been set
     *
     * @return True if the flag is set
     */
    public boolean isSet() {

        return pFlag;
    }

    /**
     * Sets the internal flag to true.
     */
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

    /**
     * Blocks until the internal flag is true
     *
     * @return The state of the flag (true)
     */
    public boolean waitEvent() {

        return waitEvent(null);
    }

    /**
     * Blocks until the internal flag is true, or the time out is reached
     *
     * @param aTimeout
     *            Maximum time to wait for the event (in milliseconds)
     * @return The state of the flag
     */
    public boolean waitEvent(final Long aTimeout) {

        pLock.lock();
        try {
            if (!pFlag) {
                // Wait only if the flag is not yet set
                if (aTimeout == null) {
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
