import os
import time
import logging
import random
import requests
from datetime import datetime, timedelta, timezone
import asyncio
import json
import re
import aiohttp

from BotTTS import text_to_shout, text_to_speech
from Viewers import viewers
from config import settings_data, get_social_links, OBS_Browser_Source, Sanity_Bar


class BaseCommand:
    user_cooldowns = {}
    platforms = ("Twitch", "YouTube", "TikTok")

    def __init__(self, name, cooldown=0, description="No description available"):
        self.name = name
        self.cooldown = cooldown
        self.description = description

    def can_execute(self, username):
        current_time = time.time()

        if username not in BaseCommand.user_cooldowns:
            BaseCommand.user_cooldowns[username] = {}

        last_used = BaseCommand.user_cooldowns[username].get(self.name, 0)

        if current_time - last_used >= self.cooldown:
            BaseCommand.user_cooldowns[username][self.name] = current_time
            return True

        return False

    def execute(self, send_reply, username, message, channel, token, client_id, broadcaster_id):
        raise NotImplementedError("Execute method not implemented.")

    def on_cooldown(self, send_reply, username):
        current_time = time.time()
        last_used = BaseCommand.user_cooldowns.get(username, {}).get(self.name, 0)
        time_left = max(self.cooldown - (current_time - last_used), 0)
        send_reply(f"@{username}, {self.name} command is on cooldown. Please wait {time_left:.1f} seconds.")
        logging.info(f"{self.name} command is on cooldown for user {username}.")


class HelpCommand(BaseCommand):
    def __init__(self):
        super().__init__(name="!help", cooldown=5, description="Displays a list of available commands or details about a specific command.")

    async def execute(self, send_reply, username, message, channel, token, client_id, broadcaster_id):
        if self.can_execute(username):
            platform = channel if channel in ("YouTube", "TikTok") else "Twitch"
            platform_commands = {k: v for k, v in COMMANDS.items() if platform in v.platforms}

            message_parts = message.split()
            if len(message_parts) > 1:
                command_name = message_parts[1]
                if not command_name.startswith("!"):
                    command_name = "!" + command_name

                command = platform_commands.get(command_name)

                if command:
                    response = f"@{username}, the '{command_name}' command: {command.description}"
                else:
                    response = f"@{username}, the command '{command_name}' does not exist."
            else:
                cmd_list = ', '.join(platform_commands.keys())
                response = f"Hello @{username}, here are the available commands: {cmd_list}"

            send_reply(response)
            logging.info(f"Executed {self.name} command for {username}")
        else:
            self.on_cooldown(send_reply, username)


class ShoutCommand(BaseCommand):
    def __init__(self):
        super().__init__(name="!shout", cooldown=10, description="does TTS a little louder")

    async def execute(self, send_reply, username, message, channel, token, client_id, broadcaster_id):
        if self.can_execute(username):
            platform = channel if channel in ("YouTube", "TikTok") else "Twitch"
            message = message.split("!shout", 1)[1].strip()
            tts_message = f"{username} shouts {message}"
            await text_to_shout(tts_message, platform=platform)
            logging.info(f"Executed {self.name} command for {username}")
        else:
            self.on_cooldown(send_reply, username)


class RaffleCommand(BaseCommand):
    def __init__(self):
        super().__init__(name="!raffle", cooldown=5, description="picks a random viewer in the chat")

    async def execute(self, send_reply, username, message, channel, token, client_id, broadcaster_id):
        if self.can_execute(username):
            raffle_message = message.split("!raffle", 1)
            filter_type = raffle_message[1].strip().lower() if len(raffle_message) > 1 else ""

            if channel == "YouTube":
                from Viewers import youtube_viewers
                eligible_viewers = [v for v in youtube_viewers if v != username.lower()]
            elif channel == "TikTok":
                from Viewers import tiktok_viewers
                eligible_viewers = [v for v in tiktok_viewers if v != username.lower()]
            elif "followers" in filter_type:
                eligible_viewers = [viewer.username for viewer in viewers if viewer.following and viewer.username != username]
            elif "subs" in filter_type:
                eligible_viewers = [viewer.username for viewer in viewers if viewer.subscribed and viewer.username != username]
            else:
                eligible_viewers = [viewer.username for viewer in viewers if viewer.username != username]

            chosen_viewer = random.choice(eligible_viewers) if eligible_viewers else "no eligible viewers"
            send_reply(f"Hello @{username}, the winner of your raffle is: @{chosen_viewer}")
            logging.info(f"Executed {self.name} command for {username}")
        else:
            self.on_cooldown(send_reply, username)


