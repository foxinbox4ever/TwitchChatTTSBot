import json
import logging

logging.basicConfig(level=logging.INFO)

# Global variables
Twitch_Bot = True
YouTube_Bot = False
sound_effects = None
sound_effects_cooldown = 0
OBS_Browser_Source = False
OBS_Bobble_image = "dwightHead.png"
TTS_Access = "all"
TTS_Volume = 0.8
TTS_Shout_Volume = 1.0
TTS_Random_Voice = False
TTS_Voice = 0
Sanity_Bar = False

# Global settings dictionary
settings_data = {}


def load_settings(settings_path):
    logging.info(f"Loading settings from {settings_path}")

    global settings_data
    global Twitch_Bot, YouTube_Bot
    global sound_effects_cooldown, OBS_Browser_Source, OBS_Bobble_image
    global TTS_Access, TTS_Volume, TTS_Shout_Volume, TTS_Random_Voice, TTS_Voice
    global Sanity_Bar

    with open(settings_path, 'r') as file:
        settings_data = json.load(file)

    # Load individual settings from settings_data
    Twitch_Bot = settings_data.get("Twitch_Bot", True)
    YouTube_Bot = settings_data.get("YouTube_Bot", settings_data.get("Youtube_Bot", False))
    sound_effects_cooldown = settings_data.get("sound_effects_cooldown", 0)
    OBS_Browser_Source = settings_data.get("OBS_Browser_Source", False)
    OBS_Bobble_image = settings_data.get("OBS_Bobble_image", "dwightHead.png")
    TTS_Access = settings_data.get("TTS_Access", "all").lower()
    Sanity_Bar = settings_data.get("Sanity_Bar", False)

    try:
        TTS_Volume = float(settings_data.get("TTS_Volume", 0.8))
    except (ValueError, TypeError):
        TTS_Volume = 0.8

    try:
        TTS_Shout_Volume = float(settings_data.get("TTS_Shout_Volume", 1.0))
    except (ValueError, TypeError):
        TTS_Shout_Volume = 1.0

    TTS_Random_Voice = settings_data.get("TTS_Random_Voice", False)

    try:
        TTS_Voice = int(settings_data.get("TTS_Voice", 0))
    except (ValueError, TypeError):
        TTS_Voice = 0

    return settings_data


def process_settings(settings_path):
    logging.info(f"Processing settings from {settings_path}")
    global sound_effects

    settings = load_settings(settings_path)

    if settings.get("enable_sound_effects", False):
        from SoundEffect import load_sound_effects
        sound_effects = load_sound_effects(settings.get("sound_effects_file_path"))

    return {
        "sound_effects": sound_effects,
        "sound_effects_cooldown": sound_effects_cooldown,
        "OBS_Browser_Source": OBS_Browser_Source,
        "OBS_Bobble_image": OBS_Bobble_image,
        "Twitch_Bot": Twitch_Bot,
        "YouTube_Bot": YouTube_Bot,
        "Twitch_Client_ID": settings.get("Twitch_Client_ID", ""),
        "Twitch_Client_Secret": settings.get("Twitch_Client_Secret", ""),
        "Twitch_Token": settings.get("Twitch_Token", ""),
        "Twitch_Name": settings.get("Twitch_Name", ""),
        "Twitch_Refresh_Token": settings.get("Twitch_Refresh_Token", ""),
        "TTS_Access": TTS_Access,
        "TTS_Volume": TTS_Volume,
        "TTS_Shout_Volume": TTS_Shout_Volume,
        "TTS_Random_Voice": TTS_Random_Voice,
        "TTS_Voice": TTS_Voice,
        "Sanity_Bar": Sanity_Bar
    }


def get_social_links():
    return {
        key.replace("_Link", ""): value
        for key, value in settings_data.items()
        if key.endswith("_Link") and value
    }
