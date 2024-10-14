from flask import request, send_file, url_for
import requests

from config import Config

VOICE_ID = 'cgSgspJ2msm6clMCkdW9' # Voice ID for Jessica

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
            "stability": 0.5,
            "similarity_boost": 0.75
        }
    }

    # Send a POST request to Eleven Labs API to generate the audio
    response = requests.post(
        f'https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}',
        headers=headers,
        json=data
    )

    # Save the audio content to a file
    audio_filename = 'app/eleven_labs_audio.mp3'
    with open(audio_filename, 'wb') as f:
        f.write(response.content)

    # Generate a URL for the audio file
    audio_url = request.url_root + url_for('serve_audio', filename=audio_filename)

    return audio_url