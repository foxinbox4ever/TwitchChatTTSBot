import subprocess
import sys
import pkg_resources


def ensure_requirements(requirements_file="requirements.txt"):
    with open(requirements_file) as f:
        reqs = [line.split("#")[0].strip() for line in f if line.split("#")[0].strip()]
    try:
        pkg_resources.require(reqs)
    except (pkg_resources.DistributionNotFound, pkg_resources.VersionConflict) as e:
        print(f"Installing missing requirements: {e}")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", requirements_file, "-q"])


ensure_requirements()

import logging
import threading
import asyncio

from core.TTSObsWebsocket import start_websocket_server
from platforms.TwitchBot import run_Twitch_Bot, shutdown_event
from platforms.YouTubeBot import run_YouTube_Bot
from platforms.TikTokBot import run_TikTok_Bot
from core.config import process_settings


def start_twitch_bot(loop):
    try:
        run_Twitch_Bot(loop)
    except Exception as e:
        logging.error(f"Twitch bot crashed: {e}")
        shutdown_event.set()


def start_youtube_bot(loop):
    try:
        run_YouTube_Bot(loop)
    except Exception as e:
        logging.error(f"YouTube bot crashed: {e}")
        shutdown_event.set()


def start_tiktok_bot():
    try:
        run_TikTok_Bot()
    except Exception as e:
        logging.error(f"TikTok bot crashed: {e}")


async def main():
    settings = process_settings("settings.json")
    logging.info(f"Settings: {settings}")

    loop = asyncio.get_running_loop()
    threads = []

    if settings.get("Twitch_Bot", False):
        t = threading.Thread(target=start_twitch_bot, args=(loop,), name="TwitchBot", daemon=True)
        t.start()
        threads.append(t)

    if settings.get("YouTube_Bot", False):
        y = threading.Thread(target=start_youtube_bot, args=(loop,), name="YouTubeBot", daemon=True)
        y.start()
        threads.append(y)

    if settings.get("TikTok_Bot", False):
        k = threading.Thread(target=start_tiktok_bot, name="TikTokBot", daemon=True)
        k.start()
        threads.append(k)

    websocket_task = None
    if settings.get("OBS_Browser_Source", False) or settings.get("Sanity_Bar", False):
        websocket_task = asyncio.create_task(start_websocket_server())

    try:
        while not shutdown_event.is_set():
            await asyncio.sleep(1)
    except (asyncio.CancelledError, KeyboardInterrupt):
        logging.info("Shutdown signal received...")
    finally:
        shutdown_event.set()
        if websocket_task:
            websocket_task.cancel()
        for t in threads:
            t.join(timeout=5)
        logging.info("All bots shut down.")


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Interrupted.")
    except Exception as e:
        logging.error(f"Fatal error: {e}")
