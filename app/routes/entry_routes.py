from flask import Blueprint, request, jsonify
from sqlalchemy import desc

import app.helpers.journal_helper as journal
from app.models.models import Entry, db

entry_bp = Blueprint('entry', __name__, url_prefix='/v1/entries')

@entry_bp.route('', methods=['POST'])
def create_journal_entry():
    data = request.json
    user_id = data.get("user_id")
    entry_text = data.get("entry_text")
    prompt_id = data.get("prompt_id")
    
    if not user_id or not entry_text:
        return jsonify({"error": "user_id and entry_text are required"}), 400
    
    result = journal.create_entry(user_id, entry_text, prompt_id)
    return jsonify(result), 201 if "entry_id" in result else 500

@entry_bp.route('/<int:user_id>', methods=['GET'])
def get_journal_entries(user_id):
    entries = Entry.query.filter_by(user_id=user_id).order_by(desc(Entry.created_at)).all()
    entries_list = [entry.to_dict() for entry in entries]
    return jsonify(entries_list), 200

@entry_bp.route('/<int:user_id>/<int:entry_id>', methods=['PUT'])
def update_journal_entry(user_id, entry_id):
    data = request.json
    new_text = data.get("entry_text")
    if not new_text:
        return jsonify({"error": "entry_text is required"}), 400

    result = journal.update_entry(entry_id, user_id, new_text)
    return jsonify(result), 201 if "entry_id" in result else 500

@entry_bp.route('/<int:user_id>/<int:entry_id>', methods=['DELETE'])
def delete_journal_entry(user_id, entry_id):
    """
    Delete a journal entry by its ID for the specified user.
    """
    entry = Entry.query.filter_by(user_id=user_id, entry_id=entry_id).first()
    if not entry:
        return jsonify({"error": "Entry not found"}), 404

    try:
        db.session.delete(entry)
        db.session.commit()
        return jsonify({"message": "Entry deleted successfully"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500