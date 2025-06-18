import os
import time
import logging
import random
import requests
from datetime import datetime, timedelta
import asyncio
import json
import re
import aiohttp

from BotTTS import text_to_shout, text_to_speech
from Viewers import viewers
from config import settings_data, get_social_links, OBS_Browser_Source

class BaseCommand:
    user_cooldowns = {}  # Store cooldowns for each user per command

    def __init__(self, name, cooldown=0, description="No description available"):
        self.name = name
        self.cooldown = cooldown
        self.description = description

    def can_execute(self, username):
        """Check if the command can be executed based on per-user cooldown for that specific command."""
        current_time = time.time()

        if username not in BaseCommand.user_cooldowns:
            BaseCommand.user_cooldowns[username] = {}

        # Retrieve the last used time for this command for the user
        last_used = BaseCommand.user_cooldowns[username].get(self.name, 0)

        if current_time - last_used >= self.cooldown:
            # Update the cooldown time for the user and the current command
            BaseCommand.user_cooldowns[username][self.name] = current_time
            return True

        return False

    def execute(self, connection, username, message, channel, token, client_id, broadcaster_id):
        """Placeholder for execution logic. Should be overridden."""
        raise NotImplementedError("Execute method not implemented.")

    def on_cooldown(self, connection, username, channel):
        """Handle the cooldown response."""
        current_time = time.time()

        # Retrieve the last used time for the specific command for the user
        user_cooldowns = BaseCommand.user_cooldowns.get(username, {})

        # Get the last time the specific command was used by the user, default to 0 if not found
        last_used = user_cooldowns.get(self.name, 0)

        # Calculate the time left on the cooldown
        time_left = self.cooldown - (current_time - last_used)

        # If time_left is less than 0, it means the cooldown has expired, so set time_left to 0
        time_left = max(time_left, 0)

        response = f"@{username}, {self.name} command is on cooldown. Please wait {time_left:.1f} seconds."
        connection.privmsg(channel, response)
        logging.info(f"{self.name} command is on cooldown for user {username}.")


class HelpCommand(BaseCommand):
    def __init__(self):
        super().__init__(name="!help", cooldown=5, description="Displays a list of available commands or details about a specific command.")

    def execute(self, connection, username, message, channel, token, client_id, broadcaster_id):
        if self.can_execute(username):
            # Check if the user has specified a command for help
            message_parts = message.split()
            if len(message_parts) > 1:
                # Command specified (e.g., !help !shout)
                command_name = message_parts[1]
                if not command_name.startswith("!"):
                    command_name = "!" + command_name # Corrected the typo here

                command = COMMANDS.get(command_name)

                if command:
                    response = f"@{username}, the '{command_name}' command: {command.description}"
                else:
                    response = f"@{username}, the command '{command_name}' does not exist."
            else:
                # No command specified, list all commands
                response = f"Hello @{username}, here are the available commands: {commands_list}"

            connection.privmsg(channel, response)
            logging.info(f"Executed {self.name} command for {username}")
        else:
            self.on_cooldown(connection, username, channel)


class ShoutCommand(BaseCommand):
    def __init__(self):
        super().__init__(name="!shout", cooldown=10, description="does TTS a little louder")

    async def execute(self, connection, username, message, channel, token, client_id, broadcaster_id):
        if self.can_execute(username):
            message = message.split("!shout", 1)[1].strip()
            tts_message = f"{username} shouts {message}"
            await text_to_shout(tts_message)
            logging.info(f"Executed {self.name} command for {username}")
        else:
            self.on_cooldown(connection, username, channel)

