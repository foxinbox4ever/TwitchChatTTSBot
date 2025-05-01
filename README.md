# TwitchChatTTSBot
This is a simple twitch bot that handles TTS for chat and a browser source for OBS. \
Made with python 3.10\
Made by foxinbox 

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

### Add more social media links;

- Add the link in this format to settings.json "Social_Link": "URL"

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
