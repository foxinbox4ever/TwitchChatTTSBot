import os
import ssl
import logging
import threading
import irc.client
import json
import time
import asyncio
import aiohttp
import websockets

from core.BotTTS import text_to_speech, notification_tts
from core.Commands import COMMANDS, VoteCommand
from core.SoundEffect import play_sound_from_file
from core.config import settings_data, sound_effects, enable_sound_effects
from core.Viewers import viewers, enqueue_viewer, enqueue_status_update, remove_viewer, get_broadcaster_id
from core.authorisation_url import autherise, refresh_token_if_available

logging.basicConfig(level=logging.INFO)
shutdown_event = threading.Event()
_loop = None

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
        enqueue_viewer(username, actual_token, client_id, broadcaster_id)

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
                enqueue_viewer(username, actual_token, client_id, broadcaster_id)
    elif event.type == "endofnames":
        logging.info(f"End of NAMES list for {event.arguments[1]}.")

def handle_chat_message_wrapper(connection, username, message):
    future = asyncio.run_coroutine_threadsafe(
        handle_chat_message(connection, username, message), _loop
    )
    future.add_done_callback(
        lambda f: logging.error(f"Error handling message from {username}: {f.exception()}") if f.exception() else None
    )

async def handle_chat_message(connection, username, message):
    logging.info(f"Handling message from {username}: {message}")
    send_reply = lambda msg: connection.privmsg(channel, msg)
    try:
        command_name = message.split(" ")[0].lower()
        command = COMMANDS.get(command_name)

        if command:
            if "Twitch" not in command.platforms:
                return
            await command.execute(send_reply, username, message, channel, actual_token, client_id, broadcaster_id)
            return

        if message.lower() == "get out" and enable_sound_effects:
            play_sound_from_file(sound_effects, "Tuco-GET-OUT-Sound-Effect.mp3", True)
            return

        if VoteCommand.vote_is_active:
            if message.strip().isdigit():
                if time.time() < VoteCommand.vote_end_time:
                    await VoteCommand.handle_vote_response(username, message)
                else:
                    await VoteCommand.handle_end_of_vote(send_reply)
                return

        # TTS fallback
        if (username != "soundalerts"):
            tts_message = f"{username} says {message}"
            await text_to_speech(tts_message, platform="Twitch")

    except Exception as e:
        logging.error(f"Error handling chat message: {e}")

def on_pubmsg(connection, event):
    username = event.source.nick
    if (username == "soundalerts"):
        logging.info("Skipping SoundAlerts bot")
        return

    message = event.arguments[0]
    user_found = any(username == viewer.username for viewer in viewers)

    if not user_found:
        enqueue_viewer(username, actual_token, client_id, broadcaster_id)
    handle_chat_message_wrapper(connection, username, message)

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
        ssl_context = ssl.create_default_context()
        factory = irc.connection.Factory(wrapper=ssl_context.wrap_socket)
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

async def _subscribe_to_eventsub(session_id: str):
    headers = {
        "Authorization": f"Bearer {actual_token}",
        "Client-Id": client_id,
        "Content-Type": "application/json"
    }
    subscriptions = [
        {
            "type": "channel.follow",
            "version": "2",
            "condition": {"broadcaster_user_id": broadcaster_id, "moderator_user_id": broadcaster_id},
        },
        {
            "type": "channel.subscribe",
            "version": "1",
            "condition": {"broadcaster_user_id": broadcaster_id},
        },
        {
            "type": "channel.subscription.message",
            "version": "1",
            "condition": {"broadcaster_user_id": broadcaster_id},
        },
        {
            "type": "channel.subscription.gift",
            "version": "1",
            "condition": {"broadcaster_user_id": broadcaster_id},
        },
        {
            "type": "channel.raid",
            "version": "1",
            "condition": {"to_broadcaster_user_id": broadcaster_id},
        },
        {
            "type": "channel.cheer",
            "version": "1",
            "condition": {"broadcaster_user_id": broadcaster_id},
        },
    ]
    async with aiohttp.ClientSession() as session:
        for sub in subscriptions:
            body = {**sub, "transport": {"method": "websocket", "session_id": session_id}}
            try:
                async with session.post(
                    "https://api.twitch.tv/helix/eventsub/subscriptions",
                    headers=headers,
                    json=body
                ) as resp:
                    if resp.status == 202:
                        logging.info(f"EventSub: subscribed to {sub['type']}")
                    else:
                        text = await resp.text()
                        logging.error(f"EventSub subscription failed for {sub['type']}: {resp.status} - {text}")
            except Exception as e:
                logging.error(f"EventSub subscription error for {sub['type']}: {e}")