class LurkCommand(BaseCommand):
    def __init__(self):
        super().__init__(name="!lurk", cooldown=10, description="notifies the streamer your lurking")

    async def execute(self, send_reply, username, message, channel, token, client_id, broadcaster_id):
        if self.can_execute(username):
            tts_message = f"{username} is watching you!"
            await text_to_speech(tts_message)
            send_reply(f"Enjoy lurking @{username}")
            logging.info(f"Executed {self.name} command for {username}")
        else:
            self.on_cooldown(send_reply, username)


class SubsCommand(BaseCommand):
    platforms = ("Twitch",)

    def __init__(self):
        super().__init__(name="!subs", cooldown=10, description="displays all the subs of the channel")

    async def execute(self, send_reply, username, message, channel, token, client_id, broadcaster_id):
        if self.can_execute(username):
            if channel in ("YouTube", "TikTok"):
                send_reply(f"@{username}, !subs is only available on Twitch.")
                return

            headers = {
                "Authorization": f"Bearer {token}",
                "Client-Id": client_id
            }
            url = f"https://api.twitch.tv/helix/subscriptions?broadcaster_id={broadcaster_id}&first=100"

            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, headers=headers) as resp:
                        data = await resp.json()

                total = data.get("total", 0)
                subscribers = [sub['user_name'] for sub in data.get('data', [])]
                if not subscribers:
                    response_msg = f"@{username}, no subscribers found."
                else:
                    sub_list = ', '.join(subscribers)
                    prefix = f"@{username}, subscribers ({total} total): "
                    if len(prefix) + len(sub_list) > 490:
                        sub_list = sub_list[:490 - len(prefix) - 3] + "..."
                    response_msg = prefix + sub_list
            except Exception as e:
                logging.error(f"Error fetching subscribers: {e}")
                response_msg = "Failed to retrieve subscribers. Please try again later."

            send_reply(response_msg)
            logging.info(f"Executed {self.name} command for {username}")
        else:
            self.on_cooldown(send_reply, username)


class DiscordCommand(BaseCommand):
    def __init__(self):
        super().__init__(name="!discord", cooldown=10, description="provides a discord link")

    async def execute(self, send_reply, username, message, channel, token, client_id, broadcaster_id):
        if self.can_execute(username):
            social_links = get_social_links()
            discord_link = next((value for key, value in social_links.items() if key.lower() == "discord"), None)

            if not discord_link:
                response = f"@{username}, no Discord link has been provided."
            else:
                response = f"@{username}, join the Discord here: {discord_link}"

            send_reply(response)
            logging.info(f"Executed {self.name} command for {username}")
        else:
            self.on_cooldown(send_reply, username)


class HugCommand(BaseCommand):
    def __init__(self):
        super().__init__(name="!hug", cooldown=10, description="hugs the provided user or everyone. To hug a specific user type !hug username (the username of the person you want to hug)")

    async def execute(self, send_reply, username, message, channel, token, client_id, broadcaster_id):
        if self.can_execute(username):
            parts = message.split(" ", 1)
            if len(parts) > 1:
                target_user = parts[1].strip()
                if "@" in target_user:
                    target_user = target_user.strip("@")
                response = f"@{username} hugs @{target_user}"
            else:
                response = f"@{username} hugs everyone in the chat!"
            send_reply(response)
            logging.info(f"Executed {self.name} command for {username}")
        else:
            self.on_cooldown(send_reply, username)


