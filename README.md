# TwitchChatTTSBot
A Twitch (and partial YouTube) bot that handles TTS for chat and a browser source for OBS.  
Made with Python 3.10  
Made by foxinbox — [Twitch](https://www.twitch.tv/foxinbox4ever)

---

### Requirements

- Python 3.10+
- Install dependencies: `pip install -r requirements.txt` (includes `edge-tts`)

The bot can run on a **remote server (e.g. Ubuntu)** with the OBS browser source on your local Windows PC. See the OBS setup section below.

---

### Set up

- Download all the files in the repository
- Copy `settings.json` and fill in your credentials (see Settings section below)
- Go to [dev.twitch.tv](https://dev.twitch.tv), click your console → Register Your Application:
  - OAuth Redirect URL: `http://localhost:8081`
  - Category: Chat Bot
  - Copy the **Client ID** and **Client Secret** into `settings.json`
  - Put your Twitch channel name in `settings.json`
- Run `Bot.py`
- The first time you run it, your browser will open and ask you to authenticate. Make sure you're logged in on the same account used to create the bot in the Twitch dev portal.
- After authenticating, the bot will automatically refresh your OAuth token every 3 hours so it can run indefinitely without needing a restart.

---

### Set up OBS browser source

The TTS audio is generated on the bot's host machine and streamed to OBS via WebSocket — no local audio playback required.

**If the bot is running on the same machine as OBS:**
- In OBS, add a Browser Source and tick **Local File**
- Point it to `tts_display.html`

**If the bot is running on a remote server (e.g. Ubuntu):**
- In OBS, add a Browser Source and tick **Local File**
- Set the URL to:
  ```
  file:///C:/path/to/tts_display.html?host=<server-ip>:8080
  ```
  Replace `<server-ip>` with your server's local IP (e.g. `192.168.1.50`)
- Make sure port `8080` is open on the server (`sudo ufw allow 8080`)

**Both setups:**
- Set `OBS_Browser_Source` to `true` in `settings.json`
- In OBS Audio Mixer → Advanced Audio Settings, find the browser source and set **Audio Monitoring** to **Monitor and Output** so you can hear TTS locally
- Tick **Refresh browser when scene becomes active**
- Run `Bot.py` to start the WebSocket server

---

### Built-in Commands

| Command | Description |
|---|---|
| `!help` | Lists all commands, or gives help on a specific one |
| `!shout` | Sends louder TTS (volume configurable via `TTS_Shout_Volume`) |
| `!raffle` | Picks a random viewer (optionally only subs or followers) |
| `!lurk` | Says you're lurking |
| `!subs` | Lists current subscribers |
| `!discord` | Posts your Discord link |
| `!hug` | Sends a hug message (can target another user) |
| `!braincells` | Shows your brain cell count |
| `!uptime` | Shows how long the streamer has been live |
| `!dadjoke` | Sends a dad joke from JokeAPI |
| `!socials` | Lists all social media links from `settings.json` |
| `!vote` | Lets mods create a chat poll (shown in OBS browser source) |
| `!sanity` | Viewers vote on the streamer's sanity level |

If you have new command ideas, join the Discord and message there: [Discord](https://discord.gg/UM3rmnf9zV)

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
| `YouTube_Bot` | `true`/`false` | Enables the YouTube bot (experimental) |
| `YouTube_Client_ID` | string | Your YouTube OAuth Client ID |
| `YouTube_Client_Secret` | string | Your YouTube OAuth Client Secret |
| `YouTube_Token` | string | YouTube access token (auto-filled) |
| `YouTube_Channel_ID` | string | Your YouTube channel ID |
| `TTS_Access` | `all`/`followers`/`subs`/`off` | Who is allowed to use TTS |
| `TTS_Shout_Volume` | `0.0`–`1.0` | Volume for the `!shout` command |
| `TTS_Random_Voice` | `true`/`false` | Assigns each viewer a unique random voice that stays consistent for them throughout the session — no two viewers share the same voice |
| `TTS_Voice` | string | The system/bot voice, always used for bot announcements (e.g. sub/raid alerts). Also used for all TTS when `TTS_Random_Voice` is `false`. Run `edge-tts --list-voices` to see options (e.g. `"en-GB-SoniaNeural"`) |
| `OBS_Websocket_Port` | number | Port the WebSocket server listens on (default `8080`) |
| `OBS_Browser_Source` | `true`/`false` | Enables the OBS browser source and WebSocket TTS delivery |
| `OBS_Bobble_image` | file path | Path to the bobble head image shown in the browser source |
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
- Add an `async def execute(self, connection, username, message, channel, token, client_id, broadcaster_id)` method
- Add the class to the `COMMANDS` dictionary with the trigger string as the key

See the existing commands in `Commands.py` as examples.

---

### Running on a remote server (e.g. Ubuntu VPS)

The bot can run headlessly on a remote Linux server while your OBS stays on your local Windows PC. The TTS audio is streamed over WebSocket so no audio hardware is needed on the server.

**On the server:**

1. Install Python 3.10+ and dependencies:
   ```bash
   sudo apt install python3 python3-pip tmux -y
   pip install -r requirements.txt
   ```

2. Fill in `settings.json` with your credentials and set:
   ```json
   "OBS_Browser_Source": true
   ```

3. Open port 8765 on the server firewall:
   ```bash
   sudo ufw allow 8765
   ```

4. Run the bot inside a tmux session so it keeps running after you disconnect:
   ```bash
   tmux new -s bot
   python3 Bot.py
   ```
   Detach with `Ctrl+B` then `D`. Reattach later with `tmux attach -t bot`.

5. The first run will print an OAuth URL — paste it into your browser on your local machine, authenticate, and the tokens will be saved automatically. The bot will then refresh them every 3 hours on its own.

**On your local Windows PC (OBS):**

1. Copy `tts_display.html` (and `sanity_bar.html` if using the sanity bar) to your PC.

2. In OBS, add a Browser Source → tick **Local File** → point it to `tts_display.html`.

3. Append the server's local IP and port as a query parameter:
   ```
   file:///C:/path/to/tts_display.html?host=<server-ip>:8765
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

### Known issues

- The YouTube bot is experimental and not fully tested — keep `YouTube_Bot` set to `false`.

---

Enjoy using the bot and customising it to your community's vibe!

If you have any issues join the [Discord](https://discord.gg/UM3rmnf9zV)
