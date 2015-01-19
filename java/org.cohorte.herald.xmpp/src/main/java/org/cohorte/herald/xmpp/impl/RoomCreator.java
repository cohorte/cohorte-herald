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
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

import org.osgi.service.log.LogService;

import rocks.xmpp.core.Jid;
import rocks.xmpp.core.XmppException;
import rocks.xmpp.core.session.XmppSession;
import rocks.xmpp.core.stanza.model.StanzaError;
import rocks.xmpp.core.stanza.model.StanzaException;
import rocks.xmpp.extensions.data.model.DataForm;
import rocks.xmpp.extensions.data.model.DataForm.Field;
import rocks.xmpp.extensions.muc.ChatRoom;
import rocks.xmpp.extensions.muc.ChatService;
import rocks.xmpp.extensions.muc.MultiUserChatManager;
import rocks.xmpp.extensions.muc.OccupantEvent;
import rocks.xmpp.extensions.muc.OccupantListener;

/**
 * XMPP Room creation utility.
 *
 * The associated client must support XEP-0004 and XEP-0045.
 *
 * @author Thomas Calmant
 */
public class RoomCreator {

    /** Domain -&gt; ChatService mapping */
    private final Map<String, ChatService> pChatServices = new LinkedHashMap<>();

    /** A log service */
    private final LogService pLogger;

    /** The MultiUserChat manager */
    private MultiUserChatManager pMucManager;

    /** The XMPP session */
    private final XmppSession pSession;

    public RoomCreator(final XmppSession aSession, final LogService aLogger) {

        // Setup members
        pLogger = aLogger;
        pSession = aSession;

        // Find the MUC chat service
        findChatServices();
    }

    /**
     * Sets up the configuration of the room (if any)
     *
     * @param aRoom
     *            The room to configuration
     * @param aConfiguration
     *            The custom configuration of the room
     * @throws XmppException
     *             Error sending room configuration
     */
    private void configureRoom(final ChatRoom aRoom,
            final Collection<Field> aConfiguration) throws XmppException {

        if (aConfiguration.isEmpty()) {
            // No configuration given: ignore
            return;
        }

        // Get current room configuration
        final DataForm configurationForm = aRoom.getConfigurationForm();
        final List<Field> rawFields = configurationForm.getFields();

        // Convert the configuration fields list to map
        final Map<String, Field> configFields = new LinkedHashMap<>();
        for (final Field field : rawFields) {
            configFields.put(field.getVar(), field);
        }

        // Filter configuration
        for (final Field customField : aConfiguration) {
            final Field configField = configFields.get(customField.getVar());
            if (configField != null) {
                // Field is supported: set it
                configField.getValues().clear();
                configField.getValues().addAll(customField.getValues());

            } else {
                // Clean up
                pLogger.log(
                        LogService.LOG_DEBUG,
                        "Unsupported configuration field: "
                                + customField.getVar());
            }
        }
        // Send the new configuration
        aRoom.submitConfigurationForm(configurationForm);
    }

    /**
     * Creates or joins the given chat room
     *
     * @param aRoom
     *            Name of the chat room (local part of JID)
     * @param aMucDomain
     *            MUC service domain (domain part of the JID)
     * @param aNickname
     *            Nickname to use in the room
     * @param aConfiguration
     *            Optional room configuration (if the room is created)
     * @param aListener
     *            Room events listener
     */
    public synchronized void createRoom(final String aRoom,
            final String aMucDomain, final String aNickname,
            final Collection<Field> aConfiguration,
            final IRoomListener aListener) {

        // Format the room JID
        final Jid roomAddress = new Jid(aRoom, aMucDomain);

        // Get the chat service
        final ChatService chatService = pChatServices.get(aMucDomain);
        if (chatService == null) {
            // Can't do anything: call the errback
            aListener.onRoomError(roomAddress, aNickname, "no-muc-service",
                    "No MUC Service has been found for domain " + aMucDomain);
            return;
        }

        // Prepare a handle to the room
        final ChatRoom room = chatService.createRoom(roomAddress.getLocal());

        // Add listeners
        room.addOccupantListener(new OccupantListener() {

            @Override
            public void occupantChanged(final OccupantEvent aEvent) {

                switch (aEvent.getType()) {
                case ENTERED:
                    // Occupant got in
                    aListener.onRoomIn(roomAddress, aEvent.getOccupant());
                    break;

                case BANNED:
                case EXITED:
                case KICKED:
                    // Occupant got away
                    aListener.onRoomOut(roomAddress, aEvent.getOccupant());
                    break;

                default:
                    // Ignore others
                    break;
                }
            }
        });

        try {
            // Enter the room
            room.enter(aNickname);

        } catch (final StanzaException ex) {
            // Server-side error
            pLogger.log(LogService.LOG_ERROR, "Error joining XMPP room: " + ex,
                    ex);

            final StanzaError error = ex.getStanza().getError();
            aListener.onRoomError(roomAddress, aNickname, error.getCondition()
                    .toString(), error.getText());
            return;

        } catch (final XmppException ex) {
            // Client-side error
            pLogger.log(LogService.LOG_ERROR, "Error joining XMPP room: " + ex,
                    ex);
            aListener.onRoomError(roomAddress, aNickname, "xmpp-error",
                    ex.getMessage());
            return;
        }

        // The "not-owner" information is not available: the configuration
        // setting may raise an exception
        try {
            // Configure the room
            configureRoom(room, aConfiguration);
        } catch (final XmppException ex) {
            pLogger.log(LogService.LOG_WARNING,
                    "Error setting up XMPP room configuration: " + ex);
        }
    }

    /**
     * Looks for available XMPP MultiUserChat services and stores them into a
     * map
     */
    private void findChatServices() {

        try {
            // Get the MUC extension manager
            pMucManager = pSession
                    .getExtensionManager(MultiUserChatManager.class);

            // Get the list of chat services
            final Collection<ChatService> chatServices = pMucManager
                    .getChatServices();

            // Store them in a map
            for (final ChatService chatService : chatServices) {
                pChatServices.put(chatService.getAddress().getDomain(),
                        chatService);
            }

        } catch (final XmppException ex) {
            pLogger.log(LogService.LOG_ERROR,
                    "Error looking for XMPP MUC chat services: " + ex);
        }
    }
}
