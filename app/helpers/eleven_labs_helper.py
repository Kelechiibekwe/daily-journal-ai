from flask import request, url_for
from datetime import datetime
import requests
import os

from config import Config

VOICE_ID_GEORGE = 'JBFqnCBsd6RMkjVDRZzb'
VOICE_ID_BRIAN = 'nPczCjzI2devNBz1zQrb'
VOICE_ID = 'JBFqnCBsd6RMkjVDRZzb' # Voice ID for Brian

def generate_eleven_labs_audio(text):
    """Generates speech audio from text using Eleven Labs API and returns the URL to the audio file."""
    headers = {
        'Accept': 'audio/mpeg',
        'Content-Type': 'application/json',
        'xi-api-key': Config.ELEVEN_LABS_API_KEY,
    }

    data = {
        "text": text,
        "voice_settings": {
            "stability": 0.3,
            "similarity_boost": 0.75
        }
    }

    response = requests.post(
        f'https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}',
        headers=headers,
        json=data
    )

    date = datetime.now()
    formatted_date = date.strftime('%Y-%m-%d_%H-%M-%S')
    audio_filename = f'app/data/audio-output/eleven_labs_audio_{formatted_date}.mp3'
    with open(audio_filename, 'wb') as f:
        f.write(response.content)

    filename_only = os.path.basename(audio_filename)
    audio_url = request.url_root.rstrip('/') + url_for('audio_bp.serve_audio', filename=filename_only)

    return audio_url
