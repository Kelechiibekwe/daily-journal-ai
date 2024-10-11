from flask import Flask, jsonify
from app.email_helper import send_journal_email, check_for_reply
from app.models.models import db, Prompts, Responses, User_Prompt
from twilio.twiml.voice_response import VoiceResponse


def init_routes(app):
    @app.route('/')
    def home():
        return "Welcome to my Flask app!"
    
    @app.route('/users/<int:user_id>/journals', methods=['POST'])
    def create_journal(user_id):       
        msg_id = send_journal_email(user_id)
        return jsonify({
            "message": "Journal email sent",
            "message_id": msg_id
        }), 201

    @app.route('/journals/<message_id>', methods=['GET'])
    def get_journal_reply(message_id):
        reply = check_for_reply(message_id)
        if reply:
            return jsonify({
                "message": f"Reply found for Message-ID: {message_id}",
                "reply_content": reply
            }), 200
        else:
            return jsonify({
                "message": f"No reply found for Message-ID: {message_id}"
            }), 404
    
    @app.route("/answer", methods=['GET', 'POST'])
    def answer_call():
        """Respond to incoming phone calls with a brief message."""
        # Start our TwiML response
        resp = VoiceResponse()

        # Read a message aloud to the caller
        resp.say("Thank you for calling! Have a great day.", voice='Polly.Amy')

        return str(resp)