class BrainCellsCommand(BaseCommand):
    def __init__(self):
        super().__init__(name="!braincells", cooldown=10, description="tells you how many braincells you have")

    async def execute(self, send_reply, username, message, channel, token, client_id, broadcaster_id):
        if self.can_execute(username):
            braincells = random.randint(0, 100)
            send_reply(f"@{username} has {braincells} braincells")
            logging.info(f"Executed {self.name} command for {username}")
        else:
            self.on_cooldown(send_reply, username)


class UptimeCommand(BaseCommand):
    platforms = ("Twitch",)

    def __init__(self):
        super().__init__(name="!uptime", cooldown=5, description="displays how long I have been streaming")

    async def execute(self, send_reply, username, message, channel, token, client_id, broadcaster_id):
        if self.can_execute(username):
            if channel in ("YouTube", "TikTok"):
                send_reply(f"@{username}, !uptime is only available on Twitch.")
                return

            headers = {
                "Authorization": f"Bearer {token}",
                "Client-Id": client_id
            }
            url = f"https://api.twitch.tv/helix/streams?user_id={broadcaster_id}"

            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, headers=headers) as resp:
                        data = await resp.json()

                if data['data']:
                    stream_start = datetime.strptime(data['data'][0]['started_at'], '%Y-%m-%dT%H:%M:%SZ')
                    stream_start = stream_start.replace(tzinfo=timezone.utc)
                    uptime = datetime.now(timezone.utc) - stream_start
                    formatted_uptime = str(timedelta(seconds=int(uptime.total_seconds())))
                    response_msg = f"@{username}, the stream has been live for {formatted_uptime}."
                else:
                    response_msg = f"@{username}, the stream is currently offline."

            except Exception as e:
                logging.error(f"Error fetching uptime: {e}")
                response_msg = "Failed to retrieve uptime. Please try again later."

            send_reply(response_msg)
            logging.info(f"Executed {self.name} command for {username}")
        else:
            self.on_cooldown(send_reply, username)


class DadJokeCommand(BaseCommand):
    def __init__(self):
        super().__init__(name="!dadjoke", cooldown=100, description="tells you one or more dad jokes.")

    async def execute(self, send_reply, username, message, channel, token, client_id, broadcaster_id):
        if self.can_execute(username):
            joke_url = "https://v2.jokeapi.dev/joke/Programming?type=single&lang=en"

            try:
                message_parts = message.split(" ", 1)
                joke = ""

                async with aiohttp.ClientSession() as session:
                    if len(message_parts) > 1:
                        try:
                            joke_amount = min(int(message_parts[1]), 3)
                        except ValueError:
                            send_reply(f"@{username}, usage: !dadjoke [number of jokes, max 3]")
                            return

                        async with session.get(f"{joke_url}&amount={joke_amount}") as resp:
                            joke_data = await resp.json(content_type=None)

                        if 'jokes' in joke_data:
                            for entry in joke_data['jokes']:
                                if entry['type'] == 'single':
                                    joke += entry['joke'] + " "
                                else:
                                    joke += f"{entry['setup']} - {entry['delivery']} "
                        else:
                            joke = joke_data.get('joke') or f"{joke_data.get('setup')} - {joke_data.get('delivery')}"
                    else:
                        async with session.get(joke_url) as resp:
                            joke_data = await resp.json(content_type=None)

                        if joke_data['type'] == 'single':
                            joke = joke_data['joke']
                        else:
                            joke = f"{joke_data['setup']} - {joke_data['delivery']}"

                joke = joke.replace('\n', ' ').replace('\r', ' ')
                prefix = f"@{username}, here's your dad joke(s): "
                if len(prefix) + len(joke) > 490:
                    joke = joke[:490 - len(prefix) - 3] + "..."

                send_reply(prefix + joke)
                logging.info(f"Executed {self.name} command for {username}")

            except Exception as e:
                logging.error(f"Error fetching dad joke: {e}")
                send_reply("Sorry, I couldn't fetch a dad joke right now. Please try again later.")
        else:
            self.on_cooldown(send_reply, username)