class RaffleCommand(BaseCommand):
    def __init__(self):
        super().__init__(name="!raffle", cooldown=5, description="picks a random viewer in the chat")

    async def execute(self, connection, username, message, channel, token, client_id, broadcaster_id):
        if self.can_execute(username):
            raffle_message = message.split("!raffle", 1)
            if len(raffle_message) > 1 and "followers" in raffle_message[1].strip().lower():
                eligible_viewers = [viewer.username for viewer in viewers if viewer.following and viewer.username != username]
            elif len(raffle_message) > 1 and "subs" in raffle_message[1].strip().lower():
                eligible_viewers = [viewer.username for viewer in viewers if viewer.subscribed and viewer.username != username]
            else:
                eligible_viewers = [viewer.username for viewer in viewers if viewer.username != username]

            chosen_viewer = random.choice(eligible_viewers) if eligible_viewers else " no eligible viewers"
            response = f"Hello @{username}, the winner of your raffle is: @{chosen_viewer}"
            connection.privmsg(channel, response)
            logging.info(f"Executed {self.name} command for {username}")
        else:
            self.on_cooldown(connection, username, channel)

class LurkCommand(BaseCommand):
    def __init__(self):
        super().__init__(name="!lurk", cooldown=10, description="notifies the streamer your lurking")

    async def execute(self, connection, username, message, channel, token, client_id, broadcaster_id):
        if self.can_execute(username):
            tts_message = f"{username} is watching you!"
            await text_to_speech(tts_message)
            response = f"Enjoy lurking @{username}"
            connection.privmsg(channel, response)
            logging.info(f"Executed {self.name} command for {username}")
        else:
            self.on_cooldown(connection, username, channel)

class SubsCommand(BaseCommand):
    def __init__(self):
        super().__init__(name="!subs", cooldown=10, description="displays all the subs of the channel")

    async def execute(self, connection, username, message, channel, token, client_id, broadcaster_id):
        if self.can_execute(username):
            headers = {
                "Authorization": f"Bearer {token}",
                "Client-Id": client_id
            }
            url = f"https://api.twitch.tv/helix/subscriptions?broadcaster_id={broadcaster_id}"

            try:
                response = requests.get(url, headers=headers)
                response.raise_for_status()
                data = response.json()

                subscribers = [sub['user_name'] for sub in data['data']]
                subscriber_list = ', '.join(subscribers) if subscribers else "No subscribers found."
                response_msg = f"@{username}, here are the subscribers: {subscriber_list}"
            except requests.exceptions.RequestException as e:
                logging.error(f"Error fetching subscribers: {e}")
                response_msg = "Failed to retrieve subscribers. Please try again later."

            connection.privmsg(channel, response_msg)
            logging.info(f"Executed {self.name} command for {username}")
        else:
            self.on_cooldown(connection, username, channel)


class DiscordCommand(BaseCommand):
    def __init__(self):
        super().__init__(name="!discord", cooldown=10, description="provides a discord link")

    async def execute(self, connection, username, message, channel, token, client_id, broadcaster_id):
        if self.can_execute(username):
            social_links = get_social_links()
            discord_link = next((value for key, value in social_links.items() if key.lower() == "discord"), None)

            if not discord_link:
                response = f"@{username}, no Discord link has been provided."
            else:
                response = f"@{username}, join the Discord here: {discord_link}"

            connection.privmsg(channel, response)
            logging.info(f"Executed {self.name} command for {username}")
        else:
            self.on_cooldown(connection, username, channel)


class HugCommand(BaseCommand):
    def __init__(self):
        super().__init__(name="!hug", cooldown=10, description="hugs the provided user or everyone. To hug a specific user type !hug username (the username of the person you want to hug)")

    async def execute(self, connection, username, message, channel, token, client_id, broadcaster_id):
        if self.can_execute(username):
            # Make sure to split by " " and ignore the command part (!hug)
            parts = message.split(" ", 1)
            if len(parts) > 1:
                # If there's a name after the command, use that name
                target_user = parts[1].strip()
                if "@" in target_user:
                    target_user = target_user.strip("@")

                response = f"@{username} hugs @{target_user}"
            else:
                # If no name is provided, send a default message
                response = f"@{username} hugs everyone in the chat!"
            connection.privmsg(channel, response)
            logging.info(f"Executed {self.name} command for {username}")
        else:
            self.on_cooldown(connection, username, channel)


class BrainCellsCommand(BaseCommand):
    def __init__(self):
        super().__init__(name="!braincells", cooldown=10, description="tells you how many braincells you have")

    async def execute(self, connection, username, message, channel, token, client_id, broadcaster_id):
        if self.can_execute(username):
            braincells = random.randint(0, 100)
            response = f"@{username} has {braincells} braincells"
            connection.privmsg(channel, response)
            logging.info(f"Executed {self.name} command for {username}")
        else:
            self.on_cooldown(connection, username, channel)


