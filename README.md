# TwitchChatTTSBot
A multi-platform streaming bot (Twitch, YouTube, TikTok) with TTS for chat and a browser source for OBS.  
Made with Python 3.10  
Made by foxinbox — [Twitch](https://www.twitch.tv/foxinbox4ever)

---

### Requirements

- Python 3.10+

Dependencies are installed automatically when you run `Bot.py`.

The bot can run on a **remote server (e.g. Ubuntu)** with the OBS browser source on your local Windows PC. See the OBS setup section below.

---

### Set up — Twitch

1. Download all the files in the repository
2. Copy `settings.example.json` to `settings.json` and fill in your credentials
3. Go to [dev.twitch.tv](https://dev.twitch.tv), click your console → Register Your Application:
   - OAuth Redirect URL: `http://localhost:8081`
   - Category: Chat Bot
   - Copy the **Client ID** and **Client Secret** into `settings.json`
   - Put your Twitch channel name in `settings.json`
4. Run `Bot.py`
5. On first run your browser will open asking you to authenticate. Log in with the same account you used in the Twitch dev portal.
6. After authenticating, the bot automatically refreshes your OAuth token every 3 hours so it can run indefinitely.

---

### Set up — YouTube

1. Go to [console.cloud.google.com](https://console.cloud.google.com)
2. Create a project and enable **YouTube Data API v3** (APIs & Services → Library)
3. Create an **OAuth 2.0 Client ID** (APIs & Services → Credentials → Create Credentials → OAuth 2.0 Client ID → Desktop app)
4. Under **OAuth consent screen**, add your Google account as a test user
5. Add `http://localhost:8082` as an **Authorized redirect URI** in the OAuth client settings
6. Copy the **Client ID** and **Client Secret** into `settings.json`
7. Set your **Channel ID** in `settings.json` (found at YouTube → Your channel → the `UC...` part of the URL, or Settings → Advanced settings)
8. Set `"Youtube_Bot": true` in `settings.json`
9. Run `Bot.py` — your browser will open for the one-time OAuth login; tokens are saved automatically

> **Note:** TTS replies from commands like `!braincells` are sent back to YouTube chat. Commands that require Twitch (`!subs`, `!uptime`) respond with a "Twitch only" message. Raffle picks from YouTube chatters, not Twitch viewers.

---

### Set up — TikTok

1. Set `"TikTok_Bot": true` in `settings.json`
2. Set `"TikTok_Username"` to your TikTok handle (e.g. `"foxinbox4ever"` or `"@foxinbox4ever"`)
3. Run `Bot.py` while you are **live on TikTok** — the bot connects automatically, no API key needed

> **Notes:**
> - TikTok does not have an API for sending messages, so command replies are **spoken via TTS** instead of appearing in chat.
> - Gifts are announced via TTS when received (streakable gifts are announced at the end of the streak).
> - The TikTok integration uses [TikTokLive](https://github.com/isaackogan/TikTokLive), an unofficial library. TikTok may occasionally block connections from certain IPs.
> - The bot must be started while you are already live — it does not poll for an upcoming stream.

---

### Set up OBS browser source

The TTS audio is generated on the bot's host machine and streamed to OBS via WebSocket — no local audio playback required.

**If the bot is running on the same machine as OBS:**
- In OBS, add a Browser Source and tick **Local File**
- Point it to `obs/tts_display.html`

**If the bot is running on a remote server (e.g. Ubuntu):**
- In OBS, add a Browser Source and tick **Local File**
- Set the URL to:
  ```
  file:///C:/path/to/obs/tts_display.html?host=<server-ip>:8080
  ```
  Replace `<server-ip>` with your server's local IP (e.g. `192.168.1.50`)
- Make sure port `8080` is open on the server (`sudo ufw allow 8080`)

**Both setups:**
- Set `OBS_Browser_Source` to `true` in `settings.json`
- In OBS Audio Mixer → Advanced Audio Settings, find the browser source and set **Audio Monitoring** to **Monitor and Output** so you can hear TTS locally
- Tick **Refresh browser when scene becomes active**
- Run `Bot.py` to start the WebSocket server

**TTS behaviour in the browser source:**
- Regular chat messages play immediately and overlap — multiple viewers talking at once will all be heard
- Sub, follow, and other alert events stop all currently playing TTS, show a confetti overlay, and play the alert announcement. Any messages that arrive during the alert are queued and play normally once it finishes
- Each message stays on screen for exactly as long as its audio plays, then fades out

---

### Built-in Commands

Commands are filtered per platform — `!help` only shows commands available on the platform the viewer is using.

| Command | Description | Platforms |
|---|---|---|
| `!help` | Lists commands available on the current platform, or gives help on a specific one | All |
| `!shout` | Sends louder TTS | All |
| `!raffle` | Picks a random viewer from the **same platform** (optionally `followers` or `subs` on Twitch) | All |
| `!lurk` | Says you're lurking via TTS | All |
| `!subs` | Lists current subscribers | Twitch only |
| `!discord` | Posts your Discord link | All |
| `!hug` | Sends a hug message (can target another user) | All |
| `!braincells` | Shows your brain cell count | All |
| `!uptime` | Shows how long the streamer has been live | Twitch only |
| `!dadjoke` | Sends a dad joke from JokeAPI | All |
| `!socials` | Lists all social media links from `settings.json` | All |
| `!vote` | Lets mods create a chat poll — mod only on all platforms | All |
| `!sanity` | Viewers vote on the streamer's sanity level | All |
| `!so` | Gives a shout out to another streamer — mod only on all platforms | All |
| `!followage` | Shows how long you (or another user) have been following the channel | Twitch only |
| `!8ball` | Ask the magic 8-ball a question | All |
| `!clip` | Creates a clip of the current stream (requires `clips:edit` scope) | Twitch only |

If you have new command ideas, join the Discord and message there: [Discord](https://discord.gg/UM3rmnf9zV)

---

### Alerts and notifications

The bot fires visual alerts on the OBS browser source with confetti for the following events. Each alert plays its own TTS announcement, pauses any ongoing chat TTS until it finishes, then resumes.

All Twitch events are received in real time via the [Twitch EventSub WebSocket API](https://dev.twitch.tv/docs/eventsub/) — no polling.

**Twitch**
- New follower — instant notification via EventSub
- Sub / resub — resub messages typed by the viewer are read out in TTS
- Gift sub / mystery gift — gifter and count announced
- Bits/cheer — amount and any cheer message read out, confetti card shown
- Raid — automatic shout out posted to chat with raider count

**YouTube**
- New member (`newSponsorEvent`)
- Member milestone (`memberMilestoneChatEvent`)
- Membership gift (`membershipGiftingEvent`)
- Super Chat (`superChatEvent`) — amount and message included in the TTS

Alert types show different styles in the browser source:

| Type | Icon | Colour |
|---|---|---|
| New follower | ✨ | Purple |
| New member / milestone / gift | ⭐ | Gold |
| Super Chat | 💰 | Green |
| Bits / cheer | 💎 | Blue |

---

### Settings

| Key | Value | Description |
|---|---|---|
| `Twitch_Bot` | `true`/`false` | Enables the Twitch bot |
| `Twitch_Client_ID` | string | Your Twitch application Client ID |
| `Twitch_Client_Secret` | string | Your Twitch application Client Secret |
| `Twitch_Token` | string | OAuth token (auto-filled on first run) |
| `Twitch_Refresh_Token` | string | Refresh token (auto-filled on first run) |
| `Twitch_Name` | string | Your Twitch channel name |
| `Youtube_Bot` | `true`/`false` | Enables the YouTube bot |
| `YouTube_Client_ID` | string | Your YouTube OAuth Client ID |
| `YouTube_Client_Secret` | string | Your YouTube OAuth Client Secret |
| `YouTube_Token` | string | YouTube access token (auto-filled on first run) |
| `YouTube_Channel_ID` | string | Your YouTube channel ID (`UC...`) |
| `TikTok_Bot` | `true`/`false` | Enables the TikTok bot |
| `TikTok_Username` | string | Your TikTok username (with or without `@`) |
| `TTS_Access` | `all`/`followers`/`subs`/`off` | Global TTS access fallback — used if a platform-specific key below is not set |
| `TTS_Access_Twitch` | `all`/`followers`/`subs`/`off` | Who can use TTS on Twitch |
| `TTS_Access_YouTube` | `all`/`members`/`off` | Who can use TTS on YouTube (`members` = channel members only) |
| `TTS_Access_TikTok` | `all`/`off` | Who can use TTS on TikTok |
| `TTS_Shout_Volume` | `0.0`–`1.0` | Volume for the `!shout` command |
| `TTS_Random_Voice` | `true`/`false` | Assigns each viewer a unique random voice that stays consistent for them throughout the session — no two viewers share the same voice |
| `TTS_Voice` | string | The system/bot voice, always used for bot announcements (e.g. sub/raid alerts). Also used for all TTS when `TTS_Random_Voice` is `false`. Run `edge-tts --list-voices` to see options (e.g. `"en-GB-SoniaNeural"`) |
| `OBS_Websocket_Port` | number | Port the WebSocket server listens on (default `8080`) |
| `OBS_Browser_Source` | `true`/`false` | Enables the OBS browser source and WebSocket TTS delivery |
| `OBS_Bobble_image` | file path | Path to the bobble head image shown in the browser source (default: `obs/dwightHead.png`) |
| `Sanity_Bar` | `true`/`false` | Enables the sanity bar in the OBS browser source |
| `enable_sound_effects` | `true`/`false` | Enables or disables sound effects |
| `sound_effects_file_path` | file path | Folder containing sound effect MP3 files |
| `sound_effects_cooldown` | number | Default cooldown between sound effects (seconds) |

---

### Add more social media links

Add a link in this format to `settings.json`:
```json
"Social_Link": "URL"
```
The key must end in `_Link`.

---

### Add more sound effects

- Save the MP3 to your sound effects folder
- In `Bot.py`, call `play_sound_from_file(sound_effects, "Example.mp3", True)` (second argument enables cooldown)
- To play without a cooldown: `play_sound_from_file(sound_effects, "Example.mp3", False)`
- To set a per-file cooldown: `set_sound_cooldown_from_file(sound_effects, "Example.mp3", 5)`

---

### Add more commands

- Create a new class in `Commands.py` that extends `BaseCommand`
- Add an `async def execute(self, send_reply, username, message, channel, token, client_id, broadcaster_id)` method
  - `send_reply(msg)` sends a response back to chat (or TTS on TikTok)
  - `channel` is the Twitch channel string, `"YouTube"`, or `"TikTok"` — use this to add platform-specific behaviour
- Add the class to the `COMMANDS` dictionary with the trigger string as the key

See the existing commands in `Commands.py` as examples.

---

### Running on a remote server (e.g. Ubuntu VPS)

The bot can run headlessly on a remote Linux server while your OBS stays on your local Windows PC. The TTS audio is streamed over WebSocket so no audio hardware is needed on the server.

**On the server:**

1. Install Python 3.10+ and pip:
   ```bash
   sudo apt install python3 python3-pip tmux -y
   ```

2. Copy `settings.example.json` to `settings.json`, fill in your credentials, and set:
   ```json
   "OBS_Browser_Source": true
   ```

3. Open port 8080 on the server firewall:
   ```bash
   sudo ufw allow 8080
   ```

4. Run the bot inside a tmux session so it keeps running after you disconnect:
   ```bash
   tmux new -s bot
   python3 Bot.py
   ```
   Detach with `Ctrl+B` then `D`. Reattach later with `tmux attach -t bot`.

5. On first run, an OAuth URL will be printed — paste it into your browser on your local machine, authenticate, and the tokens will be saved automatically. The bot refreshes them every 3 hours on its own.

**On your local Windows PC (OBS):**

1. Copy `obs/tts_display.html` (and `obs/sanity_bar.html` if using the sanity bar) to your PC.

2. In OBS, add a Browser Source → tick **Local File** → point it to `obs/tts_display.html`.

3. Append the server's local IP and port as a query parameter:
   ```
   file:///C:/path/to/obs/tts_display.html?host=<server-ip>:8080
   ```
   Replace `<server-ip>` with your server's LAN IP (e.g. `192.168.1.50`).

4. In OBS Audio Mixer → Advanced Audio Settings, set the browser source to **Monitor and Output**.

5. Tick **Refresh browser when scene becomes active**.

**Capturing logs:**

To save the bot's output for debugging after a session:
```bash
tmux capture-pane -p -S - > output.txt
```

---

Enjoy using the bot and customising it to your community's vibe!

If you have any issues join the [Discord](https://discord.gg/UM3rmnf9zV)
