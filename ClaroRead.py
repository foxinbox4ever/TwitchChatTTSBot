import requests

# Endpoint URL to request the OAuth token
token_url = "https://apijavaanalytics.claro.hr/2.0.0/oauth/token"

# Replace these with your actual client credentials from Claro
client_id = "your_client_id"
client_secret = "your_client_secret"

def get_claro_read_token():
    """
    Requests an OAuth token from the Claro Read API.
    Returns the token if successful, otherwise None.
    """
    # Define the payload and headers as per Claro's requirements
    payload = {
        'grant_type': 'client_credentials',  # Common grant type for server-to-server authentication
        'client_id': client_id,
        'client_secret': client_secret
    }

    headers = {
        'Content-Type': 'application/x-www-form-urlencoded'
    }

    try:
        # Make the POST request to retrieve the token
        response = requests.post(token_url, data=payload, headers=headers)
        response.raise_for_status()  # Raise an error if the request fails

        # Parse the token from the response JSON
        token = response.json().get('access_token')
        if token:
            print("Access Token retrieved successfully.")
            return token
        else:
            print("Access Token not found in response:", response.json())
            return None
    except requests.exceptions.RequestException as e:
        print(f"An error occurred while requesting the token: {e}")
        return None


def make_sample_request(token):
    """
    Makes a sample request to a Claro Read API endpoint using the OAuth token.
    Replace `sample_api_url` with the actual Claro Read API endpoint you want to access.
    """
    # Example Claro Read API endpoint (replace with actual endpoint you want to use)
    sample_api_url = "https://api.claroread.com/your_api_endpoint"

    headers = {
        'Authorization': f'Bearer {token}'
    }

    try:
        # Make the request to the API endpoint
        response = requests.get(sample_api_url, headers=headers)
        response.raise_for_status()  # Raise an error if the request fails

        # Process the response
        print("API Response:", response.json())
    except requests.exceptions.RequestException as e:
        print(f"An error occurred while making the API request: {e}")


# Main function to get token and make a sample request
if __name__ == "__main__":
    token = get_claro_read_token()
    if token:
        make_sample_request(token)
    else:
        print("Failed to retrieve the access token.")

