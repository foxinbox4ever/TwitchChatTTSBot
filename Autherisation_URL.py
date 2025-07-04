import requests
import webbrowser
import json
import http.server
import socketserver
import threading
import logging
import time
import urllib.parse
import os

# Twitch redirect URI - must match what's in your Twitch Developer Console
REDIRECT_URI = "http://localhost:8081"

# OAuth scopes for Twitch
OAUTH_SCOPES = [
    "analytics:read:extensions", "user:edit", "user:read:email", "clips:edit", "bits:read",
    "analytics:read:games", "user:edit:broadcast", "user:read:broadcast", "chat:read", "chat:edit",
    "channel:moderate", "channel:read:subscriptions", "whispers:read", "whispers:edit", "moderation:read",
    "channel:read:redemptions", "channel:edit:commercial", "channel:read:hype_train", "channel:read:stream_key",
    "channel:manage:extensions", "channel:manage:broadcast", "user:edit:follows", "channel:manage:redemptions",
    "channel:read:editors", "channel:manage:videos", "user:read:blocked_users", "user:manage:blocked_users",
    "user:read:subscriptions", "user:read:follows", "channel:manage:polls", "channel:manage:predictions",
    "channel:read:polls", "channel:read:predictions", "moderator:manage:automod", "channel:manage:schedule",
    "channel:read:goals", "moderator:read:automod_settings", "moderator:manage:automod_settings",
    "moderator:manage:banned_users", "moderator:read:blocked_terms", "moderator:manage:blocked_terms",
    "moderator:read:chat_settings", "moderator:manage:chat_settings", "channel:manage:raids",
    "moderator:manage:announcements", "moderator:manage:chat_messages", "user:manage:chat_color",
    "channel:manage:moderators", "channel:read:vips", "channel:manage:vips", "user:manage:whispers",
    "channel:read:charity", "moderator:read:chatters", "moderator:read:shield_mode",
    "moderator:manage:shield_mode", "moderator:read:shoutouts", "moderator:manage:shoutouts",
    "moderator:read:followers", "channel:read:guest_star", "channel:manage:guest_star",
    "moderator:read:guest_star", "moderator:manage:guest_star", "channel:bot", "user:bot",
    "user:read:chat", "channel:manage:ads", "channel:read:ads", "user:read:moderated_channels",
    "user:write:chat", "user:read:emotes", "moderator:read:unban_requests", "moderator:manage:unban_requests",
    "moderator:read:suspicious_users", "moderator:manage:warnings"
]
OAUTH_SCOPE = " ".join(OAUTH_SCOPES)


class OAuthHandler(http.server.SimpleHTTPRequestHandler):
    """Handles Twitch OAuth redirect and captures the authorization code."""
    auth_code = None

    def do_GET(self):
        parsed_path = urllib.parse.urlparse(self.path)
        query = urllib.parse.parse_qs(parsed_path.query)
        if "code" in query:
            OAuthHandler.auth_code = query["code"][0]
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(b"<h1>Authorization complete. You may now close this window.</h1>")
        elif "error" in query:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b"<h1>Authorization failed or denied.</h1>")
        else:
            self.send_response(400)
            self.end_headers()


def start_http_server():
    """Starts the local server to handle Twitch redirect."""
    httpd = socketserver.TCPServer(("localhost", 8081), OAuthHandler)
    server_thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    server_thread.start()
    return httpd

def refresh_token_if_available(client_id, client_secret):
    """Refreshes the Twitch access token if refresh token is available."""
    try:
        if not os.path.exists("settings.json"):
            logging.info("settings.json not found. Cannot refresh token.")
            return None

        with open("settings.json", "r") as f:
            settings = json.load(f)

        refresh_token = settings.get("Twitch_Refresh_Token")
        if not refresh_token:
            logging.info("No refresh token found in settings.")
            return None

        payload = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": client_id,
            "client_secret": client_secret,
        }

        response = requests.post("https://id.twitch.tv/oauth2/token", data=payload)
        logging.info(f"Token refresh response: {response.status_code} - {response.text}")

        if response.status_code != 200:
            logging.warning("Failed to refresh token. Will require full authorization.")
            return None

        token_data = response.json()
        access_token = token_data.get("access_token")
        new_refresh_token = token_data.get("refresh_token", refresh_token)  # fallback to old

        # Update the settings with new tokens
        settings["Twitch_Token"] = f"oauth:{access_token}"
        settings["Twitch_Refresh_Token"] = new_refresh_token
        with open("settings.json", "w") as f:
            json.dump(settings, f, indent=4)

        logging.info("Access token successfully refreshed and saved.")
        return f"oauth:{access_token}"

    except Exception as e:
        logging.error(f"Error during token refresh: {e}")
        return None

