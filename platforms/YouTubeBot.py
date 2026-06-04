import logging
import threading
import time
import json
import asyncio

from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from core.BotTTS import text_to_speech
from core.Commands import COMMANDS, VoteCommand
from core.SoundEffect import play_sound_from_file
from core.config import settings_data, sound_effects
from core.Viewers import add_youtube_viewer
from core.authorisation_url import authenticate_youtube

shutdown_event = threading.Event()
live_chat_id = None
youtube = None
bot_channel_id = None  # The bot's own YouTube channel ID (to skip self-messages)


def get_live_chat_id(yt_client, channel_id):
    logging.info("Getting live broadcast chat ID...")
    response = yt_client.liveBroadcasts().list(
        part='snippet',
        broadcastStatus='active',
        broadcastType='all'
    ).execute()

    items = response.get("items", [])
    if not items:
        logging.warning("No active broadcasts found.")
        return None
    return items[0]['snippet']['liveChatId']


def get_bot_channel_id(yt_client):
    try:
        response = yt_client.channels().list(part='id', mine=True).execute()
        items = response.get("items", [])
        if items:
            return items[0]['id']
    except Exception as e:
        logging.warning(f"Could not retrieve bot channel ID: {e}")
    return None


def send_youtube_message(message):
    global youtube, live_chat_id
    try:
        youtube.liveChatMessages().insert(
            part="snippet",
            body={
                "snippet": {
                    "liveChatId": live_chat_id,
                    "type": "textMessageEvent",
                    "textMessageDetails": {
                        "messageText": message[:200]
                    }
                }
            }
        ).execute()
    except Exception as e:
        logging.error(f"Failed to send YouTube message: {e}")


def poll_chat_messages():
    global youtube, live_chat_id, bot_channel_id

    # Skip historical messages — grab the current page token without processing
    try:
        response = youtube.liveChatMessages().list(
            liveChatId=live_chat_id,
            part='id'
        ).execute()
        next_page_token = response.get("nextPageToken")
    except Exception as e:
        logging.error(f"Failed to get initial page token: {e}")
        next_page_token = None

    while not shutdown_event.is_set():
        try:
            response = youtube.liveChatMessages().list(
                liveChatId=live_chat_id,
                part='snippet,authorDetails',
                pageToken=next_page_token
            ).execute()

            for message in response.get("items", []):
                author_details = message["authorDetails"]
                author_channel_id = author_details.get("channelId", "")

                # Skip messages sent by the bot itself
                if bot_channel_id and author_channel_id == bot_channel_id:
                    continue

                author = author_details["displayName"]
                text = message["snippet"]["displayMessage"]
                is_member = author_details.get("isChatSponsor", False)
                is_moderator = author_details.get("isChatModerator", False)
                logging.info(f"[YouTube Chat] {author}: {text}")
                add_youtube_viewer(author, is_member=is_member, is_moderator=is_moderator)
                threading.Thread(
                    target=handle_chat_message_wrapper,
                    args=(author, text),
                    daemon=True
                ).start()

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
    send_reply = lambda msg: send_youtube_message(msg)
    try:
        command_name = message.split(" ")[0].lower()
        command = COMMANDS.get(command_name)

        if command:
            if "YouTube" not in command.platforms:
                return
            await command.execute(send_reply, username, message, "YouTube", "", "", "")
            return

        if message.lower() == "get out":
            play_sound_from_file(sound_effects, "Tuco-GET-OUT-Sound-Effect.mp3", True)
            return

        if VoteCommand.vote_is_active:
            if message.strip().isdigit():
                if time.time() < VoteCommand.vote_end_time:
                    await VoteCommand.handle_vote_response(username, message)
                else:
                    await VoteCommand.handle_end_of_vote(send_reply)
                return

        tts_message = f"{username} says {message}"
        await text_to_speech(tts_message, platform="YouTube")

    except Exception as e:
        logging.error(f"Error processing message: {e}")


def run_YouTube_Bot():
    global youtube, live_chat_id, bot_channel_id

    channel_id = settings_data.get("YouTube_Channel_ID")
    client_id = settings_data.get("YouTube_Client_ID")
    client_secret = settings_data.get("YouTube_Client_Secret")

    if not channel_id or not client_id or not client_secret:
        logging.error("Missing YouTube credentials in settings.json (YouTube_Channel_ID, YouTube_Client_ID, YouTube_Client_Secret).")
        return

    if channel_id == "Channel ID" or client_id == "" or client_secret == "":
        logging.error("YouTube credentials appear to be placeholders. Please fill in settings.json.")
        return

    access_token = authenticate_youtube(client_id, client_secret)
    if not access_token:
        logging.error("YouTube authentication failed. Bot will not run.")
        return

    refresh_token = settings_data.get("YouTube_Refresh_Token", "")
    credentials = Credentials(
        token=access_token,
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=client_id,
        client_secret=client_secret,
    )
    youtube = build('youtube', 'v3', credentials=credentials)

    bot_channel_id = get_bot_channel_id(youtube)
    if bot_channel_id:
        logging.info(f"Bot channel ID: {bot_channel_id} (self-messages will be filtered)")

    live_chat_id = get_live_chat_id(youtube, channel_id)
    if not live_chat_id:
        logging.error("Could not retrieve Live Chat ID. Ensure you're live.")
        return

    logging.info("YouTube bot is now connected to live chat.")
    poll_chat_messages()
    logging.info("YouTube bot shutting down.")