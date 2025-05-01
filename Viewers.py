import logging
import requests
import asyncio

viewers = []

class Viewer:
    def __init__(self, username, token, client_id, broadcaster_id):
        self.username = username.strip().lower()
        self.token = token
        self.client_id = client_id
        self.broadcaster_id = broadcaster_id
        self.user_id = self.get_user_id_from_username()
        self.following = self.check_if_follower()
        self.subscribed = self.check_if_subbed()


        logging.info(f"Initialized viewer: {self.username}")

    def get_headers(self):
        return {
            'Authorization': f'Bearer {self.token}',
            'Client-ID': self.client_id
        }

    def get_user_id_from_username(self):
        headers = self.get_headers()
        response = requests.get(
            f'https://api.twitch.tv/helix/users?login={self.username}',
            headers=headers
        )
        try:
            user_data = response.json()
        except Exception as e:
            logging.error(f"Error decoding Twitch response: {e}")
            return None

        logging.debug(f"User data response for {self.username}: {user_data}")

        if response.status_code == 200 and 'data' in user_data and user_data['data']:
            user_id = user_data['data'][0]['id']
            logging.info(f"User ID for {self.username} is {user_id}")
            return user_id
        else:
            message = user_data.get('message', 'No message')
            logging.warning(f"Could not find user {self.username}. Status: {response.status_code}, Message: {message}")
            return None

    def check_if_follower(self):
        logging.info(f"Checking if {self.username} is following")

        if not self.user_id:
            logging.error(f"User {self.username} has no ID")
            return False

        headers = self.get_headers()
        follows_url = f'https://api.twitch.tv/helix/channels/followers?broadcaster_id={self.broadcaster_id}&user_id={self.user_id}'
        response = requests.get(follows_url, headers=headers)

        logging.info(f"Follower API response: {response.status_code} - {response.text}")

        if response.status_code == 400:
            logging.error(f"Bad Request: {response.text}")
            return False

        elif response.status_code == 401:
            logging.error("Unauthorized access. Missing scope: user:read:follows")
            return False

        elif response.status_code == 200:
            data = response.json().get("data", [])
            if any(entry["broadcaster_id"] == self.broadcaster_id for entry in data):
                logging.info(f"{self.username} **is** following {self.broadcaster_id}")
                return True
            else:
                logging.info(f"{self.username} **is NOT** following {self.broadcaster_id}")
                return False

    def check_if_subbed(self):
        logging.info(f"Checking if {self.username} is subbed")

        if not self.user_id:
            logging.error(f"User {self.username} has no ID")
            return False

        headers = self.get_headers()
        subs_url = f"https://api.twitch.tv/helix/subscriptions/user?broadcaster_id={self.broadcaster_id}&user_id={self.user_id}"
        response = requests.get(subs_url, headers=headers)

        logging.info(f"Subscription API response: {response.status_code} - {response.text}")

        if response.status_code == 400:
            logging.error(f"Bad Request: {response.text}")
            return False

        elif response.status_code == 401:
            logging.error("Unauthorized access. Missing scope: user:read:subscriptions")
            return False

        elif response.status_code == 404:
            logging.info(f"User {self.username} **is NOT** subscribed to {self.broadcaster_id}")
            return False

        elif response.status_code == 200:
            logging.info(f"User {self.username} **is** subscribed to {self.broadcaster_id}")
            return True

        return False


async def new_viewer(username, token, client_id, broadcaster_id):
    username_lower = username.lower()

    if any(viewer.username == username_lower for viewer in viewers):
        logging.info(f"{username} already exists in the viewer list.")
        return

    viewer = Viewer(username=username, token=token, client_id=client_id, broadcaster_id=broadcaster_id)
    viewers.append(viewer)
    logging.info(f"Added viewer: {viewer.username}")
    logging.info(f"Updated list of viewers: {[v.username for v in viewers]}")


def new_viewer_wrapper(username, token, client_id, broadcaster_id):
    try:
        asyncio.run(new_viewer(username, token, client_id, broadcaster_id))
    except Exception as e:
        logging.error(f"Error handling message from {username}: {e}")


def remove_viewer(username):
    username_lower = username.lower()
    viewer_to_remove = next((v for v in viewers if v.username == username_lower), None)

    if viewer_to_remove:
        viewers.remove(viewer_to_remove)
        logging.info(f"Removed viewer: {username}")
    else:
        logging.info(f"{username} was not found in the viewers list.")

    logging.info(f"Updated list of viewers: {[v.username for v in viewers]}")


def get_broadcaster_id(token, client_id, username):
    logging.info(f"Getting broadcaster_id for {username}")
    token = token.replace("oauth:", "").strip()

    headers = {
        'Authorization': f'Bearer {token}',
        'Client-ID': client_id
    }

    response = requests.get(f'https://api.twitch.tv/helix/users?login={username}', headers=headers)
    try:
        user_data = response.json()
    except Exception as e:
        logging.warning(f"Failed to parse Twitch user response: {e}")
        return None

    if response.status_code == 200 and 'data' in user_data and user_data['data']:
        broadcaster_id = user_data['data'][0]['id']
        logging.info(f"Successfully retrieved broadcaster ID for {username}: {broadcaster_id}")
        return broadcaster_id
    else:
        logging.warning(f"Failed to retrieve broadcaster ID. Error: {user_data.get('message', 'Unknown error')}")
        return None