class SocialsCommand(BaseCommand):
    def __init__(self):
        super().__init__(name="!socials", cooldown=10, description="provides a link to all my socials")

    async def execute(self, send_reply, username, message, channel, token, client_id, broadcaster_id):
        if self.can_execute(username):
            social_links = get_social_links()

            if not social_links:
                response = f"@{username}, no social links have been provided."
            else:
                link_display = " | ".join(
                    f"{name.capitalize()}: {url}" for name, url in social_links.items()
                )
                response = f"@{username}, here are all my socials: {link_display}"

            send_reply(response)
            logging.info(f"Executed {self.name} command for {username}")
        else:
            self.on_cooldown(send_reply, username)


from TTSObsWebsocket import broadcast_message, connected_clients

class VoteCommand(BaseCommand):
    active_vote = None
    vote_is_active = False
    vote_end_time = None
    vote_responses = {}

    def __init__(self):
        super().__init__(name="!vote", cooldown=5,
                         description="Allows you to start a vote if you're a mod")

    @staticmethod
    def _is_mod(username, channel):
        if channel not in ("YouTube", "TikTok"):
            return username.lower() in [v.username for v in viewers if v.mod]
        streamer = settings_data.get("Twitch_Name", "").strip().lower()
        if username.lower() == streamer:
            return True
        if channel == "YouTube":
            from Viewers import youtube_viewer_status
            return youtube_viewer_status.get(username.lower(), {}).get("moderator", False)
        return False

    async def execute(self, send_reply, username, message, channel, token, client_id, broadcaster_id):
        if not self.can_execute(username):
            self.on_cooldown(send_reply, username)
            return

        if self.__class__.vote_is_active:
            send_reply("⚠️ A vote is already active!")
            return

        logging.info(f"Executing {self.name} command for {username}")
        parts = message.split(" ", 1)

        # Mod check on all platforms.
        # Twitch: check the viewers mod list.
        # YouTube/TikTok: no mod API — treat the streamer's name (Twitch_Name) as the only mod.
        if not self._is_mod(username, channel):
            send_reply(f"@{username}, only moderators can start a vote!")
            return

        if len(parts) > 1 and "?" in parts[1]:
            question_and_options = parts[1]
            try:
                question, options_str = question_and_options.split("?", 1)
                options = re.findall(r'\d+\.(.*?)(?=\s*\d+\.|$)', options_str.strip())
                options = [opt.strip() for opt in options if opt.strip()]

                if len(options) < 2:
                    send_reply("You must provide at least 2 options.")
                    return

                logging.info(
                    f"Starting vote initiated by {username}: '{question.strip()}?' "
                    f"with options: {', '.join(f'{i + 1}. {opt}' for i, opt in enumerate(options))}"
                )

                if OBS_Browser_Source:
                    logging.info("Sending vote to browser source")
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
                        client.send(json.dumps(vote_payload)) for client in list(connected_clients)
                    ])
                    logging.info(f"Vote sent to browser source: {vote_payload}")
                    send_reply(f"@{username} started a vote: {question.strip()}?")
                    send_reply("Type the number of your choice to vote!")
                elif channel not in ("YouTube", "TikTok"):
                    # Twitch native poll fallback (YouTube/TikTok don't support this)
                    logging.info("OBS web browser source is offline, creating Twitch poll instead.")
                    success, result = await create_twitch_poll(token, client_id, broadcaster_id, question, options)
                    if success:
                        send_reply(f"📊 A Twitch poll has been started! Vote using the poll above!")
                    else:
                        send_reply(f"⚠️ Failed to create Twitch poll: {result}")
                        options_text = " | ".join([f"{i + 1}. {opt}" for i, opt in enumerate(options)])
                        send_reply(f"@{username} started a vote: {question.strip()}? Options: {options_text}")
                        send_reply("Type the number of your choice to vote!")
                else:
                    # YouTube/TikTok with no OBS: run an in-chat vote
                    self.__class__.active_vote = {
                        "question": question.strip() + "?",
                        "options": options,
                        "started_by": username
                    }
                    self.__class__.vote_end_time = time.time() + 60
                    self.__class__.vote_responses = {}
                    self.__class__.vote_is_active = True
                    options_text = " | ".join([f"{i + 1}. {opt}" for i, opt in enumerate(options)])
                    send_reply(f"@{username} started a vote: {question.strip()}? Options: {options_text}")
                    send_reply("Type the number of your choice to vote!")

            except Exception as e:
                logging.error(f"Error while processing vote command: {e}")
                send_reply("⚠️ Error starting vote.")
        else:
            send_reply(f"@{username}, please use the correct format: !vote Question? 1.OptionOne 2.OptionTwo [3.OptionThree ...]")

    @classmethod
    async def handle_vote_response(cls, username, message):
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
                    client.send(json.dumps(vote_payload)) for client in list(connected_clients)
                ])
                logging.info(f"Vote response sent to browser source: {vote_payload}")

    @classmethod
    async def handle_end_of_vote(cls, send_reply):
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

                result_message = f"🗳️ Final vote results for '{cls.active_vote['question']}': " + " | ".join(result_lines)
                send_reply(result_message)
                logging.info("Vote ended and results sent to chat.")

            cls.active_vote = None
            cls.vote_responses = {}
            cls.vote_end_time = None

