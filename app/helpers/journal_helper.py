from datetime import datetime
from openai import OpenAI

from app.models.models import db, Entry

client = OpenAI()
embedding_model = "text-embedding-3-small"
chat_model = "gpt-4o-mini"

def create_entry(user_id, entry_text, prompt_id):
    """
    Saves a journal entry to the database.
    """

    embedding = client.embeddings.create(input=[entry_text], model=embedding_model).data[0].embedding
    theme = extract_theme(entry_text)

    new_entry = Entry(
        user_id=user_id,
        entry_text=entry_text,
        prompt_id = prompt_id,
        theme=theme,
        embedding_vector=embedding,
        created_at = datetime.now()
    )

    try:
        db.session.add(new_entry)
        db.session.commit()
        return {"message": "Entry saved successfully", "entry_id": new_entry.entry_id}
    except Exception as e:
        db.session.rollback()
        return {"error": f"Database error: {str(e)}"}, 50
    

def update_entry(entry_id, user_id, new_text):
    entry = Entry.query.filter_by(id=entry_id, user_id=user_id).first()

    if not entry:
        return {"error": "Journal entry not found"}, 404

    entry.entry_text = new_text
    entry.updated_at = datetime.now()
    try:
        db.session.commit()
        return {"message": "Entry updated successfully", "entry_id": entry_id}
    except Exception as e:
        db.session.rollback()
        return {"error": f"Database error: {str(e)}"}, 50
    
def extract_theme(entry_text):
    system_prompt = (
        "You are an AI that extracts a single-word theme"
        "from a journal entry. Only respond with a single word."
    )
    
    user_prompt = (
        f"Journal Entry: {entry_text}\nExtract the main theme in one word."
    )

    # Prepare the messages for the Chat Completion API
    messages = [
        {"role": "system", 
        "content":  system_prompt},
        {"role": "user", "content": user_prompt}
    ]


    theme = client.chat.completions.create(model=chat_model, 
    messages=messages,
    temperature=0.3,
    max_tokens=50)

    return theme.choices[0].message.content.strip()

