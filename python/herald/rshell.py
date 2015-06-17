#!/usr/bin/python
# -- Content-Encoding: UTF-8 --
"""
Pelix Shell commands for Herald

:author: Thomas Calmant
:copyright: Copyright 2014, isandlaTech
:license: Apache License 2.0
:version: 0.0.3
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

# Module version
__version_info__ = (0, 0, 3)
__version__ = ".".join(str(x) for x in __version_info__)

# Documentation strings format
__docformat__ = "restructuredtext en"

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

# ------------------------------------------------------------------------------


@ComponentFactory("herald-remote-shell-client-factory")
@Requires("_herald", herald.SERVICE_HERALD)
@Provides((pelix.shell.SERVICE_SHELL_COMMAND, herald.SERVICE_LISTENER))
@Property('_filters', herald.PROP_FILTERS, ['{0}/*'.format(_PREFIX_CLIENT)])
@Instantiate("herald-remote-shell-client")
class HeraldRemoteShellClient(object):
    """
    Herald remote shell command

    TODO: close session on peer unregistration
    """
    def __init__(self):
        """
        Sets up the object
        """
        self._herald = None
        # Activate session ID => ShellSession
        self._sessions = {}

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

        prompt_str = "({0}) {1}".format(
            shell_info['peer_uid'], shell_info['ps1'])

        # Setup the session variables
        session.set(SESSION_SHELL_RUNNING, True)

        # Store the session
        self._sessions[session_id] = session

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

                # Prepare arguments
                content = {"line": line, "session_id": session_id}
                result_msg = self._herald.send(
                    peer, beans.Message(MSG_SERVER_COMMAND, content))
                session.write_line(prompt_str, result_msg.content)
        except (HeraldException, KeyError) as ex:
            # Error sending message
            _logger.exception("Error sending command to peer: %s", ex)
            session.write_line("Error sending command to peer: {0}", ex)
        except (KeyboardInterrupt, EOFError):
            # Ctrl+C or Ctrl+D: stop the shell
            pass
        finally:
            try:
                # Clear references
                del self._sessions[session_id]
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
                    session.set(SESSION_SHELL_RUNNING, False)
                    herald_svc.reply(message, None, MSG_SERVER_CLOSE)

        elif kind == "close":
            # Clean up a session
            session_id = message.content
            try:
                session = self._sessions.pop(session_id)
                session.write_line("Session closed. Press Enter to exit.")
                session.set(SESSION_SHELL_RUNNING, False)
            except KeyError:
                _logger.warning("No session with ID: %s", session_id)

        elif kind == "error":
            _logger.warning("Error on shell server side: %s", message.content)

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
        if prompt_msg.content is None:
            # Client closed its shell
            raise EOFError

        return prompt_msg.content


@ComponentFactory("herald-remote-shell-server-factory")
@Requires("_directory", herald.SERVICE_DIRECTORY)
@Requires("_herald", herald.SERVICE_HERALD)
@Requires("_shell", pelix.shell.SERVICE_SHELL)
@Provides(herald.SERVICE_LISTENER)
@Property('_filters', herald.PROP_FILTERS, ['{0}/*'.format(_PREFIX_SERVER)])
@Instantiate("herald-remote-shell-server")
class HeraldRemoteShellServer(object):
    """
    Herald remote shell server

    TODO: close session on peer unregistration
    """
    def __init__(self):
        """
        Sets up the object
        """
        # Injected services
        self._directory = None
        self._shell = None

        # Activate session ID => ShellSession
        self._sessions = {}

        # Local peer UID
        self._local_uid = None

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

        # Clear session
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
            del self._sessions[session_id]
        except KeyError:
            # Unknown session
            _logger.warning("Unknown session to close: %s", session_id)
        else:
            # Session close
            _logger.debug("Closed session: %s", session_id)
