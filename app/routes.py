from flask import Flask, jsonify, request, send_file
import app.helpers.journal_helper as journal
import app.helpers.prompt_helper as prompt
import app.helpers.notebooklm_helper as notebook
import requests
import time

from app.models.models import db, Prompt, Entry
def init_routes(app):
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
    
    @app.route('/v1/prompts/<int:user_id>', methods=['GET'])
    def send_prompt(user_id):       
        prompt_response = prompt.generate_prompt(user_id)
        return jsonify({
            "message": "Journal email sent",
            "prompt": prompt_response
        }), 201
    
    @app.route('/v1/podcast/<int:user_id>', methods=['GET'])
    def generate_podcast(user_id):
        """
        API endpoint that gathers all entries for the given user, uses them as
        context to generate a podcast via the AutoContent API, and returns the audio URL.
        """
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
            # Initiate content creation.
            create_response = notebook.create_content(request_data)
            request_id = create_response.get('request_id')
            if not request_id:
                return jsonify({"error": "Error initiating content creation.", "details": create_response}), 500

            print('Request initiated. Request ID:', request_id)

            # Poll the API for completion.
            status_data = notebook.poll_status(request_id)
            audio_url = status_data.get('audio_url')
            audio_title = status_data.get('audio_title')

            if not audio_url:
                return jsonify({"error": "Audio URL not returned.", "details": status_data}), 500

            save_path = f"/tmp/podcast_{user_id}_{int(time.time())}.mp3"
            download_audio(audio_url, save_path)

            return send_file(save_path, mimetype='audio/mpeg')

            # return jsonify({
            # "audio_url": audio_url,
            # "audio_title": audio_title
        # })

        except requests.HTTPError as http_err:
            return jsonify({"error": "HTTP error", "details": str(http_err)}), 500
        except Exception as err:
            return jsonify({"error": "An error occurred", "details": str(err)}), 500


def download_audio(audio_url, save_path):
    # Stream the download to handle large files
    response = requests.get(audio_url, stream=True)
    response.raise_for_status()
    with open(save_path, 'wb') as f:
        for chunk in response.iter_content(chunk_size=8192):
            if chunk:
                f.write(chunk)
    return save_path