import logging
import threading
import time
import json
import asyncio

from googleapiclient.discovery import build
from BotTTS import text_to_speech
from Commands import COMMANDS, VoteCommand
from SoundEffect import play_sound_from_file
from config import process_settings, sound_effects
from Viewers import viewers, new_viewer_wrapper, remove_viewer
from Autherisation_URL import authenticate_youtube

shutdown_event = threading.Event()
live_chat_id = None
youtube = None

def get_live_chat_id(youtube, channel_id):
    logging.info("Getting live broadcast chat ID...")
    response = youtube.liveBroadcasts().list(
        part='snippet',
        broadcastStatus='active',
        broadcastType='all',
        mine=True
    ).execute()

    items = response.get("items", [])
    if not items:
        logging.warning("No active broadcasts found.")
        return None
    return items[0]['snippet']['liveChatId']

def poll_chat_messages():
    global youtube, live_chat_id

    next_page_token = None
    while not shutdown_event.is_set():
        try:
            response = youtube.liveChatMessages().list(
                liveChatId=live_chat_id,
                part='snippet,authorDetails',
                pageToken=next_page_token
            ).execute()

            for message in response.get("items", []):
                author = message["authorDetails"]["displayName"]
                text = message["snippet"]["displayMessage"]
                logging.info(f"[YouTube Chat] {author}: {text}")
                threading.Thread(target=handle_chat_message_wrapper, args=(author, text)).start()

            next_page_token = response.get("nextPageToken")
            polling_interval = float(response.get("pollingIntervalMillis", 2000)) / 1000.0
            time.sleep(polling_interval)

        except Exception as e:
            logging.error(f"Error polling chat: {e}")
            time.sleep(5)

def handle_chat_message_wrapper(username, message):
    try:
        asyncio.run(handle_chat_message(username, message))
    except Exception as e:
        logging.error(f"Error in message handler: {e}")

async def handle_chat_message(username, message):
    try:
        command_name = message.split(" ")[0]
        command = COMMANDS.get(command_name)

        if command:
            await command.execute(None, username, message, "YouTube", "", "", "")
            return

        if message.lower() == "get out":
            play_sound_from_file(sound_effects, "Tuco-GET-OUT-Sound-Effect.mp3", True)
            return

        if VoteCommand.vote_is_active:
            if message.strip().isdigit():
                if time.time() < VoteCommand.vote_end_time:
                    await VoteCommand.handle_vote_response(None, username, message, "YouTube")
                else:
                    await VoteCommand.handle_end_of_vote(None, "YouTube")
                return

        tts_message = f"{username} says {message}"
        await text_to_speech(tts_message)

    except Exception as e:
        logging.error(f"Error processing message: {e}")

def run_YouTube_Bot():
    global youtube, live_chat_id

    settings = process_settings("settings.json")
    api_key = settings.get("YouTube_API_Key")
    channel_id = settings.get("YouTube_Channel_ID")
    client_id = settings.get("YouTube_Client_ID")
    client_secret = settings.get("YouTube_Client_Secret")

    if not api_key or not channel_id or not client_id or not client_secret:
        logging.error("Missing YouTube credentials in settings.json.")
        return

    # Authenticate and get a valid access token
    from Autherisation_URL import authenticate_youtube  # import here to avoid circular import if needed
    access_token = authenticate_youtube(client_id, client_secret)

    if not access_token:
        logging.error("YouTube authentication failed. Bot will not run.")
        return

    # Build the YouTube API client using developerKey (for public APIs)
    youtube = build('youtube', 'v3', developerKey=api_key)

    live_chat_id = get_live_chat_id(youtube, channel_id)
    if not live_chat_id:
        logging.error("Could not retrieve Live Chat ID. Ensure you're live.")
        return

    logging.info("YouTube bot is now connected to live chat.")
    poll_chat_messages()

    logging.info("YouTube bot shutting down.")