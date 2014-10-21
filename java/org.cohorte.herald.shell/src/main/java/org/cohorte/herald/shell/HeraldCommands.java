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

package org.cohorte.herald.shell;

import java.util.Arrays;
import java.util.Collection;
import java.util.TreeSet;

import org.apache.felix.ipojo.annotations.Component;
import org.apache.felix.ipojo.annotations.Instantiate;
import org.apache.felix.ipojo.annotations.Provides;
import org.apache.felix.ipojo.annotations.Requires;
import org.apache.felix.ipojo.annotations.ServiceProperty;
import org.cohorte.herald.HeraldException;
import org.cohorte.herald.HeraldTimeout;
import org.cohorte.herald.IDirectory;
import org.cohorte.herald.IHerald;
import org.cohorte.herald.IPostCallback;
import org.cohorte.herald.IPostErrback;
import org.cohorte.herald.Message;
import org.cohorte.herald.MessageReceived;
import org.cohorte.herald.NoListener;
import org.cohorte.herald.NoTransport;
import org.cohorte.herald.Peer;
import org.cohorte.herald.Target;
import org.cohorte.herald.UnknownPeer;
import org.cohorte.herald.ValueError;

/**
 * Provides Gogo shell commands for Herald
 *
 * @author Thomas Calmant
 */
@Component
@Provides(specifications = HeraldCommands.class)
@Instantiate(name = "herald-shell")
public class HeraldCommands {

    /** The Gogo commands */
    @ServiceProperty(name = "osgi.command.function",
            value = "{local,peers,fire}")
    private String[] pCommands;

    /** The Herald directory */
    @Requires
    private IDirectory pDirectory;

    /** Herald core service */
    @Requires
    private IHerald pHerald;

    /** The Gogo commands scope */
    @ServiceProperty(name = "osgi.command.scope", value = "herald")
    private String pScope;

    /**
     * Fires a message
     *
     * @param aTarget
     *            Targeted peer
     * @param aSubject
     *            Message subject
     * @param aWords
     *            Message content
     */
    public void fire(final String aTarget, final String aSubject,
            final String... aWords) {

        // Generate the content string
        final String content = join(aWords);

        try {
            // Fire message
            final String msgUid = pHerald.fire(aTarget, new Message(aSubject,
                    content));
            System.out.println("Message sent: " + msgUid);

        } catch (final NoTransport ex) {
            System.err.println("No transport to join " + aTarget);

        } catch (final UnknownPeer ex) {
            System.err.println("Unknown peer: " + aTarget);
        }
    }

    /**
     * Fires a message to a group
     *
     * @param aGroup
     *            Name of a group
     * @param aSubject
     *            Message subject
     * @param aWords
     *            Message content
     */
    public void fireGroup(final String aGroup, final String aSubject,
            final String... aWords) {

        // Generate the content string
        final String content = join(aWords);

        // Fire message
        final Message msg = new Message(aSubject, content);
        try {
            final Collection<Peer> joinedPeers = pHerald.fireGroup(aGroup, msg);
            System.out.println("Message sent: " + msg.getUid());

            // Compute missed peers
            final Collection<Peer> allPeers = pDirectory
                    .getPeersForGroup(aGroup);
            allPeers.removeAll(joinedPeers);
            if (!allPeers.isEmpty()) {
                System.out.println("Missed peers: "
                        + join(Target.toUids(allPeers)));
            }

        } catch (final NoTransport ex) {
            System.err.println("No transport to join group " + aGroup);
        }
    }

    /**
     * Forgets about the given message
     *
     * @param aUid
     *            A message UID
     */
    public void forget(final String aUid) {

        if (pHerald.forget(aUid)) {
            System.out.println("Herald forgot about " + aUid);
        } else {
            System.out.println("Herald wasn't aware of " + aUid);
        }
    }

    /**
     * Joins the given words with spaces
     *
     * @param aWords
     *            A collection of words
     * @return A string
     */
    private String join(final Collection<String> aWords) {

        // Generate the content string
        final StringBuilder content = new StringBuilder();
        for (final String word : aWords) {
            content.append(word).append(" ");
        }

        // Remove trailing space
        if (content.length() > 0) {
            content.deleteCharAt(content.length() - 1);
        }

        return content.toString();
    }

    /**
     * Joins the given words with spaces
     *
     * @param aWords
     *            An array of words
     * @return A string
     */
    private String join(final String... aWords) {

        return join(Arrays.asList(aWords));
    }

    /**
     * Prints the details of the local peer
     */
    public void local() {

        printPeer(pDirectory.getLocalPeer());
    }

    /**
     * Prints the list of the known peers
     */
    public void peers() {

        for (final Peer peer : pDirectory.getPeers()) {
            printPeer(peer);
        }
    }

