import logging
logger = logging.getLogger(__name__)
import threading
import requests
from concurrent.futures import ThreadPoolExecutor

viewers = []
_viewers_lock = threading.Lock()
_viewer_executor = ThreadPoolExecutor(max_workers=20, thread_name_prefix="viewer-lookup")

youtube_viewers = []
youtube_viewer_status = {}  # username_lower -> {"member": bool, "moderator": bool}
_youtube_viewers_lock = threading.Lock()


def add_youtube_viewer(username, is_member=False, is_moderator=False):
    username_lower = username.strip().lower()
    with _youtube_viewers_lock:
        if username_lower not in youtube_viewers:
            youtube_viewers.append(username_lower)
            logger.debug(f"Added YouTube viewer: {username_lower}")
        youtube_viewer_status[username_lower] = {
            "member": is_member,
            "moderator": is_moderator,
        }


def remove_youtube_viewer(username):
    username_lower = username.strip().lower()
    with _youtube_viewers_lock:
        if username_lower in youtube_viewers:
            youtube_viewers.remove(username_lower)
            logger.debug(f"Removed YouTube viewer: {username_lower}")


tiktok_viewers = []
_tiktok_viewers_lock = threading.Lock()


def add_tiktok_viewer(username):
    username_lower = username.strip().lower()
    with _tiktok_viewers_lock:
        if username_lower not in tiktok_viewers:
            tiktok_viewers.append(username_lower)
            logger.debug(f"Added TikTok viewer: {username_lower}")


def remove_tiktok_viewer(username):
    username_lower = username.strip().lower()
    with _tiktok_viewers_lock:
        if username_lower in tiktok_viewers:
            tiktok_viewers.remove(username_lower)
            logger.debug(f"Removed TikTok viewer: {username_lower}")

class Viewer:
    def __init__(self, username, token, client_id, broadcaster_id):
        self.username = username.strip().lower()
        self.token = token
        self.client_id = client_id
        self.broadcaster_id = broadcaster_id
        self.user_id = self.get_user_id_from_username()
        self.following = self.check_if_follower()
        self.subscribed = self.check_if_subbed()
        self.mod = self.check_if_mod()


        logger.debug(f"Initialized viewer: {self.username}")

    def get_headers(self):
        return {
            'Authorization': f'Bearer {self.token}',
            'Client-ID': self.client_id
        }

    def get_user_id_from_username(self):
        headers = self.get_headers()
        response = requests.get(
            f'https://api.twitch.tv/helix/users?login={self.username}',
            headers=headers,
            timeout=10
        )
        try:
            user_data = response.json()
        except Exception as e:
            logger.error(f"Error decoding Twitch response: {e}")
            return None

        logger.debug(f"User data response for {self.username}: {user_data}")

        if response.status_code == 200 and 'data' in user_data and user_data['data']:
            user_id = user_data['data'][0]['id']
            logger.debug(f"User ID for {self.username} is {user_id}")
            return user_id
        else:
            message = user_data.get('message', 'No message')
            logger.warning(f"Could not find user {self.username}. Status: {response.status_code}, Message: {message}")
            return None

    def check_if_follower(self):
        logger.debug(f"Checking if {self.username} is following {self.broadcaster_id}")

        if not self.user_id:
            logger.error(f"User {self.username} has no ID")
            return False

        headers = self.get_headers()
        follows_url = f'https://api.twitch.tv/helix/channels/followers?broadcaster_id={self.broadcaster_id}&user_id={self.user_id}'
        response = requests.get(follows_url, headers=headers, timeout=10)

        logger.debug(f"Follower API response: {response.status_code}")

        if response.status_code == 400:
            logger.error("Bad Request: check broadcaster_id and user_id params")
            return False

        elif response.status_code == 401:
            logger.error("Unauthorized access. Missing scope: user:read:follows")
            return False

        elif response.status_code == 200:
            data = response.json().get("data", [])
            if data:
                logger.debug(f"{self.username} **is** following {self.broadcaster_id}")
                return True
            else:
                logger.debug(f"{self.username} **is NOT** following {self.broadcaster_id}")
                return False

    def check_if_subbed(self):
        logger.debug(f"Checking if {self.username} is subbed")

        if not self.user_id:
            logger.error(f"User {self.username} has no ID")
            return False

        headers = self.get_headers()
        subs_url = f"https://api.twitch.tv/helix/subscriptions?broadcaster_id={self.broadcaster_id}&user_id={self.user_id}"
        response = requests.get(subs_url, headers=headers, timeout=10)

        logger.debug(f"Subscription API response: {response.status_code}")

        if response.status_code == 200:
            data = response.json().get("data", [])
            if data:
                logger.debug(f"User {self.username} **is** subscribed to {self.broadcaster_id}")
                return True
            else:
                logger.debug(f"User {self.username} **is NOT** subscribed to {self.broadcaster_id}")
                return False

        elif response.status_code == 401:
            logger.error("Unauthorized access. Missing scope: channel:read:subscriptions")
            return False

        else:
            logger.warning(f"Unexpected subscription response: {response.status_code}")
            return False

    def check_if_mod(self):
        logger.debug(f"Checking if {self.username} is a mod")

        if not self.user_id:
            logger.error(f"User {self.username} has no ID")
            return False

        # Viewer is the broadcaster — always has mod-level access
        if self.user_id == self.broadcaster_id:
            logger.debug(f"{self.username} **is** the broadcaster — treated as mod")
            return True

        headers = self.get_headers()
        url = (
            f"https://api.twitch.tv/helix/moderation/moderators"
            f"?broadcaster_id={self.broadcaster_id}&user_id={self.user_id}"
        )
        response = requests.get(url, headers=headers, timeout=10)

        logger.debug(f"Moderator API response: {response.status_code}")

        if response.status_code == 401:
            logger.error("Unauthorized access. Missing scope: moderation:read")
            return False

        elif response.status_code == 200:
            data = response.json().get("data", [])
            if any(entry["user_id"] == self.user_id for entry in data):
                logger.debug(f"{self.username} **is** a moderator")
                return True
            else:
                logger.debug(f"{self.username} **is NOT** a moderator")
                return False

        else:
            logger.warning(f"Unexpected response when checking mod status: {response.status_code}")
            return False

    def update_status(self):
        self.following = self.check_if_follower()
        self.subscribed = self.check_if_subbed()
        self.mod = self.check_if_mod()
        logger.info(f"Updated status for {self.username} — Follower: {self.following}, Sub: {self.subscribed}, Mod: {self.mod}")


