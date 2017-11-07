import requests
import getpass


GSC_API_URL = "http://sbs:8100/"

request_handle = requests.Session()

headers = {
    'Content-Type': 'application/json',
    'Accept': 'application/json'}

create_session_url = os.path.join(GSC_API_URL, 'session')
auth_json = {
    'username': input(),
    'password': getpass.getpass()}

response = request_handle.post(create_session_url, json=auth_json, headers=headers)

if response.status_code == 200:
    # Add the authentication token to the headers.
    token = response.json().get('token')
    headers.update({'X-Token': token})
else:
    raise Exception('unable to authenticate GSC API')


