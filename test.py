import requests
from requests.auth import HTTPBasicAuth

# Set your Traccar server and user credentials
url = "https://app.uzradyab.ir/api/session/token"
username = "*"  # email or phone
password = "*"
expiration = "*"  # Set expiration time


# Send the POST request to generate the token
response = requests.post(
    url,
    auth=HTTPBasicAuth(username, password),  # Basic Auth with username and password
    data={'expiration': expiration}  # Set expiration time
)

# Print the response status code for debugging
print(f"Response Status Code: {response.status_code}")

# If the status code is 200, try to parse JSON
if response.status_code == 200:
    try:
        data = response.json()
        token = data.get('token')  # Assuming the token is in the response JSON
        if token:
            print(f"Generated token: {token}")
        else:
            print("Token not found in response.")
    except requests.exceptions.JSONDecodeError:
        print("Response is not valid JSON.")
else:
    print(f"Error: {response.status_code}, {response.text}")