class UptimeCommand(BaseCommand):
    def __init__(self):
        super().__init__(name="!uptime", cooldown=5, description="displays how long I have been streaming")

    async def execute(self, connection, username, message, channel, token, client_id, broadcaster_id):
        if self.can_execute(username):
            headers = {
                "Authorization": f"Bearer {token}",
                "Client-Id": client_id
            }
            url = f"https://api.twitch.tv/helix/streams?user_id={broadcaster_id}"

            try:
                response = requests.get(url, headers=headers)
                response.raise_for_status()
                data = response.json()

                if data['data']:
                    # Extract stream start time
                    stream_start = data['data'][0]['started_at']
                    # Convert to datetime object
                    stream_start = datetime.strptime(stream_start, '%Y-%m-%dT%H:%M:%SZ')
                    # Calculate uptime
                    current_time = datetime.utcnow()
                    uptime = current_time - stream_start

                    # Format uptime as hours, minutes, and seconds
                    formatted_uptime = str(timedelta(seconds=int(uptime.total_seconds())))
                    response_msg = f"@{username}, the stream has been live for {formatted_uptime}."
                else:
                    response_msg = f"@{username}, the stream is currently offline."

            except requests.exceptions.RequestException as e:
                logging.error(f"Error fetching uptime: {e}")
                response_msg = "Failed to retrieve uptime. Please try again later."

            # Send the uptime message to Twitch chat
            connection.privmsg(channel, response_msg)
            logging.info(f"Executed {self.name} command for {username}")
        else:
            self.on_cooldown(connection, username, channel)


class DadJokeCommand(BaseCommand):
    def __init__(self):
        super().__init__(name="!dadjoke", cooldown=100, description="tells you one or more dad jokes.")

    async def execute(self, connection, username, message, channel, token, client_id, broadcaster_id):
        if self.can_execute(username):
            # Base URL for JokeAPI, which returns either single or multiple jokes
            joke_url = "https://v2.jokeapi.dev/joke/Programming?type=single&lang=en"

            try:
                # Split message to check if there's an amount specified
                message_parts = message.split(" ", 1)
                joke = ""

                if len(message_parts) > 1:
                    # Get the number of jokes requested from the message
                    joke_amount = int(message_parts[1])

                    # Ensure joke_amount doesn't exceed a reasonable maximum (e.g., 3)
                    joke_amount = min(joke_amount, 3)

                    # Add the amount parameter to the URL for multiple jokes
                    url_with_amount = f"{joke_url}&amount={joke_amount}"

                    # Fetch jokes from the API
                    response = requests.get(url_with_amount)
                    response.raise_for_status()
                    joke_data = response.json()

                    # Collect all jokes from the response
                    if 'jokes' in joke_data:  # When multiple jokes are returned
                        for joke_entry in joke_data['jokes']:
                            if joke_entry['type'] == 'single':
                                joke += joke_entry['joke'] + " "
                            else:  # For 'twopart' jokes (setup and delivery)
                                joke += f"{joke_entry['setup']} - {joke_entry['delivery']} "

                    else:
                        # If there's a problem, just return one joke from the original URL
                        joke = "Sorry, couldn't fetch multiple jokes. Here's one: "
                        joke_entry = joke_data
                        if joke_entry['type'] == 'single':
                            joke += joke_entry['joke']
                        else:
                            joke += f"{joke_entry['setup']} - {joke_entry['delivery']}"

                else:
                    # If no joke amount is specified, fetch just one joke
                    response = requests.get(joke_url)
                    response.raise_for_status()
                    joke_data = response.json()

                    # Handle single joke response
                    if joke_data['type'] == 'single':
                        joke = joke_data['joke']
                    else:
                        joke = f"{joke_data['setup']} - {joke_data['delivery']}"

                # Ensure no newline or carriage return characters in the joke
                joke = joke.replace('\n', ' ').replace('\r', ' ')

                # Check if joke message exceeds Twitch's character limit (500 characters)
                if len(joke) > 500:
                    joke = joke[:500]  # Truncate the joke to fit the 500-character limit

                # Send the joke(s) to Twitch chat
                response_msg = f"@{username}, here's your dad joke(s): {joke}"
                connection.privmsg(channel, response_msg)
                logging.info(f"Executed {self.name} command for {username}")

            except requests.exceptions.RequestException as e:
                logging.error(f"Error fetching dad joke: {e}")
                response_msg = "Sorry, I couldn't fetch a dad joke right now. Please try again later."
                connection.privmsg(channel, response_msg)
        else:
            self.on_cooldown(connection, username, channel)


