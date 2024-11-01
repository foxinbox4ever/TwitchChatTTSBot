import logging
import pyttsx3

from TTSObsWebsocket import update_latest_message
from config import load_settings

tts_engine = pyttsx3.init()
OBS_Browser_Source = load_settings("settings.json")["OBS_Browser_Source"]

async def text_to_speech(message):
    try:
        logging.info("TTS activated for message")
        username_message = message.split("says")

        # Estimate duration (you might need to adjust the factor for better accuracy)
        estimated_duration = len(message.split()) * 500

        # Check if OBS_Browser_Source is True before updating the last message
        logging.info(f"Is OBS Websocket is up: {OBS_Browser_Source}")
        if OBS_Browser_Source:
            await update_latest_message(username_message[0], username_message[1], estimated_duration)

        if tts_engine._inLoop:
            tts_engine.endLoop()

        tts_engine.setProperty('volume', 0.8)

        tts_engine.say(message)
        tts_engine.runAndWait()  # Ensure this completes

        return estimated_duration  # Return estimated duration
    except Exception as e:
        logging.error(f"Error in TTS: {e}")
        return 0  # Return 0 if there's an error


async def text_to_shout(message):
    try:
        logging.info("TTS activated for message")
        username_message = message.split("shouts")

        # Estimate duration (you might need to adjust the factor for better accuracy)
        estimated_duration = len(message.split()) * 500

        # Check if OBS_Browser_Source is True before updating the last message
        logging.info(f"Is OBS Websocket is up: {OBS_Browser_Source}")
        if OBS_Browser_Source:
            await update_latest_message(username_message[0], username_message[1], estimated_duration)

        if tts_engine._inLoop:
            tts_engine.endLoop()

        tts_engine.setProperty('volume', 1.0)

        tts_engine.say(message)
        tts_engine.runAndWait()  # Ensure this completes

        return estimated_duration  # Return estimated duration
    except Exception as e:
        logging.error(f"Error in TTS: {e}")
        return 0  # Return 0 if there's an error