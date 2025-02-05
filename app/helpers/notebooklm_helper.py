import time
import requests

from config import Config

TOKEN = Config.NOTEBOOKLM_API_KEY
CREATE_URL = 'https://api.autocontentapi.com/Content/Create'
STATUS_BASE_URL = 'https://api.autocontentapi.com/content/status/'
POLL_INTERVAL = 5 

def create_content(request_data):
    headers = {
        'Authorization': f'Bearer {TOKEN}',
        'Content-Type': 'application/json',
        'accept': 'text/plain'
    }
    response = requests.post(CREATE_URL, json=request_data, headers=headers)
    response.raise_for_status()
    return response.json()

def poll_status(request_id):
    headers = {
        'Authorization': f'Bearer {TOKEN}',
        'Content-Type': 'application/json',
        'accept': 'application/json'
    }
    url = f'{STATUS_BASE_URL}{request_id}'
    while True:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        status = data.get('status')
        error_message = data.get('error_message')
        if error_message:
            raise Exception(f"Error from content API: {error_message}")
        if status == 100:
            print(f'Polling completed')
            return data 
        print(f'Current status: {status}. Waiting for completion...')
        time.sleep(POLL_INTERVAL)
    