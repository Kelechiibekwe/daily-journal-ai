from flask import Blueprint, jsonify, request, send_from_directory
import os

import app.helpers.eleven_labs_helper as eleven

audio_bp = Blueprint('audio_bp', __name__)

@audio_bp.route('/v1/audios', methods=['POST','GET'])
def generate_audio():
    data = request.json or {}
    entry_text = data.get("entry_text", "")

    if not entry_text.strip():
        return jsonify({"error": "entry_text is required"}), 400
    
    audio_url = eleven.generate_eleven_labs_audio(entry_text)
    return jsonify({"audio": audio_url}), 200

@audio_bp.route('/audio/<filename>', methods=['GET'], endpoint='serve_audio')
def serve_audio(filename):
    # Build absolute path to the audio folder
    audio_folder = os.path.abspath(
        os.path.join(os.path.dirname(__file__), '..', 'data', 'audio-output')
    )
    
    # Ensure the directory exists
    if not os.path.exists(audio_folder):
        os.makedirs(audio_folder, exist_ok=True)
        
    try:
        # Ensure the requested file exists
        file_path = os.path.join(audio_folder, filename)
        if not os.path.exists(file_path):
            return jsonify({"error": f"File {filename} not found"}), 404
            
        # Serve the file from the directory
        return send_from_directory(
            audio_folder,
            filename,
            mimetype='audio/mpeg',
            as_attachment=False
        )
    except Exception as e:
        print(f"Error serving audio file: {str(e)}")
        return jsonify({"error": "Error serving audio file"}), 500