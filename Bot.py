import os
import ssl
import logging
import threading
import irc.client
import asyncio

from TTS import text_to_speech
from TTSObsWebsocket import start_websocket_server
from Commands import COMMANDS
from SoundEffect import play_sound_from_file,set_sound_cooldown_from_file
from Settings import process_settings, sound_effects

logging.basicConfig(level=logging.INFO) # Set up logging configuration

def on_connect(connection, event):
    logging.info(f"Connected to {connection.server}")
    connection.join(channel)


def on_join(connection, event):
    logging.info(f"Joined {channel}")


async def handle_chat_message(connection, username, message):
    logging.info(f"Handling message from {username}: {message}")
    try:
        command_name = message.split(" ")[0]
        command = COMMANDS.get(command_name)

        if command:
            await command.execute(connection, username, message, channel)  # Ensure command is awaited
            logging.info(f"Executed {command_name} command for {username}")
        elif "get out" == message:
            play_sound_from_file(sound_effects, "Tuco-GET-OUT-Sound-Effect.mp3", True)
        else:
            tts_message = f"{username} says {message}"
            await text_to_speech(tts_message)
            logging.info(f"Message from {username} processed successfully.")
    except Exception as e:
        logging.error(f"Error processing message from {username}: {e}")


def on_pubmsg(connection, event):
    username = event.source.nick
    message = event.arguments[0]
    logging.info(f"{connection}: {username}: {message}")

    threading.Thread(target=handle_chat_message_wrapper, args=(connection, username, message.lower())).start()


def handle_chat_message_wrapper(connection, username, message):
    try:
        asyncio.run(handle_chat_message(connection, username, message))
    except Exception as e:
        logging.error(f"Error handling message from {username}: {e}")


def run_irc_bot(server, port, nickname, token):
    reactor = irc.client.Reactor()
    factory = irc.connection.Factory(wrapper=ssl.wrap_socket)

    try:
        logging.info("Connecting to chat...")
        connection = reactor.server().connect(server, port, nickname, token, connect_factory=factory)
        logging.info(f"Connected to {server} as {nickname}")
    except irc.client.ServerConnectionError as e:
        logging.error(f"Could not connect to server: {e}")
        return

    connection.add_global_handler('welcome', on_connect)
    connection.add_global_handler('join', on_join)
    connection.add_global_handler('pubmsg', on_pubmsg)

    try:
        reactor.process_forever()
    except KeyboardInterrupt:
        logging.info("Shutting down...")
    finally:
        connection.disconnect("Bot disconnected.")
        logging.info("Bot disconnected.")


# ... (rest of your imports and setup)

async def main():
    # Check if OBS_Browser_Source is True before starting the WebSocket server
    OBS_Browser_Source = settings.get("OBS_Browser_Source", False)
    if OBS_Browser_Source:
        # Start the WebSocket server in the asyncio event loop
        websocket_server_task = asyncio.create_task(start_websocket_server())
    else:
        websocket_server_task = None  # No WebSocket server needed

    # Run the IRC bot in a separate thread
    irc_thread = threading.Thread(target=run_irc_bot, args=(server, port, nickname, token), daemon=True)
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
        if websocket_server_task:
            websocket_server_task.cancel()
        irc_thread.join()  # Ensure the IRC bot thread ends

if __name__ == "__main__":
    server = 'irc.chat.twitch.tv'
    port = 6697
    nickname = 'foxinbox4ever'
    token = os.getenv('TWITCH_TOKEN')
    channel = '#foxinbox4ever'

    settings = process_settings("settings.json")

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Keyboard interrupt received. Shutting down...")
    finally:
        logging.info("Bot and WebSocket server closed.")