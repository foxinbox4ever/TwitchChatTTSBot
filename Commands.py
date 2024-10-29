import time
import logging

from TTS import text_to_shout

class BaseCommand:
    def __init__(self, name, cooldown=0):
        self.name = name
        self.cooldown = cooldown
        self.last_used = 0

    def can_execute(self):
        """Check if the command can be executed based on cooldown."""
        current_time = time.time()
        if current_time - self.last_used >= self.cooldown:
            self.last_used = current_time
            return True
        return False

    def execute(self, connection, username, message, channel):
        """Placeholder for execution logic. Should be overridden."""
        raise NotImplementedError("Execute method not implemented.")

class HelpCommand(BaseCommand):
    def __init__(self):
        super().__init__(name="!help", cooldown=5)

    def execute(self, connection, username, message, channel):
        if self.can_execute():
            response = f"Hello @{username}, here are the available commands: {commands_list}"
            connection.privmsg(channel, response)
            logging.info(f"Executed {self.name} command for {username}")
        else:
            logging.info(f"{self.name} command is on cooldown.")

class ShoutCommand(BaseCommand):  # Fixed class definition
    def __init__(self):
        super().__init__(name="!shout", cooldown=10)

    async def execute(self, connection, username, message, channel):
        if self.can_execute():
            message = message.split("!shout")[1].strip()
            tts_message = f"{username} shouts {message}"
            await text_to_shout(tts_message)  # Use await
            logging.info(f"Executed {self.name} command for {username}")
        else:
            logging.info(f"{self.name} command is on cooldown.")

# This dictionary helps map command names to their respective classes
COMMANDS = {
    "!help": HelpCommand(),
    "!shout": ShoutCommand(),
}
commands_list = ', '.join(COMMANDS.keys())
