import logging
logger = logging.getLogger(__name__)
import threading
import time

from TikTokLive import TikTokLiveClient
from TikTokLive.client.errors import UserOfflineError, UserNotFoundError
from TikTokLive.events import CommentEvent, ConnectEvent, DisconnectEvent, GiftEvent

from core.BotTTS import text_to_speech
from core.Commands import COMMANDS, VoteCommand
from core.SoundEffect import play_sound_from_file
from core.config import settings_data, sound_effects
from core.Viewers import add_tiktok_viewer

shutdown_event = threading.Event()


async def handle_chat_message(username, message, send_reply):
    try:
        command_name = message.split(" ")[0].lower()
        command = COMMANDS.get(command_name)

        if command:
            if "TikTok" not in command.platforms:
                return
            await command.execute(send_reply, username, message, "TikTok", "", "", "")
            return

        if message.lower() == "get out":
            play_sound_from_file(sound_effects, "Tuco-GET-OUT-Sound-Effect.mp3", True)
            return

        if VoteCommand.vote_is_active and message.strip().isdigit():
            if time.time() < VoteCommand.vote_end_time:
                await VoteCommand.handle_vote_response(username, message)
            else:
                await VoteCommand.handle_end_of_vote(send_reply)
            return

        tts_message = f"{username} says {message}"
        await text_to_speech(tts_message, platform="TikTok")

    except Exception as e:
        logger.error(f"Error processing TikTok message: {e}")


def run_TikTok_Bot():
    username = settings_data.get("TikTok_Username", "").strip().lstrip("@")
    if not username:
        logger.error("Missing TikTok_Username in settings.json.")
        return

    client = TikTokLiveClient(unique_id=f"@{username}")

    @client.on(ConnectEvent)
    async def on_connect(event: ConnectEvent):
        logger.info(f"Connected to TikTok LIVE: @{username}")

    @client.on(DisconnectEvent)
    async def on_disconnect(event: DisconnectEvent):
        logger.info("Disconnected from TikTok LIVE.")

    @client.on(CommentEvent)
    async def on_comment(event: CommentEvent):
        author = event.user.nick_name
        text = event.comment
        logger.debug(f"[TikTok] {author}: {text}")
        add_tiktok_viewer(author)

        # TikTok has no unauthenticated send-message API, so replies go out as TTS
        tts_responses = []
        send_reply = lambda msg: tts_responses.append(msg)

        await handle_chat_message(author, text, send_reply)

        for resp in tts_responses:
            await text_to_speech(resp)

    @client.on(GiftEvent)
    async def on_gift(event: GiftEvent):
        # streaking=True means the combo is still going — wait until it ends
        if event.streaking:
            return
        author = event.user.nick_name
        gift_name = event.gift.name
        count = event.repeat_count or 1
        if count > 1:
            tts_msg = f"{author} sent {count} {gift_name}s, thank you so much!"
        else:
            tts_msg = f"{author} sent a {gift_name}, thank you so much!"
        await text_to_speech(tts_msg)

    try:
        logger.info(f"Connecting to TikTok LIVE for @{username}...")
        client.run()
    except UserOfflineError:
        logger.error(f"@{username} is not currently live. Start your TikTok LIVE first.")
    except UserNotFoundError:
        logger.error(f"TikTok user @{username} was not found. Check TikTok_Username in settings.json.")
    except Exception as e:
        logger.error(f"TikTok bot error: {e}")
    finally:
        logger.info("TikTok bot shutting down.")
