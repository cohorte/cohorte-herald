from .client import CommandBot

import itertools
import string
import time

# ------------------------------------------------------------------------------

class BasicCommandsBot(CommandBot):
    def cmd_part(self, connection, sender, target, payload):
        """
        Asks the bot to leave a channel
        """
        if payload:
            connection.part(payload)
        else:
            raise ValueError("No channel given")


    def cmd_join(self, connection, sender, target, payload):
        """
        Asks the bot to join a channel
        """
        if payload:
            connection.join(payload)
        else:
            raise ValueError("No channel given")

    def cmd_echo(self, connection, sender, target, payload):
        """
        Echoes the given payload
        """
        connection.privmsg(target, payload or "Hello, {0}".format(sender))


    def cmd_close(self, connection, sender, target, payload):
        """
        Closes the bot
        """
        self.close()


    def cmd_work(self, connection, sender, target, payload):
        """
        Does some job
        """
        connection.action(target, "is doing something...")
        time.sleep(int(payload or "5"))
        connection.action(target, "has finished !")
        connection.privmsg(target, "My answer is: 42.")


    def cmd_send(self, connection, sender, target, payload):
        """
        """
        cycle = itertools.cycle(string.digits)
        content = ''.join(next(cycle) for _ in range(int(payload or 600)))
        self._safe_send2(connection, target, "some-id", content)