async def _eventsub_loop():
    EVENTSUB_URL = "wss://eventsub.wss.twitch.tv/ws"
    connect_url = EVENTSUB_URL

    while not shutdown_event.is_set():
        try:
            async with websockets.connect(connect_url) as ws:
                connect_url = EVENTSUB_URL
                async for raw in ws:
                    msg = json.loads(raw)
                    msg_type = msg.get("metadata", {}).get("message_type")

                    if msg_type == "session_welcome":
                        await _subscribe_to_eventsub(msg["payload"]["session"]["id"])

                    elif msg_type == "notification":
                        await _handle_eventsub_notification(msg)

                    elif msg_type == "session_reconnect":
                        connect_url = msg["payload"]["session"]["reconnect_url"]
                        logging.info("EventSub: reconnecting to new URL")
                        break

                    elif msg_type == "revocation":
                        logging.warning("EventSub: subscription revoked, reconnecting")
                        break

        except Exception as e:
            if not shutdown_event.is_set():
                logging.error(f"EventSub error: {e}")
                await asyncio.sleep(10)


async def _handle_eventsub_notification(msg: dict):
    sub_type = msg["metadata"]["subscription_type"]
    event = msg["payload"]["event"]
    logging.info(f"EventSub notification: {sub_type}")

    if sub_type == "channel.follow":
        username = event.get("user_name", "Someone")
        await notification_tts(f"{username} just followed!", "follow", username)

    elif sub_type == "channel.subscribe" and not event.get("is_gift"):
        username = event.get("user_login", "someone")
        viewer = next((v for v in viewers if v.username == username), None)
        if viewer:
            enqueue_status_update(viewer)
        else:
            enqueue_viewer(username, actual_token, client_id, broadcaster_id)
        await text_to_speech(f"{username} subbed, thank you very much for the sub!")

    elif sub_type == "channel.subscription.message":
        username = event.get("user_login", "someone")
        months = event.get("cumulative_months", 0)
        viewer = next((v for v in viewers if v.username == username), None)
        if viewer:
            enqueue_status_update(viewer)
        else:
            enqueue_viewer(username, actual_token, client_id, broadcaster_id)
        if months > 1:
            tts = f"{username} resubbed for {months} months, thank you very much for the sub!"
        else:
            tts = f"{username} resubbed, thank you very much for the sub!"
        msg_text = (event.get("message") or {}).get("text", "")
        if msg_text:
            tts += f" They said: {msg_text}"
        await text_to_speech(tts)

    elif sub_type == "channel.subscription.gift":
        is_anon = event.get("is_anonymous", False)
        gifter = event.get("user_login") if not is_anon else None
        total = event.get("total", 1)
        if gifter:
            viewer = next((v for v in viewers if v.username == gifter), None)
            if viewer:
                enqueue_status_update(viewer)
            else:
                enqueue_viewer(gifter, actual_token, client_id, broadcaster_id)
            name = gifter
        else:
            name = "Anonymous"
        if total > 1:
            tts = f"{name} gifted {total} subs! Thank you very much for the gifted subs!"
        else:
            tts = f"{name} gifted a sub, thank you very much for the gifted sub!"
        await text_to_speech(tts)

    elif sub_type == "channel.raid":
        username = event.get("from_broadcaster_user_login", "someone")
        viewer_count = event.get("viewers", "")
        count_str = f" with {viewer_count} viewers" if viewer_count else ""
        if bot and bot.connection:
            bot.connection.privmsg(channel, f"Thank you for the raid @{username}{count_str}! Go check them out at https://twitch.tv/{username}")
        await text_to_speech(f"{username} raided, thank you very much for the raid!")

    elif sub_type == "channel.cheer":
        username = event.get("user_login") if not event.get("is_anonymous") else "Anonymous"
        bits = event.get("bits", "some")
        tts = f"{username} cheered {bits} bits, thank you very much for the bits!"
        cheer_msg = event.get("message", "")
        if cheer_msg:
            tts += f" They said: {cheer_msg}"
        await notification_tts(tts, "cheer", username)


def _token_refresh_loop():
    # Refresh every 3 hours — Twitch tokens expire in ~4 hours
    while not shutdown_event.wait(timeout=3 * 60 * 60):
        logging.info("Proactively refreshing Twitch token...")
        new_token = refresh_token_if_available(client_id, client_secret)
        if new_token:
            global token, actual_token
            token = new_token
            actual_token = new_token.split("oauth:")[-1]
            for v in list(viewers):
                v.token = actual_token
            logging.info("Token refreshed and propagated to all viewers.")
        else:
            logging.warning("Proactive token refresh failed — will retry next cycle.")


def run_Twitch_Bot(loop):
    global server, port, client_id, client_secret
    global token, actual_token, nickname, channel, broadcaster_id, _loop
    _loop = loop

    server = 'irc.chat.twitch.tv'
    port = 6697

    client_id = settings_data.get("Twitch_Client_ID")
    client_secret = settings_data.get("Twitch_Client_Secret")
    token = settings_data.get("Twitch_Token")
    actual_token = token.split("oauth:")[-1] if token else ""
    nickname = settings_data.get("Twitch_Name")
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

    threading.Thread(target=_token_refresh_loop, daemon=True).start()
    asyncio.run_coroutine_threadsafe(_eventsub_loop(), _loop)

    # Run until externally shut down
    while not shutdown_event.is_set():
        time.sleep(1)

    logging.info("Twitch bot shutting down...")
    if bot and bot.connection:
        try:
            bot.connection.close()
        except Exception:
            pass