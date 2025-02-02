import smtplib, ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.helpers.openai_helper import generate_prompt_with_hybrid_memory, update_short_term_memory, get_short_term_memory 
import imaplib
from email.utils import make_msgid
import email
from email.header import decode_header
from app.models.models import db, Prompts, Responses, User_Prompt
import logging
import openai

from config import Config

logger = logging.getLogger()
embedding_model = "text-embedding-3-small"

def send_journal_email(user_id):
    # Get user email and generate a prompt
    sender_email = Config.EMAIL_ADDRESS
    receiver_email = Config.EMAIL_ADDRESS
    password = Config.EMAIL_PASSWORD

    # Use the last journal entry (or a default if none exists) as query_text
    last_response = db.session.query(Responses.response_text).filter_by(user_id=user_id).order_by(Responses.created_at.desc()).first()
    query_text = last_response[0] if last_response else "How was your day?"

    # Generate the journal prompt using hybrid memory
    prompt_text = generate_prompt_with_hybrid_memory(user_id, query_text)

    # Create the email message
    message = MIMEMultipart("alternative")
    message["Subject"] = "Your Daily Journal Prompt"
    message["From"] = sender_email
    message["To"] = receiver_email

    msg_id = make_msgid()  # Generate unique Message-ID
    message["Message-ID"] = msg_id

    html = f"""\
    <html>
      <body>
        <p>Hi,<br>
           It's time to journal! Here's your prompt for today:<br>
           "{prompt_text}"<br>
           Keep up the great habit!
        </p>
      </body>
    </html>
    """
    part = MIMEText(html, "html")
    message.attach(part)

    # Send the email
    context = ssl.create_default_context()
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
        server.login(sender_email, password)
        server.sendmail(sender_email, receiver_email, message.as_string())

    # Generate embedding for the email body using OpenAI API
    embedding = openai.embeddings.create(input=[prompt_text],
    model=embedding_model).data[0].embedding

    # Store the generated prompt in the database
    new_prompt = Prompts(user_id=user_id, prompt_text=prompt_text, embedding_vector=embedding)
    db.session.add(new_prompt)
    db.session.commit()

    # Store the User_Prompt with the Message-ID
    user_prompt = User_Prompt(user_id=user_id, prompt_id=new_prompt.prompt_id, message_id=msg_id)
    db.session.add(user_prompt)
    db.session.commit()

    # Update short-term memory with the new prompt
    update_short_term_memory(user_id, {"prompt": prompt_text, "message_id": msg_id})

    return msg_id


def check_for_reply(message_id):
    default_email = Config.EMAIL_ADDRESS
    password = Config.EMAIL_PASSWORD
    has_reply = False
    try:
            # Connect to the email server and login
            mail = imaplib.IMAP4_SSL("imap.gmail.com")
            mail.login(default_email, password)
            mail.select("inbox")

            # Search for emails with 'In-Reply-To' matching the original Message-ID
            status, messages = mail.search(None, f'HEADER In-Reply-To "{message_id}"')

            if status != "OK" or not messages[0]:
                logger.warning(f"No messages found with In-Reply-To: {message_id}")
                return

            for msg_id in messages[0].split():
                status, msg_data = mail.fetch(msg_id, "(RFC822)")

                if status != "OK":
                    logger.error(f"Failed to fetch email with msg_id: {msg_id}")
                    continue

                for response_part in msg_data:
                    if isinstance(response_part, tuple):
                        msg = email.message_from_bytes(response_part[1])
                        subject, encoding = decode_header(msg["Subject"])[0]

                        if isinstance(subject, bytes):
                            subject = subject.decode(encoding if encoding else "utf-8")

                        # Extract the body of the email
                        if msg.is_multipart():
                            body = None
                            for part in msg.walk():
                                if part.get_content_type() == "text/plain":
                                    body = part.get_payload(decode=True).decode()
                                elif part.get_content_type() == "text/html" and body is None:
                                    # Fallback to HTML if no plain text found
                                    body = part.get_payload(decode=True).decode()
                        else:
                            body = msg.get_payload(decode=True).decode()

                        # Log the email subject and body
                        logger.info(f"Subject: {subject}\nBody: {body}")

                        user_prompt = User_Prompt.query.filter_by(message_id=message_id).first()
                        if user_prompt and body:
                            has_reply = True
                            
                            is_content_safe = is_content_appropriate(body)

                            if not is_content_safe:
                                return has_reply

                            # Generate embedding for the email body using OpenAI API
                            embedding = openai.embeddings.create(input=[body],
                            model=embedding_model).data[0].embedding

                            # Save the response with the embedding
                            response = Responses(
                                user_id=user_prompt.user_id, 
                                prompt_id=user_prompt.prompt_id, 
                                response_text=body,
                                embedding_vector=embedding
                            )
                            db.session.add(response)
                            db.session.commit()
                            logger.info(f"Saved response for user_id: {user_prompt.user_id}, prompt_id: {user_prompt.prompt_id}")

                            # Update short-term memory with the response
                            update_short_term_memory(user_prompt.user_id, {"response": body, "message_id": message_id})
            return has_reply  
    except Exception as e:
        logger.error(f"Error checking for reply: {e}")
    finally:
        # Ensure the connection to the mail server is closed
        mail.logout()

def is_content_appropriate(content):
    """
    Check if the content is appropriate using OpenAI's Moderation API.
    Returns False if flagged as inappropriate, True otherwise.
    """
    response = openai.Moderation.create(input=content)
    return not response["results"][0]["flagged"]