class SocialsCommand(BaseCommand):
    def __init__(self):
        super().__init__(name="!socials", cooldown=10, description="provides a link to all my socials")

    async def execute(self, connection, username, message, channel, token, client_id, broadcaster_id):
        if self.can_execute(username):
            social_links = get_social_links()

            if not social_links:
                response = f"@{username}, no social links have been provided."
            else:
                # Create a string of "Name: URL" entries
                link_display = " | ".join(
                    f"{name.capitalize()}: {url}" for name, url in social_links.items()
                )
                response = f"@{username}, here are all my socials: {link_display}"

            connection.privmsg(channel, response)
            logging.info(f"Executed {self.name} command for {username}")
        else:
            self.on_cooldown(connection, username, channel)


from TTSObsWebsocket import broadcast_message, connected_clients

class VoteCommand(BaseCommand):
    active_vote = None
    vote_is_active = False
    vote_end_time = None
    vote_responses = {}

    def __init__(self):
        super().__init__(name="!vote", cooldown=5,
                         description="Starts a vote if you're a mod, or votes if a vote is active")

    async def execute(self, connection, username, message, channel, token, client_id, broadcaster_id):
        if not self.can_execute(username):
            self.on_cooldown(connection, username, channel)
            return

        if self.__class__.vote_is_active:
            connection.privmsg(channel, "⚠️ A vote is already active!")
            return

        logging.info(f"Executed {self.name} command for {username}")
        parts = message.split(" ", 1)

        # Only moderators can start a vote
        if username not in [viewer.username for viewer in viewers if viewer.mod]:
            connection.privmsg(channel, f"@{username}, only moderators can start a vote!")
            return

        if len(parts) > 1 and "?" in parts[1]:
            question_and_options = parts[1]
            try:
                question, options_str = question_and_options.split("?", 1)
                options = re.findall(r'\d+\.(.*?)(?=\s*\d+\.|$)', options_str.strip())
                options = [opt.strip() for opt in options if opt.strip()]

                if len(options) < 2:
                    connection.privmsg(channel, "You must provide at least 2 options.")
                    return

                logging.info(
                    f"Starting vote initiated by {username}: '{question.strip()}?' "
                    f"with options: {', '.join(f'{i + 1}. {opt}' for i, opt in enumerate(options))}"
                )

                if OBS_Browser_Source:
                    self.__class__.active_vote = {
                        "question": question.strip() + "?",
                        "options": options,
                        "started_by": username
                    }
                    self.__class__.vote_end_time = time.time() + 60
                    self.__class__.vote_responses = {}
                    self.__class__.vote_is_active = True

                    vote_payload = {
                        "vote": {
                            "question": self.active_vote["question"],
                            "options": self.active_vote["options"],
                            "timeRemaining": int(self.vote_end_time - time.time())
                        }
                    }
                    await broadcast_message(username, "", 0)
                    await asyncio.sleep(0.1)
                    await asyncio.gather(*[
                        client.send(json.dumps(vote_payload)) for client in connected_clients
                    ])
                    logging.info(f"Vote sent to browser source: {vote_payload}")
                else:
                    logging.info("OBS web browser source is offline, creating Twitch poll instead.")
                    success, result = await create_twitch_poll(token, client_id, broadcaster_id, question, options)
                    if success:
                        connection.privmsg(channel, f"📊 A Twitch poll has been started! Vote using the poll above!")
                    else:
                        connection.privmsg(channel, f"⚠️ Failed to create Twitch poll: {result}")
                        options_text = " | ".join([f"{i + 1}. {opt}" for i, opt in enumerate(options)])
                        connection.privmsg(channel,
                                           f"@{username} started a vote: {question.strip()}? Options: {options_text}")
                        connection.privmsg(channel, "Type the number of your choice to vote!")

            except Exception as e:
                logging.error(f"Error while processing vote command: {e}")
                connection.privmsg(channel, "⚠️ Error starting vote.")

    @classmethod
    async def handle_vote_response(cls, connection, username, message, channel):
        logging.info(f"Handling vote response from {username}")

        if not cls.active_vote or time.time() >= cls.vote_end_time:
            logging.info("No active vote or vote has ended.")
            return

        if not message.strip().isdigit():
            return

        choice = int(message.strip())
        if 1 <= choice <= len(cls.active_vote["options"]):
            cls.vote_responses[username] = choice
            logging.info(f"Vote response for {username} was {choice}")

            results = {}
            for vote in cls.vote_responses.values():
                results[vote] = results.get(vote, 0) + 1

            vote_counts = [results.get(i + 1, 0) for i in range(len(cls.active_vote["options"]))]

            if OBS_Browser_Source:
                vote_payload = {
                    "vote": {
                        "question": cls.active_vote["question"],
                        "options": cls.active_vote["options"],
                        "timeRemaining": int(cls.vote_end_time - time.time())
                    },
                    "voteCounts": vote_counts
                }
                await asyncio.gather(*[
                    client.send(json.dumps(vote_payload)) for client in connected_clients
                ])
                logging.info(f"Vote response sent to browser source: {vote_payload}")

    @classmethod
    async def handle_end_of_vote(cls, connection, channel):
        if cls.vote_end_time and time.time() >= cls.vote_end_time:
            logging.info("Handling end of vote.")
            cls.vote_is_active = False

            if not OBS_Browser_Source:
                results = {}
                for vote in cls.vote_responses.values():
                    results[vote] = results.get(vote, 0) + 1

                result_lines = []
                for i, option in enumerate(cls.active_vote["options"]):
                    count = results.get(i + 1, 0)
                    result_lines.append(f"{i + 1}. {option}: {count} votes")

                result_message = f"🗳️ Final vote results for '{cls.active_vote['question']}': " + " | ".join(
                    result_lines)
                connection.privmsg(channel, result_message)
                logging.info("Vote ended and results sent to chat.")

            cls.active_vote = None
            cls.vote_responses = {}
            cls.vote_end_time = None

