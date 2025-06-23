import logging
import threading
import asyncio

from TTSObsWebsocket import start_websocket_server
from TwitchBot import run_Twitch_Bot
from YouTubeBot import run_YouTube_Bot
from config import process_settings

# Global shutdown event
shutdown_event = threading.Event()

def start_twitch_bot():
    try:
        run_Twitch_Bot()
    except Exception as e:
        logging.error(f"Twitch bot crashed: {e}")
        shutdown_event.set()

def start_youtube_bot():
    try:
        run_YouTube_Bot()
    except Exception as e:
        logging.error(f"YouTube bot crashed: {e}")
        shutdown_event.set()

async def main():
    settings = process_settings("settings.json")
    logging.info(f"Settings: {settings}")

    threads = []

    if settings.get("Twitch_Bot"):
        t = threading.Thread(target=start_twitch_bot, name="TwitchBot")
        t.start()
        threads.append(t)

    if settings.get("YouTube_Bot"):
        y = threading.Thread(target=start_youtube_bot, name="YouTubeBot")
        y.start()
        threads.append(y)

    websocket_task = None
    if settings.get("OBS_Browser_Source", False):
        websocket_task = asyncio.create_task(start_websocket_server())

    try:
        # Monitor threads and wait
        while not shutdown_event.is_set():
            await asyncio.sleep(1)
    except asyncio.CancelledError:
        logging.info("Shutting down asyncio tasks...")
    finally:
        if websocket_task:
            websocket_task.cancel()
        for t in threads:
            t.join(timeout=5)
        logging.info("All bots shut down.")

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    try:
        asyncio.run(main())
    except Exception as e:
        logging.error(f"Fatal error: {e}")