def autherise(client_id, client_secret):
    """Attempts to refresh token first; falls back to full OAuth if needed."""
    logging.info("Attempting to refresh token if available...")

    refreshed_token = refresh_token_if_available(client_id, client_secret)
    if refreshed_token:
        logging.info("Token successfully refreshed. Skipping full OAuth.")
        return refreshed_token

    # If refresh fails, proceed with full OAuth authorization
    logging.info("Starting full OAuth authorization...")

    auth_url = (
        "https://id.twitch.tv/oauth2/authorize"
        f"?client_id={client_id}"
        f"&redirect_uri={REDIRECT_URI}"
        f"&response_type=code"
        f"&scope={urllib.parse.quote(OAUTH_SCOPE)}"
        "&force_verify=true"
    )

    print("\nIf your browser doesn't open automatically, paste this into your browser:\n")
    print(auth_url + "\n")
    webbrowser.open(auth_url)

    httpd = start_http_server()
    logging.info("Waiting for Twitch OAuth redirect on port 8081...")

    timeout = 60  # seconds
    start_time = time.time()
    while OAuthHandler.auth_code is None:
        if time.time() - start_time > timeout:
            logging.error("OAuth timeout: No code received within 60 seconds.")
            httpd.shutdown()
            httpd.server_close()
            return None
        time.sleep(1)

    httpd.shutdown()
    httpd.server_close()

    auth_code = OAuthHandler.auth_code
    logging.info(f"Received auth code: {auth_code}")

    # Exchange code for access token
    token_url = "https://id.twitch.tv/oauth2/token"
    payload = {
        "client_id": client_id,
        "client_secret": client_secret,
        "code": auth_code,
        "grant_type": "authorization_code",
        "redirect_uri": REDIRECT_URI,
    }

    response = requests.post(token_url, data=payload)
    logging.info(f"Token exchange response: {response.status_code} - {response.text}")

    if response.status_code != 200:
        logging.error("Failed to exchange code for token.")
        return None

    token_data = response.json()
    access_token = token_data.get("access_token")
    refresh_token = token_data.get("refresh_token", "")

    if not access_token:
        logging.error("Access token missing from response.")
        return None

    logging.info("Access token received and validated.")

    # Update settings.json
    try:
        settings = {}
        if os.path.exists("settings.json"):
            with open("settings.json", "r") as f:
                settings = json.load(f)

        # Prefix with 'oauth:' for Twitch IRC login
        settings["Twitch_Token"] = f"oauth:{access_token}"
        settings["Twitch_Refresh_Token"] = refresh_token

        with open("settings.json", "w") as f:
            json.dump(settings, f, indent=4)

        logging.info("Updated Twitch_Token and refresh token in settings.json.")
    except Exception as e:
        logging.warning(f"Could not update settings.json: {e}")

    return f"oauth:{access_token}"  # Use this directly in IRC connection

import requests
import webbrowser
import json
import http.server
import socketserver
import threading
import logging
import time
import urllib.parse
import os

# Redirect URI must match the one registered in Google Cloud Console for your OAuth client
YOUTUBE_REDIRECT_URI = "http://localhost:8082"

YOUTUBE_OAUTH_SCOPES = [
    "https://www.googleapis.com/auth/youtube",
    "https://www.googleapis.com/auth/youtube.force-ssl",
    "https://www.googleapis.com/auth/youtube.readonly",
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtubepartner",
    "https://www.googleapis.com/auth/youtube.channel-memberships.creator",
    "https://www.googleapis.com/auth/youtube.manage",
    "https://www.googleapis.com/auth/youtube.readonly",
    "https://www.googleapis.com/auth/youtube.transaction",
    "https://www.googleapis.com/auth/youtube.moderation",
    "https://www.googleapis.com/auth/youtube.channel-memberships.creator"
]


YOUTUBE_OAUTH_SCOPE = " ".join(YOUTUBE_OAUTH_SCOPES)


class YouTubeOAuthHandler(http.server.SimpleHTTPRequestHandler):
    """Handles YouTube OAuth redirect and captures the authorization code."""
    auth_code = None

    def do_GET(self):
        parsed_path = urllib.parse.urlparse(self.path)
        query = urllib.parse.parse_qs(parsed_path.query)
        if "code" in query:
            YouTubeOAuthHandler.auth_code = query["code"][0]
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(b"<h1>YouTube authorization complete. You may close this window.</h1>")
        elif "error" in query:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b"<h1>YouTube authorization failed or denied.</h1>")
        else:
            self.send_response(400)
            self.end_headers()


def start_youtube_http_server():
    """Starts the local server to handle YouTube redirect."""
    httpd = socketserver.TCPServer(("localhost", 8082), YouTubeOAuthHandler)
    server_thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    server_thread.start()
    return httpd


