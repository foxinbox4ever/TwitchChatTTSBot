# TwitchChatTTSBot
This is a simple twitch bot that handles TTS for chat and a browser source for OBS. \
Made with python 3.10\
Made by foxinbox 
[twitch](https://www.twitch.tv/foxinbox4ever)

### Set up;

- Check requirements.txt to see what libraries you will need to install with pip
- Download all the files in the repository
- Open settings.json and adjust the settings you want for the bot
- Go to dev.Twitch.tv in the top right hand corner of the screen, click your console, click register your application, give it a name, OAuth Redirect URL http://localhost:8081, select chat bot, click create, click manage on the bot you created, copy the client ID to your settings.json, click create secret, copy the client secret to your settings.json, put your twitch name in settings.json
- run Bot.py
- The first time you run it, your browser should open and ask you to authenticate the bot. Please ensure you're logged in on the same account as the one that you created the bot in the Twitch dev portal

### Set up OBS/Streamlabs browser source;

- Go open settings.json and set OBS_Browser_Source to true
- Open OBS/Streamlabs
- Click the check mark for local file
- Change the file to the tts_display.html you installed
- Adjust height and width to your liking
- Click the check mark for refresh browser when scene becomes active
- Run Bot.py to start the websocket server

### Built-in Commands;

- "!help" - Lists all commands, or gives help on a specific one.
- "!shout" - Sends louder TTS (volume configurable).
- "!raffel" - Picks a random viewer (optionally only subs or followers).
- "!lurk" - 	Says you're lurking.
- "!subs" - Lists current subscribers.
- "!discord" - Posts your Discord link.
- "!hug" - Sends a hug message (target another user if desired).
- "!braincells" - Shows your brain cell count.
- "!uptime" - Shows how long the streamer has been live.
- "!dadjoke" - Sends a dad joke from JokeAPI (AI version coming soon).
- "!socials" - Lists all social media links from settings.json.
- "!vote" - Lets mods create a chat poll (OBS-based or Twitch native).
- "!sanity" - Viewers vote on the streamer's sanity level (can show in OBS).

  If you have any new command ideas, join my twitch discord and message me there. [Discord](https://discord.gg/UM3rmnf9zV)

### Settings

- Twitch_Bot - true or false, enables the twitch bot.
- Twitch_Client_ID - this is your client ID and is required to run the twitch bot. (see setup to find out how to get one)
- Twitch_Client_Secret - this is your client secret and is required to run the twitch bot. (see setup to find out how to get one)
- Twitch_Token - this is your bots oauth token for twitch allowing it to interact with the API. (to store the token)
- Twitch_Refresh_Token - this is used to refresh the oauth token when its no longer valid.
- Twitch_Name - this is your twitch channel name.
- YouTube_Bot - true or false, enables the youtube bot. The youtube bot functionality isnt complete yet, so keep it false.
- YouTube_Client_ID - this is your client ID and is required to run the youtube bot.
- YouTube_Client_Secret - this is your client secret and is required to run the youtube bot.
- YouTube_Token - this is your bots oauth token for youtube allowing it to interact with the API. (to store the token)
- YouTube_Channel_ID - this is your youtube channel ID and is required to run the youtube bot.
- TTS_Access - all, followers, subs, or off. Allows you to specify which users are allowed to use the TTS.
- TTS_Volume - 0 - 1. Allows you to set the volume of the TTS.
- TTS_Shout_Volume - 0 - 1. Allows you to set the TTS volume for the "!shout" command.
- TTS_Random_Voice - true or false. Allows you to have a random voice for each message from the downloaded windows voices.
- TTS_Voice - 0 - the number of installed voices (for English up to 2). Sets the TTS voice.
- enable_sound_effects - true or false. Enables or disables the sound effects functionality.
- sound_effects_file_path - file path. Is the file path for the sound effects.
- sound_effects_cooldown - number. Allows you to set the cool down for the sound effects in secounds.
- OBS_Browser_Source - true or false. Allows you to turn the OBS browser source functionality on or off.
- OBS_Bobble_image - file path. This is the file path of the bobble image for the browser source.
- Sanity_Bar - true or false. Allows you to turn the OBS browser source functionality on or off for the sanity bar.

### Add more social media links;

- Add the link in this format to settings.json "Social_Link": "URL" (ensure you put _Link after the name of the link)

### Add more sound effects;

- Save the mp3 file to the sound effects folder (location of this can be adjusted in settings)
- Adjust Bot.py so it plays the sound effect when you want it to with play_sound_from_file(sound_effects, "Example.mp3", True)
- To make it play without a cooldown play_sound_from_file(sound_effects, "Example.mp3", False)
- To change the cooldown e.g set the cooldown to 5 seconds set_sound_cooldown_from_file(sound_effects, "Example.mp3", 5) or adjust in the settings folder what the default cooldown is

### Add more commands;

- Create a new class in Commands.py that imports the BaseCommand
- Create a function in the class called execute (this is where you write what the command does)
- Add it to the COMMANDS dictionary with how you want the command to be called by the users as the key 

See the other commands that I have already written as an example 

### Known issues
Claro read TTS not fully setup yet (deleted from the repository)
The youtube bot has not been tested and will not work with commands or most things.

Enjoy using the bot and customising it to your community's vibe!

If you have any issues join my [discord](https://discord.gg/UM3rmnf9zV)
