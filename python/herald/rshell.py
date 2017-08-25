#!/usr/bin/python
# -- Content-Encoding: UTF-8 --
"""
Pelix Shell commands for Herald

:author: Thomas Calmant
:copyright: Copyright 2014, isandlaTech
:license: Apache License 2.0
:version: 1.0.1
:status: Alpha

..

    Copyright 2014 isandlaTech

    Licensed under the Apache License, Version 2.0 (the "License");
    you may not use this file except in compliance with the License.
    You may obtain a copy of the License at

        http://www.apache.org/licenses/LICENSE-2.0

    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS,
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    See the License for the specific language governing permissions and
    limitations under the License.
"""

# Bundle version
import herald.version
__version__=herald.version.__version__

# ------------------------------------------------------------------------------

# Herald
from herald.exceptions import HeraldException
import herald
import herald.beans as beans

# Pelix
from pelix.ipopo.decorators import ComponentFactory, Requires, Provides, \
    Property, Validate, Invalidate, Instantiate
import pelix.shell.beans

# Standard library
import logging
import threading
import uuid

try:
    # Python 2
    from StringIO import StringIO
except ImportError:
    # Python 3
    from io import StringIO

# ------------------------------------------------------------------------------

_logger = logging.getLogger(__name__)

# Subject of the messages for the server
_PREFIX_SERVER = "herald/shell"
MSG_SERVER_OPEN = "{0}/open".format(_PREFIX_SERVER)
MSG_SERVER_COMMAND = "{0}/command".format(_PREFIX_SERVER)
MSG_SERVER_CLOSE = "{0}/close".format(_PREFIX_SERVER)

# Subject of the messages for the client
_PREFIX_CLIENT = "herald/shell-client"
MSG_CLIENT_ERROR = "{0}/error".format(_PREFIX_CLIENT)
MSG_CLIENT_PRINT = "{0}/print".format(_PREFIX_CLIENT)
MSG_CLIENT_PROMPT = "{0}/prompt".format(_PREFIX_CLIENT)
MSG_CLIENT_CLOSE = "{0}/close".format(_PREFIX_CLIENT)

# Session properties
SESSION_SHELL_RUNNING = "__herald_shell_running__"
SESSION_SESSION_ID = "__session_id__"
SESSION_CLIENT_ID = "__client_uid__"
SESSION_SERVER_ID = "__server_uid__"

# ------------------------------------------------------------------------------


@ComponentFactory("herald-remote-shell-client-factory")
@Requires("_herald", herald.SERVICE_HERALD)
@Provides((pelix.shell.SERVICE_SHELL_COMMAND, herald.SERVICE_LISTENER,
           herald.SERVICE_DIRECTORY_LISTENER))
