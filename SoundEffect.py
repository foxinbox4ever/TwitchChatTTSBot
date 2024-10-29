from pydub import AudioSegment
from pydub.playback import play
import time
import logging

class Sound:
    def __init__(self, coolDown, filePath):
        self.coolDown = coolDown
        self.filePath = filePath
        self.lastTimePlayed = 0

    def getCoolDown(self):
        return self.coolDown

    def getLastTimePlayed(self):
        return self.lastTimePlayed

    def getFilePath(self):
        return self.filePath

    def setCoolDown(self, coolDown):
        self.coolDown = coolDown

    def setLastTimePlayed(self, lastTimePlayed):
        self.lastTimePlayed = lastTimePlayed

    def setFilePath(self, filePath):
        self.filePath = filePath

def _play_sound_with_cooldown(sound):
    try:
        currentTime = time.time()
        if currentTime - sound.getLastTimePlayed() >= sound.getCoolDown():
            sound.setLastTimePlayed(currentTime)
            soundEffect = AudioSegment.from_mp3(sound.getFilePath())
            play(soundEffect)
            logging.info(f"Played sound: {sound.getFilePath()}")
        else:
            logging.info(f"Sound is in cooldown: {sound.getFilePath()}")
    except FileNotFoundError:
        logging.error(f"File not found: {sound.getFilePath()}")
    except Exception as e:
        logging.error(f"Error playing sound: {e}")

def _play_sound(sound):
    try:
        soundEffect = AudioSegment.from_mp3(sound.getFilePath())
        play(soundEffect)
        logging.info(f"Played sound: {sound.getFilePath()}")

    except FileNotFoundError:
        logging.error(f"File not found: {sound.getFilePath()}")
    except Exception as e:
        logging.error(f"Error playing sound: {e}")