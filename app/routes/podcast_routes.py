from flask import Blueprint, jsonify
from datetime import datetime
from sqlalchemy import desc
from io import BytesIO
import requests, wave

from app.models.models import Podcast, Entry, db
import app.helpers.notebooklm_helper as notebook

podcast_bp = Blueprint('podcast', __name__, url_prefix='/v1/podcasts')

@podcast_bp.route('/<int:user_id>', methods=['POST'])
def generate_podcast(user_id):
    entries = Entry.query.filter_by(user_id=user_id).all()
    if not entries:
        return jsonify({"error": "No entries found for this user."}), 404

    combined_text = "\n".join([entry.entry_text for entry in entries if entry.entry_text])
    if not combined_text.strip():
        return jsonify({"error": "User entries do not contain any text."}), 400

    request_data = {
        "resources": [
            {"content": combined_text, "type": "text"}
        ],
        "text": "Generate a podcast narration based on the user's journal entries. The narration should be inspiring, reflective, and insightful.",
        "outputType": "audio"
    }

    try:
        create_response = notebook.create_content(request_data)
        request_id = create_response.get('request_id')
        if not request_id:
            return jsonify({"error": "Error initiating content creation.", "details": create_response}), 500

        status_data = notebook.poll_status(request_id)
        audio_url = status_data.get('audio_url')
        audio_title = status_data.get('audio_title')

        if not audio_url:
            return jsonify({"error": "Audio URL not returned.", "details": status_data}), 500

        duration = get_wav_duration(audio_url)

        new_podcast = Podcast(
            user_id=user_id,
            podcast_title=audio_title,
            podcast_url=audio_url,
            podcast_duration=duration,
            created_at=datetime.now()
        )

        db.session.add(new_podcast)
        db.session.commit()

        return jsonify({
            "audio_url": audio_url,
            "audio_title": audio_title
        })

    except requests.HTTPError as http_err:
        return jsonify({"error": "HTTP error", "details": str(http_err)}), 500
    except Exception as err:
        return jsonify({"error": "An error occurred", "details": str(err)}), 500

@podcast_bp.route('/<int:user_id>', methods=['GET'])
def get_podcasts(user_id):
    podcasts = Podcast.query.filter_by(user_id=user_id).order_by(desc(Podcast.created_at)).all()
    if not podcasts:
        return jsonify([{
            'id': 0,
            'userId': user_id,
            'title': 'No Stories Available',
            'audioUrl': 'Click “Generate Podcast!” to create your first story',
            'duration': 0,
            'createdAt': 'Click “Generate Podcast!” to create your first story'
        }]), 200

    podcasts_list = [podcast.to_dict() for podcast in podcasts]
    return jsonify(podcasts_list), 200

def get_wav_duration(url):
    response = requests.get(url)
    response.raise_for_status()
    file_bytes = BytesIO(response.content)
    with wave.open(file_bytes, 'rb') as wav_file:
        frames = wav_file.getnframes()
        rate = wav_file.getframerate()
        duration = frames / float(rate)
    return duration