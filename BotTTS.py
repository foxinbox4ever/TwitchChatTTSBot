import logging
import random
import pyttsx3

from TTSObsWebsocket import update_latest_message
from config import load_settings
from Viewers import viewers  # Ensure this import exists

# Initialize TTS engine
tts_engine = pyttsx3.init()

# Get available voices and log them
voices = tts_engine.getProperty('voices')
logging.info("Available TTS voices:")
for i, voice in enumerate(voices):
    logging.info(f"  [{i}] Name: {voice.name}, ID: {voice.id}, Lang: {voice.languages}")


# Load settings
settings = load_settings("settings.json")
OBS_Browser_Source = settings.get("OBS_Browser_Source", False)
TTS_Access = settings.get("TTS_Access", "all").lower()
TTS_Volume = float(settings.get("TTS_Volume", 0.8))
TTS_Shout_Volume = float(settings.get("TTS_Shout_Volume", 1.0))
TTS_Random_Voice = settings.get("TTS_Random_Voice", False)
TTS_Voice = int(settings.get("TTS_Voice", 0))

# Get available voices
voices = tts_engine.getProperty('voices')


def set_tts_voice():
    try:
        if TTS_Random_Voice:
            voice = random.choice(voices)
        else:
            if 0 <= TTS_Voice < len(voices):
                voice = voices[TTS_Voice]
            else:
                voice = voices[0]  # fallback to first if index out of range
        tts_engine.setProperty('voice', voice.id)
    except Exception as e:
        logging.error(f"Error setting TTS voice: {e}")


def user_allowed_tts(username):
    viewer_info = next((v for v in viewers if v.username.lower() == username.lower()), None)

    if TTS_Access == "off":
        return False
    if TTS_Access == "subscribers" and not (viewer_info and viewer_info.is_subscribed):
        return False
    if TTS_Access == "followers" and not (viewer_info and viewer_info.is_following):
        return False
    return True


async def text_to_speech(message):
    try:
        logging.info("TTS activated for message")
        username_message = message.split("says")
        username = username_message[0].strip()

        if not user_allowed_tts(username):
            logging.info(f"TTS skipped for {username}: Not allowed by TTS_Access setting.")
            return 0

        estimated_duration = len(message.split()) * 500

        if OBS_Browser_Source:
            await update_latest_message(username_message[0], username_message[1], estimated_duration)

        if tts_engine._inLoop:
            tts_engine.endLoop()

        set_tts_voice()
        tts_engine.setProperty('volume', TTS_Volume)
        tts_engine.say(message)
        tts_engine.runAndWait()

        return estimated_duration
    except Exception as e:
        logging.error(f"Error in TTS: {e}")
        return 0


async def text_to_shout(message):
    try:
        logging.info("TTS shout activated for message")
        username_message = message.split("shouts")
        username = username_message[0].strip()

        if not user_allowed_tts(username):
            logging.info(f"TTS shout skipped for {username}: Not allowed by TTS_Access setting.")
            return 0

        estimated_duration = len(message.split()) * 500

        if OBS_Browser_Source:
            await update_latest_message(username_message[0], username_message[1], estimated_duration)

        if tts_engine._inLoop:
            tts_engine.endLoop()

        set_tts_voice()
        tts_engine.setProperty('volume', TTS_Shout_Volume)
        tts_engine.say(message)
        tts_engine.runAndWait()

        return estimated_duration
    except Exception as e:
        logging.error(f"Error in TTS shout: {e}")
        return 0