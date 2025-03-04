from flask import Blueprint, request, jsonify
from sqlalchemy import cast, Date, desc
from datetime import datetime

import app.helpers.prompt_helper as prompt
from app.models.models import Prompt

prompt_bp = Blueprint('prompt', __name__, url_prefix='/v1')

@prompt_bp.route('/prompts/<int:user_id>', methods=['GET'])
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

@prompt_bp.route('/writer-block-prompt', methods=['POST','GET'])
def generate_write_block_prompt():
    data = request.get_json()
    journal_text = data.get('content', '')
    
    if not journal_text.strip():
        return jsonify({'question': ''}), 400

    question = prompt.generate_writer_block_prompt(journal_text)
    return jsonify({'question': question})

