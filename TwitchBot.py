import os
import ssl
import logging
import threading
import irc.client
import json
import time
import asyncio

from BotTTS import text_to_speech
from Commands import COMMANDS, VoteCommand
from SoundEffect import play_sound_from_file
from config import process_settings, sound_effects
from Viewers import viewers, new_viewer_wrapper, remove_viewer, get_broadcaster_id
from Autherisation_URL import autherise

logging.basicConfig(level=logging.INFO)
shutdown_event = threading.Event()

# Global bot and thread references
bot = None
irc_thread = None

def on_any_event(connection, event):
    logging.info(f"Event received: {event.type} - Arguments: {event.arguments}")

def on_connect(connection, event):
    logging.info(f"Connected to {connection.server}")
    connection.cap("REQ", ":twitch.tv/membership")
    connection.cap("REQ", ":twitch.tv/commands")
    connection.cap("REQ", ":twitch.tv/tags")
    connection.join(channel)

def on_join(connection, event):
    username = event.source.nick
    logging.info(f"{username} has joined {channel}")
    if username.lower() != nickname.lower() and username != "own3d":
        threading.Thread(target=new_viewer_wrapper, args=(username, actual_token, client_id, broadcaster_id)).start()

def on_part(connection, event):
    username = event.source.nick
    logging.info(f"{username} has left {channel}")
    remove_viewer(username)

def on_ping(connection, event):
    ping_message = event.arguments[0] if event.arguments else ""
    logging.info(f"Received PING: {ping_message}")
    connection.send_raw(f"PONG :{ping_message}")

def on_names(connection, event):
    if event.type == "namreply":
        usernames = event.arguments[2].split()
        logging.info(f"usernames: {usernames}")
        for username in usernames:
            if username.lower() != nickname.lower() and username != "own3d":
                threading.Thread(target=new_viewer_wrapper, args=(username, actual_token, client_id, broadcaster_id)).start()
    elif event.type == "endofnames":
        logging.info(f"End of NAMES list for {event.arguments[1]}.")

def handle_chat_message_wrapper(connection, username, message):
    try:
        asyncio.run(handle_chat_message(connection, username, message))
    except Exception as e:
        logging.error(f"Error handling message from {username}: {e}")

async def handle_chat_message(connection, username, message):
    logging.info(f"Handling message from {username}: {message}")
    try:
        command_name = message.split(" ")[0]
        command = COMMANDS.get(command_name)

        if command:
            await command.execute(connection, username, message, channel, actual_token, client_id, broadcaster_id)
            return

        if message.lower() == "get out" and enable_sound_effects:
            play_sound_from_file(sound_effects, "Tuco-GET-OUT-Sound-Effect.mp3", True)
            return

        if VoteCommand.vote_is_active:
            if message.strip().isdigit():
                if time.time() < VoteCommand.vote_end_time:
                    await VoteCommand.handle_vote_response(connection, username, message, channel)
                else:
                    await VoteCommand.handle_end_of_vote(connection, channel)
                return

        # TTS fallback
        tts_message = f"{username} says {message}"
        await text_to_speech(tts_message)

    except Exception as e:
        logging.error(f"Error handling chat message: {e}")

def on_pubmsg(connection, event):
    username = event.source.nick
    if username == "SoundAlerts":
        return

    message = event.arguments[0]
    user_found = any(username == viewer.username for viewer in viewers)

    if not user_found:
        threading.Thread(target=new_viewer_wrapper, args=(username, actual_token, client_id, broadcaster_id)).start()
    threading.Thread(target=handle_chat_message_wrapper, args=(connection, username, message.lower())).start()

