import logging
import requests
import asyncio

viewers = []

class Viewer:
    def __init__(self, username, token, client_id, broadcaster_id):
        self.username = username
        self.user_id = self.get_user_id_from_username(token, client_id, username)
        self.following = self.check_if_follower(token, client_id, broadcaster_id)
        self.subscribed = self.check_if_subbed(token, client_id, broadcaster_id)
        logging.info(f"Initialized viewer: {self.username}")

    def check_if_follower(self, token, client_id, broadcaster_id):
        headers = {
            'Authorization': f'Bearer {token}',
            'Client-ID': client_id
        }
        try:
            # Get the user ID for the username
            viewer_id = self.user_id
            if viewer_id is None:
                logging.warning(f"Could not find user ID for {self.username}, cannot check follower status.")
                return False

            # Check if the user is a follower of the broadcaster
            follows_url = f'https://api.twitch.tv/helix/channels/followers?broadcaster_id={broadcaster_id}&user_id={viewer_id}'
            followers_response = requests.get(follows_url, headers=headers)

            followers_data = followers_response.json()

            # Check if we get a 401 Unauthorized error here
            if followers_response.status_code == 401:
                logging.error("Unauthorized access. Verify if the token has the user:read:follows scope.")
                return False

            # Parse the response
            followers_data = followers_response.json()

            logging.info(f"Followers_response: {followers_response}")

            # Check if the user is in the list of followers
            return 'data' in followers_data and len(followers_data['data']) > 0
        except Exception as e:
            logging.error(f"Error retrieving follower status for {self.username}: {e}")
            return False


    def check_if_subbed(self, token, client_id, broadcaster_id):
        headers = {
            'Authorization': f'Bearer {token}',
            'Client-ID': client_id
        }
        try:
            # Get the user ID for the username
            viewer_id = self.user_id
            if viewer_id is None:
                logging.warning(f"Could not find user ID for {self.username}, cannot check follower status.")
                return False

            # Check if the user is a subscriber
            subscriptions_response = requests.get(
                f'https://api.twitch.tv/helix/subscriptions/user?broadcaster_id={broadcaster_id}&user_id={viewer_id}',
                headers=headers
            )

            logging.info(f"Subscriptions_response: {subscriptions_response}")

            if subscriptions_response.status_code == 400:
                logging.error("Bad request")
                return False
            elif subscriptions_response.status_code == 401:
                logging.error("Unauthorized access. Verify if the token has the user:read:subscription scope.")
                return False
            elif subscriptions_response.status_code == 404:
                logging.info(f"{self.username} has no subscription.")
                return False
            elif subscriptions_response.status_code == 200:
                logging.info(f"{self.username} has a subscription.")
                return True

        except Exception as e:
            logging.error(f"Error retrieving subscription status for {self.username}: {e}")
            return False

    def get_user_id_from_username(self, token, client_id, username):
        headers = {
            'Authorization': f'Bearer {token}',
            'Client-ID': client_id
        }

        response = requests.get(
            f'https://api.twitch.tv/helix/users?login={username}',
            headers=headers
        )

        user_data = response.json()
        logging.debug(f"User data response for {username}: {user_data}")

        if response.status_code == 200 and 'data' in user_data and user_data['data']:
            user_id = user_data['data'][0]['id']
            logging.info(f"User ID for {username} is {user_id}")
            return user_id
        else:
            logging.warning(f"Could not find user {username}")
            return None


async def new_viewer(username, token, client_id, broadcaster_id):
    # Convert username to lower case for a case-insensitive comparison
    username_lower = username.lower()

    # Check for existing viewers in a case-insensitive manner
    if any(viewer.username.lower() == username_lower for viewer in viewers):
        logging.info(f"{username} already exists in the viewer list.")
        return  # Exit if the viewer already exists

    # If not found, create and add the new Viewer instance
    viewer = Viewer(username=username, token=token, client_id=client_id, broadcaster_id=broadcaster_id)
    viewers.append(viewer)  # Append only if it's a new viewer
    logging.info(f"Added viewer: {viewer.username}")
    logging.info(f"Updated list of viewers: {[viewer.username for viewer in viewers]}")


def new_viewer_wrapper(username, token, client_id, broadcaster_id):
    try:
        asyncio.run(new_viewer(username, token, client_id, broadcaster_id))
    except Exception as e:
        logging.error(f"Error handling message from {username}: {e}")


def remove_viewer(username):
    # Find and remove the viewer
    viewer_to_remove = next((viewer for viewer in viewers if viewer.username == username), None)

    if viewer_to_remove:
        viewers.remove(viewer_to_remove)  # Remove the viewer from the list
        del viewer_to_remove  # Delete the object
        logging.info(f"Removed viewer: {username}")
    else:
        logging.info(f"{username} was not found in the viewers list.")

    logging.info(f"Updated list of viewers: {[viewer.username for viewer in viewers]}")


def get_broadcaster_id(token, client_id, username):
    logging.info(f"Getting broadcaster_id for {username}")
    headers = {
        'Authorization': f'Bearer {token}',
        'Client-ID': client_id
    }
    response = requests.get(
        f'https://api.twitch.tv/helix/users?login={username}',
        headers=headers
    )
    user_data = response.json()
    logging.debug(f"Response from Twitch API for user '{username}': {user_data}")

    if response.status_code == 200 and 'data' in user_data and user_data['data']:
        broadcaster_id = user_data['data'][0]['id']
        logging.info(f"Successfully retrieved broadcaster ID for {username}: {broadcaster_id}")
        return broadcaster_id
    else:
        logging.warning(f"Could not retrieve broadcaster ID for {username} or insufficient permissions.")
        return None
