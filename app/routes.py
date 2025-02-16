from flask import Flask, jsonify, request, send_file
from flask import send_from_directory
from sqlalchemy import cast, Date
from datetime import datetime
from sqlalchemy import desc
from flask_cors import CORS
from io import BytesIO
import requests
import wave
import pytz
import os

from app.models.models import db, Prompt, Entry, Podcast
import app.helpers.notebooklm_helper as notebook
import app.helpers.eleven_labs_helper as eleven
import app.helpers.journal_helper as journal
import app.helpers.prompt_helper as prompt


def init_routes(app):
    CORS(app, resources={r"/*": {"origins": "http://localhost:3000"}})
    @app.route('/')
    def home():
        return "Welcome to StoryLine!"

    @app.route('/v1/entries', methods=['POST'])
    def create_journal_entry():
        data = request.json
        user_id = data.get("user_id")
        entry_text = data.get("entry_text")
        prompt_id = data.get("prompt_id")
        
        if not user_id or not entry_text:
            return jsonify({"error": "user_id and entry_text are required"}), 400
        
        result = journal.create_entry(user_id, entry_text, prompt_id)
        return jsonify(result), 201 if "entry_id" in result else 500
    
    @app.route('/v1/entries/<int:user_id>', methods=['GET'])
    def get_journal_entries(user_id):
        entries = Entry.query.filter_by(user_id=user_id)\
                             .order_by(desc(Entry.created_at))\
                             .all()
        
        entries_list = [entry.to_dict() for entry in entries]
        
        return jsonify(entries_list), 200
    
    @app.route('/v1/audios', methods=['POST','GET'])
    def generate_audio():
        data = request.json
        entry_text = data.get("entry_text")
        audio_url = eleven.generate_eleven_labs_audio(entry_text)
        
        return jsonify({"audio":audio_url}), 200
    
    @app.route('/audio/<filename>', methods=['GET'])
    def serve_audio(filename):
        # Create absolute path to the audio folder
        audio_folder = os.path.abspath(os.path.join(app.root_path, 'data', 'audio-output'))
        
        # Ensure the directory exists
        if not os.path.exists(audio_folder):
            os.makedirs(audio_folder, exist_ok=True)
            
        try:
            # Ensure the requested file exists
            file_path = os.path.join(audio_folder, filename)
            if not os.path.exists(file_path):
                return jsonify({"error": f"File {filename} not found"}), 404
                
            # Use send_from_directory with safe_join for security
            return send_from_directory(
                audio_folder,
                filename,
                mimetype='audio/mpeg',
                as_attachment=False
            )
            
        except Exception as e:
            print(f"Error serving audio file: {str(e)}")
            return jsonify({"error": "Error serving audio file"}), 500
    
    @app.route('/v1/prompts/<int:user_id>', methods=['GET'])
    def send_prompt(user_id):
        today = datetime.now().date()
        prompt_record = Prompt.query.filter(
            Prompt.user_id == user_id,
            cast(Prompt.created_at, Date) == today
        ).order_by(desc(Prompt.created_at)).first()
        
        if prompt_record:
            return jsonify({
                "message": "Prompt already generated for today.",
                "prompt": prompt_record.prompt_text,
                "prompt_id": prompt_record.prompt_id
            }), 200
        else:
            new_prompt = prompt.generate_prompt(user_id)
            return jsonify({
                "message": "New prompt generated for today.",
                "prompt": new_prompt.prompt_text,
                "prompt_id": new_prompt.prompt_id
            }), 201
        
    
    @app.route('/v1/writer-block-prompt', methods=['POST','GET'])
    def generate_write_block_prompt():
        data = request.get_json()
        journal_text = data.get('content', '')
        
        if not journal_text.strip():
            return jsonify({'question': ''}), 400

        question = prompt.generate_writer_block_prompt(journal_text)

        return jsonify({'question': question})
        
    
    @app.route('/v1/podcasts/<int:user_id>', methods=['POST'])
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

            print('Request initiated. Request ID:', request_id)

            status_data = notebook.poll_status(request_id)
            audio_url = status_data.get('audio_url')
            audio_title = status_data.get('audio_title')

            print(f'audio_url: {audio_url}; audio_title: {audio_title}')
            if not audio_url:
                return jsonify({"error": "Audio URL not returned.", "details": status_data}), 500

            duration = get_wav_duration(audio_url)

            new_podcast = Podcast(
                user_id=user_id,
                podcast_title = audio_title,
                podcast_url=audio_url,
                podcast_duration=duration,
                created_at = datetime.now()
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

    @app.route('/v1/podcasts/<int:user_id>', methods=['GET'])
    def get_podcasts(user_id):
        podcasts = Podcast.query.filter_by(user_id=user_id).order_by(desc(Podcast.created_at)).all()
        if not podcasts:
            return jsonify([{'id': 0,
            'userId': user_id,
            'title': 'No Stories Available',
            'audioUrl': 'Click “Generate Podcast!” to create your first story',
            'duration': 0,
            'createdAt': 'Click “Generate Podcast!” to create your first story'}]), 200
        
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