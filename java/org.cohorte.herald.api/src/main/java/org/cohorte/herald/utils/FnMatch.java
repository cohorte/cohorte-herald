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

import java.util.regex.Pattern;

/**
 * A wild card filter
 *
 * @author Thomas Calmant
 */
public class FnMatch {

    /** The compiled Regex pattern */
    private final Pattern pPattern;

    /**
     * Sets up the file name filter
     *
     * @param aFnMatch
     *            A file name match string
     */
    public FnMatch(final String aFnMatch) {

        pPattern = compile(aFnMatch);
    }

    /**
     * Compiles a wild card filename filter into a Regex pattern
     *
     * Inspired from <a href=
     * "http://stackoverflow.com/questions/1247772/is-there-an-equivalent-of-java-util-regex-for-glob-type-patterns"
     * >this post on StackOverflow</a>
     *
     * @param aFnMatch
     *            A file name match string
     * @return A compiled Regex pattern
     */
    private Pattern compile(final String aFnMatch) {

        final StringBuilder out = new StringBuilder("^");
        boolean escaped = false;

        for (final char currentChar : aFnMatch.toCharArray()) {
            switch (currentChar) {
            case '*':
                if (escaped) {
                    out.append("\\*");
                    escaped = false;
                } else {
                    out.append(".*");
                }
                break;

            case '?':
                if (escaped) {
                    out.append("\\?");
                    escaped = false;
                } else {
                    out.append(".");
                }
                break;

            case '.':
                out.append("\\.");
                break;

            case '\\':
                if (escaped) {
                    out.append("\\\\");
                } else {
                    escaped = true;
                }
                break;

            default:
                out.append(currentChar);
            }
        }
        out.append('$');
        return Pattern.compile(out.toString());
    }

    /*
     * (non-Javadoc)
     *
     * @see java.lang.Object#equals(java.lang.Object)
     */
    @Override
    public boolean equals(final Object aObj) {

        if (aObj instanceof FnMatch) {
            // Compare by pattern string
            return pPattern.pattern().equals(
                    ((FnMatch) aObj).pPattern.pattern());

        } else if (aObj instanceof CharSequence) {
            // Compare string with pattern
            return aObj.toString().equals(pPattern.pattern());
        }

        return false;
    }

    /*
     * (non-Javadoc)
     *
     * @see java.lang.Object#hashCode()
     */
    @Override
    public int hashCode() {

        return pPattern.pattern().hashCode();
    }

    /**
     * Checks if the given string matches the name filter
     *
     * @param aName
     *            A string
     * @return True if the given string matches the filter
     */
    public boolean matches(final String aName) {

        return pPattern.matcher(aName).matches();
    }

    /*
     * (non-Javadoc)
     * 
     * @see java.lang.Object#toString()
     */
    @Override
    public String toString() {

        return pPattern.pattern();
    }
}