def new_viewer(username, token, client_id, broadcaster_id):
    username_lower = username.lower()

    with _viewers_lock:
        if any(v.username == username_lower for v in viewers):
            logger.debug(f"{username} already exists in the viewer list.")
            return

    viewer = Viewer(username=username, token=token, client_id=client_id, broadcaster_id=broadcaster_id)

    with _viewers_lock:
        if any(v.username == username_lower for v in viewers):
            return
        viewers.append(viewer)

    logger.debug(f"Added viewer: {viewer.username}")


def new_viewer_wrapper(username, token, client_id, broadcaster_id):
    try:
        new_viewer(username, token, client_id, broadcaster_id)
    except Exception as e:
        logger.error(f"Error adding viewer {username}: {e}")


def enqueue_viewer(username, token, client_id, broadcaster_id):
    _viewer_executor.submit(new_viewer_wrapper, username, token, client_id, broadcaster_id)


def enqueue_status_update(viewer):
    _viewer_executor.submit(viewer.update_status)


def remove_viewer(username):
    username_lower = username.lower()
    with _viewers_lock:
        viewer_to_remove = next((v for v in viewers if v.username == username_lower), None)
        if viewer_to_remove:
            viewers.remove(viewer_to_remove)
            logger.debug(f"Removed viewer: {username}")
        else:
            logger.debug(f"{username} was not found in the viewers list.")


def get_broadcaster_id(token, client_id, username):
    logger.info(f"Getting broadcaster_id for {username}")
    token = token.replace("oauth:", "").strip()

    headers = {
        'Authorization': f'Bearer {token}',
        'Client-ID': client_id
    }

    response = requests.get(f'https://api.twitch.tv/helix/users?login={username}', headers=headers, timeout=10)
    try:
        user_data = response.json()
    except Exception as e:
        logger.warning(f"Failed to parse Twitch user response: {e}")
        return None

    if response.status_code == 200 and 'data' in user_data and user_data['data']:
        broadcaster_id = user_data['data'][0]['id']
        logger.info(f"Successfully retrieved broadcaster ID for {username}: {broadcaster_id}")
        return broadcaster_id
    else:
        logger.warning(f"Failed to retrieve broadcaster ID. Error: {user_data.get('message', 'Unknown error')}")
        return None