def authorise_youtube(client_id, client_secret):
    """Full YouTube OAuth2 flow to get access and refresh tokens."""

    auth_url = (
        "https://accounts.google.com/o/oauth2/v2/auth"
        f"?client_id={client_id}"
        f"&redirect_uri={urllib.parse.quote(YOUTUBE_REDIRECT_URI)}"
        f"&response_type=code"
        f"&scope={urllib.parse.quote(YOUTUBE_OAUTH_SCOPE)}"
        "&access_type=offline"  # To get refresh token
        "&prompt=consent"  # Force consent every time, to ensure refresh token
    )

    print("\nIf your browser doesn't open automatically, paste this into your browser:\n")
    print(auth_url + "\n")
    webbrowser.open(auth_url)

    httpd = start_youtube_http_server()
    logging.info("Waiting for YouTube OAuth redirect on port 8082...")

    timeout = 120  # seconds, YouTube flow might take longer
    start_time = time.time()
    while YouTubeOAuthHandler.auth_code is None:
        if time.time() - start_time > timeout:
            logging.error("OAuth timeout: No code received within 120 seconds.")
            httpd.shutdown()
            httpd.server_close()
            return None
        time.sleep(1)

    httpd.shutdown()
    httpd.server_close()

    auth_code = YouTubeOAuthHandler.auth_code
    logging.info(f"Received YouTube auth code: {auth_code}")

    # Exchange code for tokens
    token_url = "https://oauth2.googleapis.com/token"
    payload = {
        "code": auth_code,
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": YOUTUBE_REDIRECT_URI,
        "grant_type": "authorization_code",
    }

    response = requests.post(token_url, data=payload)
    logging.info(f"YouTube token exchange response: {response.status_code} - {response.text}")

    if response.status_code != 200:
        logging.error("Failed to exchange code for YouTube tokens.")
        return None

    token_data = response.json()
    access_token = token_data.get("access_token")
    refresh_token = token_data.get("refresh_token", "")

    if not access_token:
        logging.error("Access token missing from YouTube token response.")
        return None

    logging.info("Access token received and validated from YouTube.")

    # Save tokens to settings.json
    try:
        settings = {}
        if os.path.exists("settings.json"):
            with open("settings.json", "r") as f:
                settings = json.load(f)

        settings["YouTube_Token"] = access_token
        settings["YouTube_Refresh_Token"] = refresh_token

        with open("settings.json", "w") as f:
            json.dump(settings, f, indent=4)

        logging.info("Updated YouTube_Token and refresh token in settings.json.")
    except Exception as e:
        logging.warning(f"Could not update settings.json with YouTube tokens: {e}")

    return access_token


def refresh_youtube_token(client_id, client_secret, refresh_token):
    """Refresh YouTube access token using refresh token."""
    token_url = "https://oauth2.googleapis.com/token"
    payload = {
        "client_id": client_id,
        "client_secret": client_secret,
        "refresh_token": refresh_token,
        "grant_type": "refresh_token",
    }

    response = requests.post(token_url, data=payload)
    logging.info(f"YouTube token refresh response: {response.status_code} - {response.text}")

    if response.status_code != 200:
        logging.error("Failed to refresh YouTube token.")
        return None

    token_data = response.json()
    new_access_token = token_data.get("access_token")
    if not new_access_token:
        logging.error("No access token returned on refresh.")
        return None

    # Update settings.json with new access token
    try:
        settings = {}
        if os.path.exists("settings.json"):
            with open("settings.json", "r") as f:
                settings = json.load(f)

        settings["YouTube_Token"] = new_access_token
        with open("settings.json", "w") as f:
            json.dump(settings, f, indent=4)

        logging.info("Refreshed YouTube access token saved in settings.json.")
    except Exception as e:
        logging.warning(f"Could not update settings.json with refreshed YouTube token: {e}")

    return new_access_token

def authenticate_youtube(client_id, client_secret):
    """Try existing token, refresh if needed, else reauthorize."""
    if not os.path.exists("settings.json"):
        logging.info("settings.json not found. Starting full YouTube OAuth.")
        return authorise_youtube(client_id, client_secret)

    with open("settings.json", "r") as f:
        settings = json.load(f)

    access_token = settings.get("YouTube_Token")
    refresh_token = settings.get("YouTube_Refresh_Token")

    # Validate current token with a lightweight API call
    headers = {"Authorization": f"Bearer {access_token}"}
    response = requests.get("https://www.googleapis.com/youtube/v3/channels?part=id&mine=true", headers=headers)

    if response.status_code == 200:
        logging.info("YouTube access token is valid.")
        return access_token
    else:
        logging.warning(f"Access token invalid (status {response.status_code}). Attempting refresh...")

    if refresh_token:
        new_token = refresh_youtube_token(client_id, client_secret, refresh_token)
        if new_token:
            logging.info("YouTube token successfully refreshed.")
            return new_token

    logging.warning("Refresh failed or no refresh token. Falling back to full OAuth.")
    return authorise_youtube(client_id, client_secret)