@Property('_filters', herald.PROP_FILTERS, ['{0}/*'.format(_PREFIX_CLIENT)])
@Instantiate("herald-remote-shell-client")
class HeraldRemoteShellClient(object):
    """
    Herald remote shell command
    """
    def __init__(self):
        """
        Sets up the object
        """
        self._herald = None

        # Thread safety
        self.__lock = threading.Lock()

        # Active session ID -> local shell session
        self._sessions = {}

        # Peer UID -> session ID
        self._peers = {}

    @staticmethod
    def get_namespace():
        """
        Retrieves the name space of this command handler
        """
        return "herald"

    def get_methods(self):
        """
        Retrieves the list of tuples (command, method) for this command handler
        """
        return [("remote", self.remote_shell)]

    def remote_shell(self, session, peer):
        """
        Opens a remote shell to the given peer
        """
        try:
            # Open session
            shell_info_msg = self._herald.send(
                peer, beans.Message(MSG_SERVER_OPEN))
        except HeraldException as ex:
            session.write_line("Error opening session: {0}", ex)
            return
        except KeyError as ex:
            session.write_line("Unknown peer: {0}", ex)
            return

        # Read session information
        shell_info = shell_info_msg.content
        session_id = shell_info['session_id']
        if not session_id:
            session.write_line("Connection refused")
            return

        peer_uid = shell_info['peer_uid']
        prompt_str = "({0}) {1}".format(peer_uid, shell_info['ps1'])

        # Setup the session variables
        session.set(SESSION_SHELL_RUNNING, True)
        session.set(SESSION_SERVER_ID, peer_uid)

        with self.__lock:
            # Store the session
            self._sessions[session_id] = session
            self._peers.setdefault(peer_uid, set()).add(session_id)

        # Print the banner
        session.write_line(shell_info['banner'])

        try:
            # REPL
            while session.get(SESSION_SHELL_RUNNING):
                # Read command line
                line = session.prompt(prompt_str)
                if line.strip().lower() == "exit":
                    # Exit server
                    break
                elif not line.strip():
                    # Empty line
                    continue

                # Send the command line
                content = {"session_id": session_id,
                           "line": line}
                result_msg = self._herald.send(
                    peer, beans.Message(MSG_SERVER_COMMAND, content))

                # Print results
                session.write_line(prompt_str, result_msg.content)

        except (HeraldException, KeyError) as ex:
            # Error sending message
            _logger.exception("Error sending command to peer: %s", ex)
            session.write_line("Error sending command to peer: {0}", ex)

        except (KeyboardInterrupt, EOFError):
            # Ctrl+C or Ctrl+D: just stop the shell
            pass

        try:
            # Clear local references
            self.__clear_session(session_id)
        except KeyError:
            # Session has been closed on the server side
            pass
        else:
            try:
                # Close the session (don't worry about errors)
                self._herald.fire(
                    peer, beans.Message(MSG_SERVER_CLOSE, session_id))
            except Exception as ex:
                _logger.warning("Error closing session: %s", ex)

    def __clear_session(self, session_id):
        """
        Removes references to the given session ID

        :param session_id: A session ID
        :return: The local shell session
        :raise KeyError: Unknown session UID
        """
        with self.__lock:
            # Pop local session
            session = self._sessions.pop(session_id)

            # Clean up peer reference
            peer_uid = session.get(SESSION_SERVER_ID)
            peer_session = self._peers[peer_uid]
            peer_session.discard(session_id)
            if not peer_session:
                del self._peers[peer_uid]

        return session

    def herald_message(self, herald_svc, message):
        """
        An Herald message has been received
        """
        kind = message.subject.rsplit('/', 1)[1]
        if kind == "print":
            # Print a line
            session_id = message.content['session_id']
            text = message.content['text']
            try:
                # Print the given line, as is
                session = self._sessions[session_id]
                session.write(text)
                session.flush()
            except KeyError:
                _logger.warning("No session with ID: %s", session_id)

        elif kind == "prompt":
            # Request data from the client
            session_id = message.content['session_id']
            try:
                # Read command line
                session = self._sessions[session_id]
            except KeyError:
                _logger.warning("No session with ID: %s", session_id)
            else:
                try:
                    line = session.prompt()
                    herald_svc.reply(message, line)
                except (EOFError, KeyboardInterrupt):
                    # Ctrl+D received: close the session
                    if session.get(SESSION_SHELL_RUNNING):
                        herald_svc.reply(message, session_id, MSG_SERVER_CLOSE)

                    session.set(SESSION_SHELL_RUNNING, False)

        elif kind == "close":
            # Clean up a session
            session_id = message.content
            try:
                session = self.__clear_session(session_id)
                session.write_line("Session closed. Press Enter to exit.")
                session.set(SESSION_SHELL_RUNNING, False)
            except KeyError:
                _logger.warning("No session with ID: %s", session_id)

        elif kind == "error":
            _logger.warning("Error on shell server side: %s", message.content)

    def peer_unregistered(self, peer):
        """
        Peer unregistered: close local session
        """
        with self.__lock:
            try:
                # Get all active sessions for this peer
                sessions_ids = self._peers.pop(peer.uid)
            except KeyError:
                # No active session: ignore
                return

            for session_id in sessions_ids:
                try:
                    # Pop the session & stop the loop
                    session = self._sessions.pop(session_id)
                    session.set(SESSION_SHELL_RUNNING, False)

                    # Print an exit message
                    session.write_line("Peer has gone away. "
                                       "Press Enter to exit.")
                except KeyError:
                    # Unknown session
                    pass

    @staticmethod
    def peer_registered(peer):
        """
        Peer registered: ignore
        """
        pass

    @staticmethod
    def peer_updated(peer, access_id, data, previous):
        """
        Peer updated: ignore
        """
        pass

# ------------------------------------------------------------------------------


class _HeraldOutputStream(object):
    """
    The I/O handler for the Herald shell
    """
    def __init__(self, herald_svc, peer_uid, session_id):
        """
        Sets up the I/O handler

        :param herald_svc: Herald service
        :param peer_uid: Shell client peer UID
        :param session_id: Shell session ID
        """
        self._herald = herald_svc
        self._peer = peer_uid
        self._session = session_id
        self._buffer = StringIO()

    def write(self, data):
        """
        Writes data to a buffer
        """
        self._buffer.write(data)

    def flush(self):
        """
        Sends buffered data to the target
        """
        # Flush buffer
        line = self._buffer.getvalue()
        self._buffer = StringIO()

        # Send the message
        content = {"session_id": self._session, "text": line}
        self._herald.fire(self._peer, beans.Message(MSG_CLIENT_PRINT, content))


class _HeraldInputStream(object):
    """
    The I/O handler for the Herald shell
    """
    def __init__(self, herald_svc, peer_uid, session_id):
        """
        Sets up the I/O handler

        :param herald_svc: Herald service
        :param peer_uid: Shell client peer UID
        :param session_id: Shell session ID
        """
        self._herald = herald_svc
        self._peer = peer_uid
        self._session = session_id

    def readline(self):
        """
        Waits for a line from the Herald client
        """
        content = {"session_id": self._session}
        prompt_msg = self._herald.send(
            self._peer, beans.Message(MSG_CLIENT_PROMPT, content))
        if prompt_msg.subject == MSG_SERVER_CLOSE:
            # Client closed its shell
            raise EOFError

        return prompt_msg.content


