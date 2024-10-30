import json
import logging


logging.basicConfig(level=logging.INFO)

sound_effects = None
sound_effects_cooldown = 0
OBS_Browser_Source = False
OBS_Bobble_image = "dwightHead.png"

def load_settings(settings_path):
    logging.info(f"Loading settings from {settings_path}")

    with open(settings_path, 'r') as file:
        settings = json.load(file)

    global sound_effects_cooldown, OBS_Browser_Source, OBS_Bobble_image

    enable_sound_effects = settings.get("enable_sound_effects", False)
    sound_effects_cooldown = settings.get("sound_effects_cooldown", 0)
    OBS_Browser_Source = settings.get("OBS_Browser_Source", False)
    OBS_Bobble_image = settings.get("OBS_Bobble_image", "dwightHead.png")

    return {
        "enable_sound_effects": enable_sound_effects,
        "sound_effects_cooldown": sound_effects_cooldown,
        "OBS_Browser_Source": OBS_Browser_Source,
        "OBS_Bobble_image": OBS_Bobble_image,
    }


def process_settings(settings_path):
    logging.info(f"Processing settings from {settings_path}")
    global sound_effects
    settings = load_settings(settings_path)

    if settings["enable_sound_effects"]:
        from SoundEffect import load_sound_effects  # Function to load settings
        sound_effects = load_sound_effects(settings.get("sound_effects_file_path"))

    return {
        "sound_effects": sound_effects,
        "sound_effects_cooldown": sound_effects_cooldown,
        "OBS_Browser_Source": OBS_Browser_Source,
        "OBS_Bobble_image": OBS_Bobble_image,
    }