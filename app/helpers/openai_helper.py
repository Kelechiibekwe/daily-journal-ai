from openai import OpenAI
from sqlalchemy import text

client = OpenAI()
from config import Config
from app.models.models import db, Prompt, Responses, User_Prompt
import time
import numpy as np
import json

# Set embedding model and chat model
embedding_model = "text-embedding-3-small"
chat_model = "gpt-4o-mini"

# In-memory short-term buffer (could also use Redis for this)
short_term_memory = {}

def update_short_term_memory(user_id, new_message):
    """
    Stores the user's short-term memory in memory (instead of Redis).
    Keeps the last 5 messages for each user.
    """
    # Ensure there's an entry for the user in the dictionary
    if user_id not in short_term_memory:
        short_term_memory[user_id] = []

    # Add the new message to the beginning of the list
    short_term_memory[user_id].insert(0, new_message)

    # Keep only the last 5 messages
    if len(short_term_memory[user_id]) > 5:
        short_term_memory[user_id] = short_term_memory[user_id][:5]

def get_short_term_memory(user_id):
    """
    Retrieves the user's short-term memory from the in-memory dictionary.
    """
    return short_term_memory.get(user_id, [])  # Return an empty list if the user doesn't exist

# Function to store journal entry as embedding
def store_journal_embedding(user_id, journal_entry):
    # Generate embedding using OpenAI's embeddings API
    embedding = client.embeddings.create(input=[journal_entry], model=embedding_model).data[0].embedding

    # Store the embedding and journal entry in the database
    new_prompt = Prompts(user_id=user_id, prompt_text=journal_entry, embedding_vector=embedding)
    db.session.add(new_prompt)
    db.session.commit()


def get_relevant_long_term_entries(user_id, query_text):
    # Generate embedding for the query
    query_embedding = client.embeddings.create(input=[query_text], model=embedding_model).data[0].embedding

    # Convert the query embedding into a PostgreSQL array format for SQL query
    query_embedding_sql = "ARRAY[" + ",".join(map(str, query_embedding)) + "]"

    # Define the SQL query to calculate cosine similarity using pgvector
    query = text(f"""
        WITH query AS (
            SELECT {query_embedding_sql}::vector(1536) AS query_embedding
        )
        SELECT 
            r.response_text,
            (1 - (r.embedding_vector <-> query.query_embedding)) AS response_similarity
        FROM responses r, query
        WHERE r.user_id = :user_id
        ORDER BY response_similarity DESC
        LIMIT 3;
    """)

    # Execute the query
    results = db.session.execute(query, {'user_id': user_id}).fetchall()

    # Format the results as needed
    # relevant_entries = [{"prompt": row[0], "response": row[1], "similarity": row[4]} for row in results]
    relevant_entries = [{"response": row[0], "similarity": row[1]} for row in results]

    return relevant_entries

def generate_prompt_with_hybrid_memory(user_id, query_text):
    # Fetch recent messages from short-term memory
    recent_context = get_short_term_memory(user_id)

    # Check if recent context or past entries are empty and provide a fallback
    if not recent_context:
        recent_context = ["(No recent context available)"]

    else:
        recent_context = [f"Prompt: {entry['prompt']}\nResponse: {entry['response']}" for entry in recent_context]

    # Fetch relevant past entries from long-term memory
    relevant_past_entries = get_relevant_long_term_entries(user_id, query_text)

    if not relevant_past_entries:
        relevant_past_entries = ["(No relevant past entries found)"]
    else:
        # Convert relevant past entries (which may be a list of dicts) to strings
        relevant_past_entries = [f"Response: {entry['response']}" for entry in relevant_past_entries]

    # Combine the recent context and relevant past entries
    combined_context = "Here’s what you’ve shared recently:\n" + "\n".join(recent_context) + "\n\n"
    combined_context += "Based on your previous journal entries:\n" + "\n".join(relevant_past_entries)

    # If both are empty, add a default message
    if combined_context.strip() == "":
        combined_context = "There is no previous context or entries available. You can start journaling now!"

    prompt = (
    "You are a journaling assistant that helps users generate light hearted personalized journal prompts. "
    "You should use the previous entries as context to make the journal prompt more personalized. "
    "You can sometimes generate journal prompts not solely based on previous entries. When there "
    "are no previous entries or you are unsure, use any of the sample prompts below as inspiration "
    "to generate a prompt. Just say the prompt, no need for any intro."
    "Example of sample prompts to generate when you have no context or you want to generate a prompt without using previous entries: "
    "1. What small thing could you do today to live more mindfully? "
    "2. Describe a goal that once seemed unreachable, but you've since achieved. "
    "3. Reflect on a quote that fills you with optimism. "
    "4. What are some recurring thoughts you grapple with? "
    "5. How do you maintain a positive outlook during tough times? "
    "6. How do you spread positivity to others? "
    "7. Reflect on a skill you worked hard to master."
    )

    # Prepare the messages for the Chat Completion API
    messages = [
        {"role": "system", 
            "content":  prompt},
        {"role": "user", "content": f"Here’s my context:\n{combined_context}\nPlease generate a new personalized journal prompt for me."}
    ]


    # Call OpenAI to generate the journal prompt based on combined context
    prompt_response = client.chat.completions.create(model=chat_model, 
    messages=messages,
    max_tokens=150)

    return prompt_response.choices[0].message.content.strip()
