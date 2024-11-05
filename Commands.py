import time
import logging
import random

from TTS import text_to_shout
from Viewers import viewers

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


class RaffleCommand(BaseCommand):
    def __init__(self):
        super().__init__(name="raffle", cooldown=5)

    async def execute(self, connection, username, message, channel):
        if self.can_execute():
            logging.info(f"Viewers: {[viewer.username for viewer in viewers]}")
            logging.info(f"Followers: {[viewer.username for viewer in viewers if viewer.following]}")
            logging.info(f"Subscribers: {[viewer.username for viewer in viewers if viewer.subscribed]}")

            raffle_message = message.split("!raffle", 1)
            if len(raffle_message) > 1 and "followers" in raffle_message[1].strip().lower():
                # Choose from followers only
                eligible_viewers = [viewer.username for viewer in viewers if viewer.following and viewer.username != username]
            elif len(raffle_message) > 1 and "subs" in raffle_message[1].strip().lower():
                # Choose from subscribers only
                eligible_viewers = [viewer.username for viewer in viewers if viewer.subscribed and viewer.username != username]
            else:
                # Choose from all viewers
                eligible_viewers = [viewer.username for viewer in viewers if viewer.username != username]

            chosen_viewer = random.choice(eligible_viewers) if eligible_viewers else f" no {raffle_message[1]} viewers available"

            logging.info(f"Raffle outcome: {chosen_viewer}")
            response = f"Hello @{username}, the winner of your raffle is: @{chosen_viewer}"
            connection.privmsg(channel, response)
            logging.info(f"Executed {self.name} command for {username}")
        else:
            logging.info(f"{self.name} command is on cooldown.")


# This dictionary helps map command names to their respective classes
COMMANDS = {
    "!help": HelpCommand(),
    "!shout": ShoutCommand(),
    "!raffle": RaffleCommand(),
}
commands_list = ', '.join(COMMANDS.keys())