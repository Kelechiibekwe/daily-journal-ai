from flask import request, url_for
from app.models.models import db, Prompts
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
    audio_filename = 'data/audio-output/eleven_labs_audio.mp3'
    with open(audio_filename, 'wb') as f:
        f.write(response.content)

    # Generate a URL for the audio file
    audio_url = request.url_root + url_for('serve_audio', filename=audio_filename)

    return audio_url

def get_user_by_phone_number(phone_number):

    user = 1
    # # Remove any non-digit characters and standardize format
    # clean_number = ''.join(filter(str.isdigit, phone_number))
    
    # # Try different formats: full number, last 10 digits
    # user = (
    #     User.query.filter(
    #         (User.phone_number == phone_number) | 
    #         (User.phone_number.endswith(clean_number[-10:]))
    #     ).first()
    # )
    
    return user

def get_latest_user_prompt(user_id):

    latest_prompt = (
        Prompts.query.filter_by(user_id=user_id)
        .order_by(Prompts.created_at.desc())
        .first()
    )
    
    return latest_prompt.text if latest_prompt else "No recent prompts found."