from pydub import AudioSegment
from pydub.playback import play
import time
import logging
import os
from Settings import sound_effects_cooldown

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s') # Set up logging

class Sound:
    def __init__(self, filePath, coolDown=sound_effects_cooldown):
        self.coolDown = coolDown
        self.filePath = filePath
        self.lastTimePlayed = 0

    @property
    def coolDown(self):
        return self._coolDown

    @coolDown.setter
    def coolDown(self, value):
        self._coolDown = value

    @property
    def lastTimePlayed(self):
        return self._lastTimePlayed

    @lastTimePlayed.setter
    def lastTimePlayed(self, value):
        self._lastTimePlayed = value

    @property
    def filePath(self):
        return self._filePath

    @filePath.setter
    def filePath(self, value):
        self._filePath = value

    def _load_sound(self):
        """Load sound from file."""
        try:
            return AudioSegment.from_mp3(self.filePath)
        except FileNotFoundError:
            logging.error(f"File not found: {self.filePath}")
            return None

    def play_with_cooldown(self):
        """Play sound with cooldown logic."""
        currentTime = time.time()
        if currentTime - self.lastTimePlayed >= self.coolDown:
            self.lastTimePlayed = currentTime
            soundEffect = self._load_sound()
            if soundEffect:
                play(soundEffect)
                logging.info(f"Played sound: {self.filePath}")
        else:
            logging.info(f"Sound is in cooldown: {self.filePath}")

    def play(self):
        """Play sound without cooldown."""
        soundEffect = self._load_sound()
        if soundEffect:
            play(soundEffect)
            logging.info(f"Played sound: {self.filePath}")

# Function to create Sound instances for each .mp3 file
def load_sound_effects(sound_folder):
    logging.info(f"Loading sound effects from {sound_folder}")
    sound_objects = []
    for filename in os.listdir(sound_folder):
        if filename.endswith(".mp3"):
            filePath = os.path.join(sound_folder, filename)
            sound_objects.append(Sound(filePath))
            logging.info(f"Loaded sound effect: {filename}")

    return sound_objects

def get_sound_from_file(sound_objects, file_name):
    return next((sound for sound in sound_objects if sound.filePath.endswith(file_name)), None)

# Function to play a specific sound by filename if it exists
def play_sound_from_file(sound_objects, file_name, cool_down):
    sound_to_play = get_sound_from_file(sound_objects, file_name)

    if sound_to_play:
        if cool_down:
            sound_to_play.play_with_cooldown()
        else:
            sound_to_play.play()
    else:
        logging.info(f"Sound '{file_name}' not found in sound effects folder.")

def set_sound_cooldown_from_file(sound_objects, file_name, cool_down):
    sound = get_sound_from_file(sound_objects, file_name)

    if sound:
        sound.coolDown = cool_down
    else:
        logging.info(f"Sound '{file_name}' not found in sound effects folder.")