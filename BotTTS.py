import logging
import random
import re
import base64
import io

import edge_tts

from TTSObsWebsocket import update_latest_message
from config import load_settings
from Viewers import viewers

settings = load_settings("settings.json")
OBS_Browser_Source = settings.get("OBS_Browser_Source", False)
TTS_Access = settings.get("TTS_Access", "all").lower()
TTS_Access_Twitch = settings.get("TTS_Access_Twitch", TTS_Access).lower()
TTS_Access_YouTube = settings.get("TTS_Access_YouTube", TTS_Access).lower()
TTS_Access_TikTok = settings.get("TTS_Access_TikTok", TTS_Access).lower()
TTS_Shout_Volume = float(settings.get("TTS_Shout_Volume", 1.0))
TTS_Random_Voice = settings.get("TTS_Random_Voice", False)

_voice_setting = settings.get("TTS_Voice", "en-GB-SoniaNeural")
TTS_Voice = _voice_setting if isinstance(_voice_setting, str) else "en-GB-SoniaNeural"

AVAILABLE_VOICES = [
    # US
    "en-US-AriaNeural", "en-US-AnaNeural", "en-US-JennyNeural", "en-US-MichelleNeural",
    "en-US-MonicaNeural", "en-US-EmmaNeural", "en-US-GuyNeural",
    "en-US-ChristopherNeural", "en-US-EricNeural", "en-US-RogerNeural",
    "en-US-SteffanNeural", "en-US-AndrewNeural", "en-US-BrianNeural",
    # GB
    "en-GB-SoniaNeural", "en-GB-LibbyNeural", "en-GB-MaisieNeural",
    "en-GB-RyanNeural", "en-GB-ThomasNeural",
    "en-GB-AbbiNeural", "en-GB-AlfieNeural", "en-GB-BellaNeural",
    "en-GB-ElliotNeural", "en-GB-EthanNeural", "en-GB-NoahNeural",
    "en-GB-OliverNeural", "en-GB-OliviaNeural",
    # AU
    "en-AU-NatashaNeural", "en-AU-WilliamNeural", "en-AU-AnnetteNeural",
    "en-AU-CarlyNeural", "en-AU-DarrenNeural", "en-AU-DuncanNeural",
    "en-AU-ElsieNeural", "en-AU-FreyaNeural", "en-AU-JoanneNeural",
    "en-AU-KenNeural", "en-AU-KimNeural", "en-AU-NeilNeural",
    "en-AU-TimNeural", "en-AU-TinaNeural",
    # CA
    "en-CA-ClaraNeural", "en-CA-LiamNeural",
    # IE
    "en-IE-EmilyNeural", "en-IE-ConnorNeural",
    # NZ
    "en-NZ-MitchellNeural", "en-NZ-MollyNeural",
    # ZA
    "en-ZA-LeahNeural", "en-ZA-LukeNeural",
    # SG
    "en-SG-LunaNeural", "en-SG-WayneNeural",
    # IN
    "en-IN-NeerjaNeural", "en-IN-PrabhatNeural",
    # PH
    "en-PH-JamesNeural", "en-PH-RosaNeural",
    # HK
    "en-HK-SamNeural", "en-HK-YanNeural",
    # KE
    "en-KE-AsiliaNeural", "en-KE-ChilembaNeural",
    # NG
    "en-NG-AbeoNeural", "en-NG-EzinneNeural",
    # TZ
    "en-TZ-ElimuNeural", "en-TZ-ImaniNeural",
]

_user_voices: dict[str, str] = {}

SPAM_LINK_KEYWORDS = [
    ".com", "dot com", ".net", "dot net", ".xyz", "dot xyz",
    "http", "www", "discord.gg", "free viewers",
]

# Patterns that TTS would phonetically render as slurs.
# Covers direct forms, leet/symbol substitutions, spaced-out letters,
# and near-homophones (e.g. "nicker", "nigg her") that bypass spelling filters
# but sound identical when spoken aloud.
_TTS_SLUR_PATTERNS = [re.compile(p, re.IGNORECASE) for p in [
    # n-word: direct, leet substitutions (i→1/!, g→9, a/e→3/4)
    r"n[i1!|][g9q][g9q][e3a4]r",
    # spaced / punctuated letters:  n . i . g . g . e . r  etc.
    r"n[\s\W_]*i[\s\W_]*g[\s\W_]*g[\s\W_]*[ae][\s\W_]*r",
    # phonetic near-homophones: "nicker", "nick er"
    r"\bnick\s*er",
    # split form: "nigg her", "nigg-her"
    r"\bnigg[\s\-_]*h?er\b",
    # f-slur and near-homophones
    r"\bf[a4][g9][g9][io0]t",
    r"\bf[\s\W_]*[a4][\s\W_]*g[\s\W_]*g[\s\W_]*[io0][\s\W_]*t",
]]


def _platform_access(platform):
    if platform == "YouTube":
        return TTS_Access_YouTube
    if platform == "TikTok":
        return TTS_Access_TikTok
    return TTS_Access_Twitch