    /**
     * Posts a message
     *
     * @param aTarget
     *            Targeted peer
     * @param aSubject
     *            Message subject
     * @param aWords
     *            Message content
     */
    public void post(final String aTarget, final String aSubject,
            final String... aWords) {

        // Generate the content string
        final String content = join(aWords);

        // Prepare callback methods
        final IPostCallback callback = new IPostCallback() {

            @Override
            public void heraldCallback(final IHerald aHerald,
                    final MessageReceived aReply) {

                System.out.println("Got answer to " + aReply.getReplyTo()
                        + ":\n" + aReply.getContent());
            }
        };

        final IPostErrback errback = new IPostErrback() {

            @Override
            public void heraldErrback(final IHerald aHerald,
                    final HeraldException aException) {

                System.err.println("Error posting message: " + aException);
            }
        };

        try {
            // Post message
            final String msgUid = pHerald.post(aTarget, new Message(aSubject,
                    content), callback, errback);
            System.out.println("Message sent: " + msgUid);

        } catch (final NoTransport ex) {
            System.err.println("No transport to join " + aTarget);

        } catch (final UnknownPeer ex) {
            System.err.println("Unknown peer: " + aTarget);
        }
    }

    /**
     * Posts a message to a group
     *
     * @param aGroup
     *            Name of a group
     * @param aSubject
     *            Message subject
     * @param aWords
     *            Message content
     */
    public void postGroup(final String aGroup, final String aSubject,
            final String... aWords) {

        // Generate the content string
        final String content = join(aWords);

        // Prepare callback methods
        final IPostCallback callback = new IPostCallback() {

            @Override
            public void heraldCallback(final IHerald aHerald,
                    final MessageReceived aReply) {

                System.out.println("Got answer to " + aReply.getReplyTo()
                        + ":\n" + aReply.getContent());
            }
        };

        final IPostErrback errback = new IPostErrback() {

            @Override
            public void heraldErrback(final IHerald aHerald,
                    final HeraldException aException) {

                System.err.println("Error posting message: " + aException);
            }
        };

        // Fire message
        try {
            final String msgUid = pHerald.postGroup(aGroup, new Message(
                    aSubject, content), callback, errback, null);
            System.out.println("Message sent: " + msgUid);

        } catch (final NoTransport ex) {
            System.err.println("No transport to join group " + aGroup);

        } catch (final ValueError ex) {
            System.out.println("Unknown group: " + aGroup);
        }
    }

    /**
     * Prints information about the given peer
     *
     * @param aPeer
     *            Peer to print
     */
    private void printPeer(final Peer aPeer) {

        // Prepare the string
        final StringBuilder builder = new StringBuilder();
        builder.append("Peer ").append(aPeer.getUid()).append("\n");
        builder.append("\t- UID......: ").append(aPeer.getUid()).append("\n");
        builder.append("\t- Name.....: ").append(aPeer.getName()).append("\n");
        builder.append("\t- Node UID.: ").append(aPeer.getNodeUid())
                .append("\n");
        builder.append("\t- Node Name: ").append(aPeer.getNodeName())
                .append("\n");
        builder.append("\t- App ID...: ").append(aPeer.getApplicationId())
                .append("\n");

        // Groups will be sorted if we use a TreeSet
        builder.append("\t- Groups...:").append("\n");
        final Collection<String> groups = new TreeSet<>(aPeer.getGroups());
        for (final String group : groups) {
            builder.append("\t\t- ").append(group).append("\n");
        }

        // Accesses
        builder.append("\t- Accesses.:").append("\n");
        final Collection<String> accesses = new TreeSet<>(aPeer.getAccesses());
        for (final String accessId : accesses) {
            builder.append("\t\t- ").append(accessId).append(": ")
                    .append(aPeer.getAccess(accessId)).append("\n");
        }

        // Print everything at once
        System.out.println(builder);
    }

    /**
     * Sends a message to a peer
     *
     * @param aGroup
     *            Name of a group
     * @param aSubject
     *            Message subject
     * @param aWords
     *            Message content
     */
    public void send(final String aTarget, final String aSubject,
            final String... aWords) {

        // Generate the content string
        final String content = join(aWords);

        try {
            // Send message
            final Object result = pHerald.send(aTarget, new Message(aSubject,
                    content));
            System.out.println("Response: " + result);

        } catch (final NoTransport ex) {
            System.err.println("No transport to join " + aTarget);

        } catch (final NoListener ex) {
            System.err.println("No listener for " + aSubject);

        } catch (final HeraldTimeout ex) {
            System.err.println("No response given before timeout");

        } catch (final HeraldException ex) {
            System.err.println("Error sending message: " + ex);
        }
    }
}
