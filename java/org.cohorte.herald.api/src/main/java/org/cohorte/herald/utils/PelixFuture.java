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

import java.util.concurrent.TimeoutException;

import org.cohorte.herald.eventapi.EventData;
import org.cohorte.herald.eventapi.EventException;

/**
 * A class to poll the result of a method called asynchronously.
 *
 * This class mimics Python's Pelix thread pooling
 *
 * @param <R>
 *            The type of the result of the executed method
 * @param <E>
 *            The type of the extra parameter of the callback method
 *
 * @author Thomas Calmant
 */
public class PelixFuture<R, E> implements Runnable {

    /**
     * A method that can be called by PelixFuture
     *
     * @param <R>
     *            The type of the result of the method
     *
     * @author Thomas Calmant
     */
    public interface Callable<R> {

        R run() throws Exception;
    }

    /**
     * A method to call back when the executed method ends
     *
     * @param <R>
     *            The type of the result of the executed method
     * @param <E>
     *            The type of the extra parameter
     *
     * @author Thomas Calmant
     */
    public interface Callback<R, E> {

        void run(R aResult, Throwable aThrowable, E aExtra);
    }

    /** The method to execute */
    private Callable<R> pCallable;

    /** The method to call back */
    private Callback<R, E> pCallback;

    /** Result/Failure event */
    private final EventData<R> pDoneEvent = new EventData<>();

    /** Extra argument */
    private E pExtra;

    /**
     * Checks if the method has been executed
     *
     * @return True if the method has been executed
     */
    public boolean done() {

        return pDoneEvent.isSet();
    }

    /**
     * Notifies the given callback about the result of the execution
     */
    private synchronized void notifyCallback() {

        if (pCallback != null) {
            pCallback.run(pDoneEvent.getData(), pDoneEvent.getError(), pExtra);
        }
    }

    /**
     * Waits for a result
     *
     * @return The result of the method
     * @throws EventException
     *             An error occurred executing the method
     */
    public R result() throws EventException {

        try {
            return result(null);

        } catch (final TimeoutException ex) {
            // Can't happen
            return null;
        }
    }

    /**
     * Waits for a result
     *
     * @param aTimeout
     *            Maximum time to wait for a result
     * @return The result of the execution
     * @throws EventException
     *             Something went wrong
     * @throws TimeoutException
     *             Timeout reached before the execution ends
     */
    public R result(final Long aTimeout) throws EventException,
            TimeoutException {

        if (pDoneEvent.waitEvent(aTimeout)) {
            return pDoneEvent.getData();

        } else {
            throw new TimeoutException();
        }
    }

    /*
     * (non-Javadoc)
     *
     * @see java.lang.Runnable#run()
     */
    @Override
    public void run() {

        if (pCallable == null) {
            return;
        }

        try {
            // Run the method
            final R result = pCallable.run();
            pDoneEvent.set(result);

        } catch (final Exception ex) {
            // Something went wrong
            pDoneEvent.raiseException(ex);

        } finally {
            // Notify the callback in any case
            notifyCallback();
        }
    }

    /**
     * Sets the callback method, called once the result has been computed or in
     * case of exception
     *
     * @param aCallback
     *            The method to call back
     * @param aExtra
     *            An extra parameter given to the callback method
     */
    public synchronized void setCallback(final Callback<R, E> aCallback,
            final E aExtra) {

        pCallback = aCallback;
        pExtra = aExtra;
    }

    /**
     * Sets the method to execute
     *
     * @param aMethod
     *            The method to execute
     */
    public void setMethod(final Callable<R> aMethod) {

        pCallable = aMethod;
    }
}
