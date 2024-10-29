import json

from SoundEffect import load_sound_effects # Function to load settings

sound_effects = None
OBS_Browser_Source = False
sound_effects_cooldown = 0

def load_settings(settings_path):
    with open(settings_path, 'r') as file:
        settings = json.load(file)
    return settings


def process_settings(settings_path):
    global sound_effects, OBS_Browser_Source
    settings = load_settings(settings_path)

    if settings.get("enable_sound_effects", False):
        sound_effects = load_sound_effects(settings.get("sound_effects_file_path"))

    # Store the other settings
    OBS_Browser_Source = settings.get("OBS_Browser_Source", False)
    sound_effects_cooldown = settings.get("sound_effects_cooldown", 0)

    return settings