async def create_twitch_poll(token, client_id, broadcaster_id, question, options, duration=60):
    headers = {
        "Authorization": f"Bearer {token}",
        "Client-ID": client_id,
        "Content-Type": "application/json"
    }

    payload = {
        "broadcaster_id": broadcaster_id,
        "title": question.strip()[:60],
        "choices": [{"title": opt[:25]} for opt in options[:5]],
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


class SanityCommand(BaseCommand):
    Current_Sanity = 100
    sanity_responses = {}

    def __init__(self):
        super().__init__(name="!sanity", cooldown=2, description="Vote on the streamer's current sanity level (1–100)")

    async def execute(self, send_reply, username, message, channel, *args):
        if not self.can_execute(username):
            self.on_cooldown(send_reply, username)
            return
        try:
            parts = message.strip().split()
            if len(parts) > 1:
                value = int(parts[1])
                if not (1 <= value <= 100):
                    send_reply(f"@{username}, please enter a number between 1 and 100.")
                    return

                self.__class__.sanity_responses[username] = value
                logging.info(f"Sanity vote by {username}: {value}")

                total = sum(self.sanity_responses.values())
                count = len(self.sanity_responses)
                if count == 0:
                    return

                avg_sanity = round(total / count)
                self.__class__.Current_Sanity = avg_sanity

                if Sanity_Bar:
                    sanity_payload = {
                        "type": "sanity",
                        "value": avg_sanity
                    }
                    await asyncio.gather(*[
                        client.send(json.dumps(sanity_payload)) for client in list(connected_clients)
                    ])
                    logging.info(f"Updated sanity sent to OBS: {sanity_payload}")

                send_reply(f"@{username} Your vote has been recorded. Current sanity: {avg_sanity}/100")

            else:
                avg_sanity = self.__class__.Current_Sanity
                send_reply(f"@{username} Current sanity is {avg_sanity}/100 with {len(self.sanity_responses)} vote(s).")

        except ValueError:
            send_reply(f"@{username}, please provide a number like `!sanity 85`.")


class ShoutOutCommand(BaseCommand):
    def __init__(self):
        super().__init__(
            name="!so",
            cooldown=60,
            description="Give a streamer you like or raided with a shout out."
        )

    async def execute(self, send_reply, username, message, channel, *args):
        if not self.can_execute(username):
            self.on_cooldown(send_reply, username)
            return

        parts = message.split()

        if len(parts) < 2:
            send_reply(f"@{username}, please provide a username")
            return

        shoutout_user = parts[1].lstrip("@").lower()

        response = (
            f"🎉 Shout out to @{shoutout_user}! "
            f"Go check them out at https://twitch.tv/{shoutout_user} 🔥"
        )

        logging.info(f"{username} is attempting to shoutout: {shoutout_user}")
        send_reply(response)


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
    "!vote": VoteCommand(),
    "!sanity": SanityCommand(),
    "!so": ShoutOutCommand()
}