def on_privnotice(connection, event):
    message = event.arguments[0] if event.arguments else ""
    logging.warning(f"Privnotice received: {message}")
    if any(err in message.lower() for err in ["login unsuccessful", "authentication failed", "improperly formatted", "invalid nick"]):
        logging.warning("Invalid token or login issue detected. Attempting reauthorization...")
        global token
        token = autherise(client_id, client_secret)
        if token:
            logging.info("Reauthorization successful. Reconnecting...")
            save_token_to_settings(token)
            connection.close()
            reconnect_bot()
        else:
            logging.error("Reauthorization failed. Exiting.")
            shutdown_event.set()

def on_usernotice_wrapper(connection, event):
    try:
        asyncio.run(on_usernotice(connection, event))
    except Exception as e:
        logging.error(f"Error handling usernotice {event}: {e}")

async def on_usernotice(connection, event):
    tags = {tag["key"]: tag["value"] for tag in event.tags}
    username = tags.get("login")
    msg_id = tags.get("msg-id")
    tts_message = None  # Initialize early

    # Log all tags (optional for debugging)
    logging.debug(f"USERNOTICE tags: {tags}")

    # Handle anonymous gifts (no username/login field)
    if not username:
        logging.info(f"USERNOTICE received but no username found: {event}")

        if msg_id == "anongiftpaidupgrade":
            tts_message = "Anonymous gifted a sub, thank you very much for the gifted sub!"
            await text_to_speech(tts_message)

        return

    username = username.lower()
    logging.info(f"USERNOTICE from {username} (type: {msg_id})")

    # Determine if we need to update the viewer (subber or gifter)
    update_needed = msg_id in {"sub", "resub", "subgift", "giftpaidupgrade"}

    # Find existing viewer
    viewer = next((v for v in viewers if v.username == username), None)

    if update_needed:
        if not viewer:
            threading.Thread(
                target=new_viewer_wrapper,
                args=(username, actual_token, client_id, broadcaster_id)
            ).start()
        else:
            threading.Thread(target=viewer.update_status).start()

    # Handle recipient viewer if it's a subgift
    if msg_id == "subgift":
        recipient = tags.get("msg-param-recipient-user-name")
        if recipient:
            recipient = recipient.lower()
            recipient_viewer = next((v for v in viewers if v.username == recipient), None)
            if not recipient_viewer:
                threading.Thread(
                    target=new_viewer_wrapper,
                    args=(recipient, actual_token, client_id, broadcaster_id)
                ).start()
            else:
                threading.Thread(target=recipient_viewer.update_status).start()
            tts_message = f"{username} gifted a sub to {recipient}, thank you very much for the gifted sub!"
        else:
            tts_message = f"{username} gifted a sub, thank you very much for the gifted sub!"

    elif msg_id == "sub":
        tts_message = f"{username} subbed, thank you very much for the sub!"

    elif msg_id == "resub":
        months = tags.get("msg-param-cumulative-months")
        if months and months.isdigit() and months > 1:
            months_int = int(months)
            tts_message = f"{username} resubbed for {months_int} months, thank you very much for the sub!"
        else:
            tts_message = f"{username} resubbed, thank you very much for the sub!"

    elif msg_id == "submysterygift":
        gift_count = tags.get("msg-param-mass-gift-count", "some")
        tts_message = f"{username} gifted {gift_count} subs! Thank you very much for the gifted subs!"

    elif msg_id == "giftpaidupgrade":
        tts_message = f"{username} continued their gifted sub, thank you very much!"

    elif msg_id == "raid":
        tts_message = f"{username} raided, thank you very much for the raid!"

    elif msg_id == "bitsbadgetier":
        tts_message = f"{username} gave bits, thank you very much for the bits!"

    if tts_message:
        await text_to_speech(tts_message)

def save_token_to_settings(new_token):
    if not new_token.startswith("oauth:"):
        new_token = f"oauth:{new_token}"
    with open("settings.json", "r+") as f:
        data = json.load(f)
        data["Twitch_Token"] = new_token
        f.seek(0)
        json.dump(data, f, indent=4)
        f.truncate()
    global token
    token = new_token