def user_allowed_tts(username, platform="Twitch"):
    access = _platform_access(platform)

    if access == "off":
        return False
    if access == "all":
        return True

    if platform == "Twitch":
        viewer_info = next((v for v in viewers if v.username.lower() == username.lower()), None)
        if viewer_info is None:
            return True
        if access == "subs" and not viewer_info.subscribed:
            return False
        if access == "followers" and not viewer_info.following:
            return False

    elif platform == "YouTube":
        # "members" = YouTube channel members (isChatSponsor from the API)
        if access == "members":
            from Viewers import youtube_viewer_status
            return youtube_viewer_status.get(username.lower(), {}).get("member", False)

    # TikTok only supports "all" or "off" — anything else falls through to allowed
    return True


def _get_voice_for_user(username: str) -> str:
    key = username.lower()
    if key in _user_voices:
        return _user_voices[key]

    candidate_voices = [v for v in AVAILABLE_VOICES if v != TTS_Voice]
    taken = set(_user_voices.values())
    available = [v for v in candidate_voices if v not in taken]
    pool = available if available else candidate_voices

    _user_voices[key] = random.choice(pool)
    logging.info(f"Assigned voice {_user_voices[key]} to {username}")
    return _user_voices[key]


async def _generate_audio(text, username: str = "TTSystem"):
    if TTS_Random_Voice and username != "TTSystem":
        assigned = _get_voice_for_user(username)
        voices_to_try = [assigned] + [v for v in random.sample(AVAILABLE_VOICES, 2) if v != assigned]
    else:
        voices_to_try = [TTS_Voice]

    last_error = None
    for voice in voices_to_try:
        try:
            logging.info(f"Attempting TTS with voice: {voice}")
            communicate = edge_tts.Communicate(text, voice)
            buf = io.BytesIO()
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    buf.write(chunk["data"])
            audio = buf.getvalue()
            if not audio:
                raise RuntimeError("Empty audio response")
            logging.info(f"TTS audio generated with voice: {voice} ({len(audio)} bytes)")
            if TTS_Random_Voice and voice != voices_to_try[0]:
                _user_voices[username.lower()] = voice
                logging.info(f"Updated voice for {username} to {voice} (original voice failed)")
            return audio
        except Exception as e:
            logging.warning(f"Voice {voice} failed: {e}. Trying next voice...")
            last_error = e

    raise RuntimeError(f"All voices failed. Last error: {last_error}")


async def text_to_speech(message, platform="Twitch"):
    try:
        logging.info("TTS activated for message")

        username = "TTSystem"
        apply_spam_filter = True

        if " says " in message:
            username_message = message.split(" says ", 1)
            username = username_message[0].strip()

            if not user_allowed_tts(username, platform):
                logging.info(f"TTS skipped for {username}: Not allowed by TTS_Access_{platform} setting.")
                return 0
        else:
            apply_spam_filter = False
            username_message = [username, message]

        if apply_spam_filter:
            if any(keyword in message.lower() for keyword in SPAM_LINK_KEYWORDS):
                logging.info(f"TTS skipped for {username}: potential spam or link")
                return 0
            if re.search(r"(.)\1{4,}", message.lower()):
                logging.info(f"TTS skipped for {username}: repeated character spam")
                return 0
            if re.search(r"(\b\w+\b(?:\s+\b\w+\b){0,4})\s+\1\s+\1", message.lower()):
                logging.info(f"TTS skipped for {username}: repeated phrase spam")
                return 0
            if any(p.search(message) for p in _TTS_SLUR_PATTERNS):
                logging.info(f"TTS skipped for {username}: matched slur/phonetic filter")
                return 0

        if not OBS_Browser_Source:
            logging.warning("OBS_Browser_Source is disabled — TTS audio will not play.")
            return 0

        audio_bytes = await _generate_audio(message, username)
        audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")
        estimated_duration = len(message.split()) * 500

        await update_latest_message(username_message[0], username_message[1], estimated_duration, audio_b64)

        logging.info("TTS done")
        return estimated_duration

    except Exception as e:
        logging.error(f"Error in TTS: {e}")
        return 0


async def text_to_shout(message, platform="Twitch"):
    try:
        logging.info("TTS shout activated for message")
        username_message = message.split(" shouts ", 1)
        username = username_message[0].strip()

        if not user_allowed_tts(username, platform):
            logging.info(f"TTS shout skipped for {username}: Not allowed by TTS_Access_{platform} setting.")
            return 0

        if not OBS_Browser_Source:
            logging.warning("OBS_Browser_Source is disabled — TTS shout will not play.")
            return 0

        audio_bytes = await _generate_audio(message, username)
        audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")
        estimated_duration = len(message.split()) * 500

        await update_latest_message(
            username_message[0], username_message[1],
            estimated_duration, audio_b64,
            volume=TTS_Shout_Volume,
        )

        return estimated_duration

    except Exception as e:
        logging.error(f"Error in TTS shout: {e}")
        return 0