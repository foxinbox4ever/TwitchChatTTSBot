import os
import ssl
import logging
import threading
import irc.client
import asyncio

from TTS import text_to_speech
from TTSObsWebsocket import start_websocket_server
from Commands import COMMANDS
from SoundEffect import play_sound_from_file, set_sound_cooldown_from_file
from config import process_settings, sound_effects
from Viewers import Viewer, viewers, new_viewer_wrapper, remove_viewer, get_broadcaster_id

logging.basicConfig(level=logging.INFO)  # Set up logging configuration
shutdown_event = threading.Event()

def on_any_event(connection, event):
    logging.info(f"Event received: {event.type} - Arguments: {event.arguments}")

def on_connect(connection, event):
    logging.info(f"Connected to {connection.server}")
    connection.cap("REQ", ":twitch.tv/membership")
    connection.join(channel)

def on_join(connection, event):
    username = event.source.nick
    logging.info(f"{username} has joined {channel}")

    # Create a Viewer instance for the new user
    #if username != nickname.lower() or channel.split('#')[1]:
    threading.Thread(target=new_viewer_wrapper, args=(username, token, client_id, broadcaster_id)).start()

def on_part(connection, event):
    username = event.source.nick
    logging.info(f"{username} has left {channel}")

    remove_viewer(username)


def on_ping(connection, event):
    # Extract the message from the PING
    ping_message = event.arguments[0] if event.arguments else ""
    logging.info(f"Received PING: {ping_message}")

    # Send the PONG response
    connection.send_raw(f"PONG :{ping_message}")

def on_names(connection, event):
    # Check for NAMES response
    if event.type == "namreply":  # NAMES reply
        channel = event.arguments[1]
        usernames = event.arguments[2].split()
        logging.info(f"Argument for namreply: {event.arguments}")
        logging.info(f"usernames: {usernames}")
        for username in usernames:
            if username != nickname.lower():
                new_viewer_wrapper(username, token, client_id, broadcaster_id)

    elif event.type == "endofnames":  # End of NAMES reply
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
            await command.execute(connection, username, message, channel)
        elif "get out" == message:
            play_sound_from_file(sound_effects, "Tuco-GET-OUT-Sound-Effect.mp3", True)
        else:
            tts_message = f"{username} says {message}"
            await text_to_speech(tts_message)
    except Exception as e:
        logging.error(f"Error processing message from {username}: {e}")

def on_pubmsg(connection, event):
    username = event.source.nick
    message = event.arguments[0]
    user_found = False
    logging.info(f"{connection}: {username}: {message}")

    for viewer in viewers:
        if username == viewer.username:
            user_found = True
            break
    if not user_found:
        threading.Thread(target=new_viewer_wrapper, args=(username, token, client_id, broadcaster_id)).start()

    threading.Thread(target=handle_chat_message_wrapper, args=(connection, username, message.lower())).start()

class IRCBot:
    def __init__(self, server, port, nickname, token, client_id, client_secret):
        self.server = server
        self.port = port
        self.nickname = nickname
        self.client_id = client_id
        self.client_secret = client_secret
        self.token = token
        self.reactor = irc.client.Reactor()
        self.connection = None

    def connect(self):
        factory = irc.connection.Factory(wrapper=ssl.wrap_socket)
        try:
            logging.info("Connecting to chat...")
            self.connection = self.reactor.server().connect(
                self.server, self.port, self.nickname, f"oauth:{self.token}", connect_factory=factory
            )
            logging.info(f"Connected to {self.server} as {self.nickname}")
        except irc.client.ServerConnectionError as e:
            logging.error(f"Could not connect to server: {e}")
            return

    def setup_handlers(self):
        if self.connection:
            self.connection.add_global_handler('welcome', on_connect)
            self.connection.add_global_handler('join', on_join)
            self.connection.add_global_handler('part', on_part)
            self.connection.add_global_handler('pubmsg', on_pubmsg)
            self.connection.add_global_handler('namreply', on_names)
            self.connection.add_global_handler('endofnames', on_names)
            self.connection.add_global_handler('ping', on_ping)
            #self.connection.add_global_handler("all_events", on_any_event)

    def run(self):
        self.connect()
        self.setup_handlers()

        try:
            self.reactor.process_forever()
        except KeyboardInterrupt:
            logging.info("Shutting down...")
            logging.info(f"Running threads {threading.enumerate()}")
        finally:
            if self.connection:
                self.connection.close()
            logging.info("Bot disconnected.")

async def main():
    # Check if OBS_Browser_Source is True before starting the WebSocket server
    OBS_Browser_Source = settings.get("OBS_Browser_Source", False)
    if OBS_Browser_Source:
        # Start the WebSocket server in the asyncio event loop
        websocket_server_task = asyncio.create_task(start_websocket_server())
    else:
        websocket_server_task = None  # No WebSocket server needed

    bot = IRCBot(server, port, nickname, token, client_id, client_secret)
    # Run the IRC bot in a separate thread
    irc_thread = threading.Thread(target=bot.run, daemon=True)
    irc_thread.start()

    try:
        if websocket_server_task:
            # Await the WebSocket server task to keep it running
            await websocket_server_task
    except asyncio.CancelledError:
        logging.info("WebSocket server task cancelled.")
    finally:
        # Gracefully handle shutdown
        logging.info("Shutting down bot and WebSocket server...")
        shutdown_event.set()  # Signal shutdown
        if websocket_server_task:
            websocket_server_task.cancel()
        if bot.connection:
            bot.connection.close()

        # Wait for the IRC bot thread to finish
        irc_thread.join(timeout=5)

if __name__ == "__main__":
    server = 'irc.chat.twitch.tv'
    port = 6697
    nickname = 'foxinbox4ever'
    channel = '#foxinbox4ever'

    client_id = os.getenv('CLIENT_ID')  # Your Client ID
    client_secret = os.getenv('CLIENT_SECRET')  # Your Client Secret (use securely)
    token = os.getenv('TWITCH_TOKEN') # Your Generated Token
    if not token or not client_id or not client_secret:
        logging.error("TWITCH_TOKEN, CLIENT_ID, and or CLIENT_SECRET environment variable not set.")
        exit(1)

    logging.info(f"{channel.split('#')[1]}")
    broadcaster_id = get_broadcaster_id(token, client_id, channel.split('#')[1])

    settings = process_settings("settings.json")
    logging.info(f"Settings: {settings}")

    try:
        asyncio.run(main())
    except Exception as e:
        logging.info(f"Running threads {threading.enumerate()}")
        logging.warning(f"Error: {e}")
    finally:
        logging.info("Bot and WebSocket server closed.")
        exit(0)