def reconnect_bot():
    global bot, irc_thread
    if bot and bot.connection:
        try:
            bot.connection.close()
            logging.info("Previous connection closed.")
        except Exception as e:
            logging.warning(f"Error closing previous connection: {e}")
    bot = IRCBot(server, port, nickname, token, client_id, client_secret)
    irc_thread = threading.Thread(target=bot.run, daemon=True)
    irc_thread.start()
    logging.info("Reconnection thread started.")

class IRCBot:
    def __init__(self, server, port, nickname, token, client_id, client_secret):
        self.server = server
        self.port = port
        self.nickname = nickname
        self.token = token
        self.client_id = client_id
        self.client_secret = client_secret
        self.reactor = irc.client.Reactor()
        self.connection = None

    def connect(self):
        factory = irc.connection.Factory(wrapper=ssl.wrap_socket)
        try:
            logging.info("Connecting to chat...")
            token = self.token
            if not token.startswith("oauth:"):
                token = f"oauth:{token}"
            self.connection = self.reactor.server().connect(
                self.server,
                self.port,
                self.nickname,
                token,
                connect_factory=factory
            )
            logging.info(f"Connected to {self.server} as {self.nickname}")
        except irc.client.ServerConnectionError as e:
            logging.error(f"Could not connect to server: {e}")

    def setup_handlers(self):
        if self.connection:
            self.connection.add_global_handler('welcome', on_connect)
            self.connection.add_global_handler('join', on_join)
            self.connection.add_global_handler('part', on_part)
            self.connection.add_global_handler('pubmsg', on_pubmsg)
            self.connection.add_global_handler('namreply', on_names)
            self.connection.add_global_handler('endofnames', on_names)
            self.connection.add_global_handler('ping', on_ping)
            self.connection.add_global_handler('privnotice', on_privnotice)
            self.connection.add_global_handler('usernotice', on_usernotice)
            self.connection.add_global_handler('all_events', on_any_event)  # Debug

    def run(self):
        self.connect()
        self.setup_handlers()
        try:
            self.reactor.process_forever()
        except KeyboardInterrupt:
            logging.info("Shutting down...")
        finally:
            if self.connection:
                self.connection.close()
            logging.info("Bot disconnected.")

def run_Twitch_Bot():
    global server, port, settings, client_id, client_secret
    global token, actual_token, nickname, channel, broadcaster_id

    server = 'irc.chat.twitch.tv'
    port = 6697

    settings = process_settings("settings.json")
    logging.info(f"Settings: {settings}")

    client_id = settings.get("Twitch_Client_ID")
    client_secret = settings.get("Twitch_Client_Secret")
    token = settings.get("Twitch_Token")
    actual_token = token.split("oauth:")[-1] if token else ""
    nickname = settings.get("Twitch_Name")
    channel = f"#{nickname.lower()}" if nickname else ""

    if not token or not client_id or not client_secret or not nickname:
        logging.warning("Missing Twitch credentials. Attempting to authorize...")
        token = autherise(client_id, client_secret)
        if not token:
            logging.error("Could not retrieve Twitch token.")
            return
        save_token_to_settings(token)
        actual_token = token.split("oauth:")[-1]

    logging.info(f"Bot will join channel: {channel}")

    broadcaster_id = get_broadcaster_id(actual_token, client_id, nickname)
    if broadcaster_id is None:
        logging.warning("Failed to retrieve broadcaster ID. Reauthorizing...")
        token = autherise(client_id, client_secret)
        if token:
            save_token_to_settings(token)
            actual_token = token.split("oauth:")[-1]
            broadcaster_id = get_broadcaster_id(actual_token, client_id, nickname)

    if broadcaster_id is None:
        logging.error("Could not find broadcaster ID after reauthorization.")
        return

    reconnect_bot()

    # Run until externally shut down
    while not shutdown_event.is_set():
        time.sleep(1)

    logging.info("Twitch bot shutting down...")