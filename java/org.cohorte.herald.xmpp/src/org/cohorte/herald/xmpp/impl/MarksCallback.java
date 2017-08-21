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

package org.cohorte.herald.xmpp.impl;

import java.util.Collection;
import java.util.LinkedHashSet;
import java.util.Set;

import org.osgi.service.log.LogService;

/**
 * Calls back a method when a list of elements have been marked
 *
 * @author Thomas Calmant
 */
public class MarksCallback<T> {

    /**
     * Defines the method called back when all elements have been marked
     *
     * @param <T>
     *            The type of the marked elements
     *
     * @author Thomas Calmant
     */
    public interface ICallback<T> {

        /**
         * Method call when all elements have been marked
         *
         * @param aSucceeded
         *            The list of succeeded elements
         * @param aErrors
         *            The list of elements marked with an error
         */
        void onMarksDone(Set<T> aSucceeded, Set<T> aErrors);
    }

    /** The method to call back */
    private final ICallback<T> pCallback;

    /** A flag to indicate if the callback method has been called */
    private boolean pCalled;

    /** The elements to mark */
    private final Set<T> pElements;

    /** The set of elements marked as an error */
    private final Set<T> pErrors = new LinkedHashSet<>();

    /** The log service */
    private final LogService pLogger;

    /** The set of elements marked as a success */
    private final Set<T> pSuccesses = new LinkedHashSet<>();

    /**
     * Sets up the count down.
     *
     * The callback method must accept two arguments: successful elements and
     * erroneous ones. The elements must be hashable, as sets are used
     * internally.
     *
     * @param aElements
     *            A list of elements to wait for
     * @param aCallback
     *            Method to call back when all elements have been marked
     * @param aLogger
     *            A log service, in case of error
     */
    public MarksCallback(final Collection<T> aElements,
            final ICallback<T> aCallback, final LogService aLogger) {

        pElements = new LinkedHashSet<>(aElements);
        pCallback = aCallback;
        pLogger = aLogger;
    }

    /**
     * Safely calls the callback method
     */
    private void call() {

        try {
            // Call the method, if any
            if (pCallback != null) {
                pCallback.onMarksDone(pSuccesses, pErrors);
            }

            // Job done
            pCalled = true;

        } catch (final Exception ex) {
            // Something went wrong
            pLogger.log(LogService.LOG_ERROR,
                    "Error calling back count down handler: " + ex, ex);
        }
    }

    /**
     * Checks if the call back has been called, i.e. if this object can be
     * deleted
     *
     * @return True if the call back method has been called
     */
    public boolean isDone() {

        return pCalled;
    }

    /**
     * Marks an element: removes it from the pending elements set and adds it to
     * the given set
     *
     * @param aElement
     *            The element to mark
     * @param aMarkSet
     *            The set where the element must be put
     * @return True if the element was pending, else false
     */
    private boolean mark(final T aElement, final Set<T> aMarkSet) {

        if (!pElements.remove(aElement)) {
            // Unknown element
            return false;
        }

        // The marked element is known
        aMarkSet.add(aElement);

        if (pElements.isEmpty()) {
            // No more elements to mark
            call();
        }

        return true;
    }

    /**
     * Marks an element as successful
     *
     * @param aElement
     *            The element to mark
     * @return True if the element was known
     */
    public boolean set(final T aElement) {

        return mark(aElement, pSuccesses);
    }

    /**
     * Marks an element as erroneous
     *
     * @param aElement
     *            The element to mark
     * @return True if the element was known
     */
    public boolean setError(final T aElement) {

        return mark(aElement, pErrors);
    }
}