@ComponentFactory("herald-remote-shell-server-factory")
@Requires("_directory", herald.SERVICE_DIRECTORY)
@Requires("_herald", herald.SERVICE_HERALD)
@Requires("_shell", pelix.shell.SERVICE_SHELL)
@Provides((herald.SERVICE_LISTENER, herald.SERVICE_DIRECTORY_LISTENER))
@Property('_filters', herald.PROP_FILTERS, ['{0}/*'.format(_PREFIX_SERVER)])
@Instantiate("herald-remote-shell-server")
class HeraldRemoteShellServer(object):
    """
    Herald remote shell server
    """
    def __init__(self):
        """
        Sets up the object
        """
        # Injected services
        self._directory = None
        self._herald = None
        self._shell = None

        # Local peer UID
        self._local_uid = None

        # Active session ID => local shell session
        self._sessions = {}
        self.__lock = threading.Lock()

    @Validate
    def validate(self, _):
        """
        Component validated
        """
        self._local_uid = self._directory.local_uid

    @Invalidate
    def invalidate(self, _):
        """
        Component invalidated
        """
        with self.__lock:
            for session in self._sessions.values():
                peer_uid = session.get(SESSION_CLIENT_ID)
                session_id = session.get(SESSION_SESSION_ID)

                try:
                    self._herald.fire(
                        peer_uid, beans.Message(MSG_CLIENT_CLOSE, session_id))
                except HeraldException as ex:
                    # Error sending message
                    _logger.error("Error sending session close message: %s", ex)
                except KeyError:
                    # Unknown peer: ignore
                    pass

            # Clear sessions
            self._sessions.clear()

    def herald_message(self, herald_svc, message):
        """
        An Herald message has been received
        """
        try:
            kind = message.subject.rsplit('/', 1)[1]
            if kind == "open":
                # Open a session
                self._open_session(herald_svc, message)

            elif kind == "close":
                # Clean up a session
                self._close_session(herald_svc, message)

            elif kind == "command":
                # Execute a command
                self._run_command(herald_svc, message)
        except Exception as ex:
            herald_svc.reply(
                message, "Error handling message: {0}".format(ex),
                MSG_CLIENT_ERROR)

    def peer_unregistered(self, peer):
        """
        Peer unregistered: close its sessions
        """
        lost_peer = peer.uid
        with self.__lock:
            # List IDs of lost sessions
            lost_sessions = [session_id
                             for session_id, session in self._sessions.items()
                             if session.get(SESSION_CLIENT_ID) == lost_peer]

            # Clear them
            for session_id in lost_sessions:
                del self._sessions[session_id]

    @staticmethod
    def peer_registered(peer):
        """
        Peer registered: ignore
        """
        pass

    @staticmethod
    def peer_updated(peer, access_id, data, previous):
        """
        Peer updated: ignore
        """
        pass

    def _open_session(self, herald_svc, message):
        """
        Opens a remote shell session.

        Replies to the sender with a session ID, a banner, a PS1 and the local
        peer UID

        :param herald_svc: Herald service
        :param message: Received message
        """
        # Generate a session ID
        session_id = str(uuid.uuid4())

        # Prepare a shell session
        io_handler = pelix.shell.beans.IOHandler(
            _HeraldInputStream(herald_svc, message.sender, session_id),
            _HeraldOutputStream(herald_svc, message.sender, session_id))

        session = pelix.shell.beans.ShellSession(io_handler)
        session.set(SESSION_SESSION_ID, session_id)
        session.set(SESSION_CLIENT_ID, message.sender)

        with self.__lock:
            # Store it
            self._sessions[session_id] = session

        # Reply content
        content = {"session_id": session_id,
                   "banner": self._shell.get_banner(),
                   "ps1": self._shell.get_ps1(),
                   "peer_uid": self._local_uid}

        # Send reply
        herald_svc.reply(message, content)

    def _run_command(self, herald_svc, message):
        """
        Runs the given command line

        :param herald_svc: Herald service
        :param message: Received message
        """
        # Find the session
        session_id = message.content['session_id']
        try:
            with self.__lock:
                session = self._sessions[session_id]
        except KeyError:
            # Unknown session
            _logger.warning("Unknown session for execution: %s", session_id)
            herald_svc.reply(message, session_id, MSG_CLIENT_CLOSE)
            return

        # Execute the command
        result = self._shell.execute(message.content['line'], session)

        # Return the result
        herald_svc.reply(message, result)

    def _close_session(self, herald_svc, message):
        """
        Closes the session given in the message

        :param herald_svc: Herald service
        :param message: Received message
        """
        session_id = message.content
        try:
            with self.__lock:
                del self._sessions[session_id]
        except KeyError:
            # Unknown session
            _logger.warning("Unknown session to close: %s", session_id)
        else:
            # Session close
            _logger.debug("Closed session: %s", session_id)