async def create_twitch_poll(token, client_id, broadcaster_id, question, options, duration=60):
    """
    Creates a Twitch poll using the Helix API.
    """
    headers = {
        "Authorization": f"Bearer {token}",
        "Client-ID": client_id,
        "Content-Type": "application/json"
    }

    payload = {
        "broadcaster_id": broadcaster_id,
        "title": question.strip()[:60],
        "choices": [{"title": opt[:25]} for opt in options[:5]],  # Max 5 options
        "duration": duration
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post("https://api.twitch.tv/helix/polls", headers=headers, json=payload) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    logging.info(f"Twitch poll successfully created: {result}")
                    return True, result
                else:
                    error_text = await resp.text()
                    logging.warning(f"Failed to create Twitch poll: {resp.status} - {error_text}")
                    return False, error_text
    except Exception as e:
        logging.error(f"Exception during Twitch poll creation: {e}")
        return False, str(e)


# This dictionary helps map command names to their respective classes
COMMANDS = {
    "!help": HelpCommand(),
    "!shout": ShoutCommand(),
    "!raffle": RaffleCommand(),
    "!lurk": LurkCommand(),
    "!subs": SubsCommand(),
    "!discord": DiscordCommand(),
    "!hug": HugCommand(),
    "!braincells": BrainCellsCommand(),
    "!uptime": UptimeCommand(),
    "!dadjoke": DadJokeCommand(),
    "!socials": SocialsCommand(),
    "!vote": VoteCommand()
}
commands_list = ', '.join(COMMANDS.keys())