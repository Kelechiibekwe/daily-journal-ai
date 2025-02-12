from datetime import datetime, timedelta
from sqlalchemy import text
from openai import OpenAI

from app.models.models import db, Prompt, Entry

client = OpenAI()

chat_model = "gpt-4o-mini"
embedding_model = "text-embedding-3-small"

def generate_prompt(user_id):
    recent_entries = (db.session
                      .query(Entry.entry_text, Entry.created_at)
                      .filter_by(user_id=user_id)
                      .order_by(Entry.created_at.desc())
                      .limit(5) # Get the last 5 entries
                      .all())
    
    recent_entries = [{"entry_text": entry.entry_text, "created_at": entry.created_at} for entry in recent_entries]
    strategy = determine_prompt_strategy(recent_entries)
    prompt  = generate_prompt_for_user(user_id, strategy, recent_entries)
    prompt_embedding = client.embeddings.create(input=[prompt], model=embedding_model).data[0].embedding
    new_prompt = Prompt(
        user_id=user_id,
        prompt_text=prompt,
        embedding_vector = prompt_embedding
    )
    db.session.add(new_prompt)
    db.session.commit()

    return new_prompt

def determine_prompt_strategy(recent_entries):
    if len(recent_entries) == 0:
        return "fresh"
    
    introspection_score = analyze_introspection(recent_entries)
    # print(f'Introspection Score of recent entries is: {introspection_score}')

    time_since_last_entry = datetime.now() - recent_entries[-1]["created_at"]
    # print(f'time_since_last_entry of recent entries is: {time_since_last_entry}')
    inactive_threshold = timedelta(days=4)
    
    theme_consistency = calculate_theme_consistency(recent_entries)
    # print(f'theme_consistency of recent entries is: {theme_consistency}')
    
    if time_since_last_entry > inactive_threshold or introspection_score < 4:
        return "personalized"
    elif theme_consistency > 0.8:
        return "fresh"
    else:
        return "personalized"
    

def analyze_introspection(entries):
    """
    Analyze the introspectiveness of recent entries.
    Returns a score between 1 and 10.
    """

    entries_text = "\n".join(entry["entry_text"] for entry in entries)

    system_prompt = (
        "You are a journal analysis assistant. Your task is to evaluate the depth, "
        "introspection, and reflective quality of journal entries. Please focus solely "
        "on the introspective nature of the content."
    )
    
    user_prompt = (
        f"Analyze the following journal entries for introspection and depth:\n\n{entries_text}\n\n"
        "On a scale of 1-10, where 1 is not introspective at all and 10 is extremely introspective, "
        "rate how introspective these entries are. Respond with only a numerical score."
    )

    # Prepare the messages for the Chat Completion API
    messages = [
        {"role": "system", 
        "content":  system_prompt},
        {"role": "user", "content": user_prompt}
    ]


    response = client.chat.completions.create(model=chat_model, 
    messages=messages,
    max_tokens=50)

    result = response.choices[0].message.content.strip()
    try:
        # Try to convert the response to a float score.
        score = float(result)
        return score
    except ValueError:
        # If the response is not a simple number, you might log it and return a default value.
        print("Unexpected response for introspection score:", result)
        return 5.0
    

def calculate_theme_consistency(recent_entries):
    """
    Analyzes the consistency of themes in recent journal entries.
    Returns a consistency score between 0 (completely inconsistent) and 1 (highly consistent).
    """

    entries_text = "\n".join(entry["entry_text"] for entry in recent_entries)

    system_prompt = (
        "You are an AI trained to analyze the thematic consistency of journal entries. "
        "Your task is to determine how similar the themes are across multiple journal entries. "
        "Rate the consistency between 0 (completely different themes) and 1 (identical themes)."
    )

    user_prompt = (
        f"Analyze the following journal entries:\n\n{entries_text}\n\n"
        "On a scale of 0 to 1, where 0 means no thematic consistency and 1 means highly consistent themes, "
        "rate how consistent the themes are across these entries. Respond with only a numerical score."
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]

    response = client.chat.completions.create(
        model=chat_model,
        messages=messages,
        max_tokens=10
    )

    result = response.choices[0].message.content.strip()

    try:
        score = float(result)
        return score
    except ValueError:
        print("Unexpected response for theme consistency:", result)
        return 0.5 


def generate_prompt_for_user(user_id, strategy, recent_entries):
    if strategy == "fresh":
        return generate_fresh_prompt()
    elif strategy == "personalized":
        return generate_personalized_prompt(user_id, recent_entries)
    elif strategy == "hybrid":
        return generate_personalized_prompt(user_id, recent_entries)
    else:
        return generate_fresh_prompt()

def generate_fresh_prompt():
    system_prompt = (
        "You are a creative journaling assistant. Your role is to generate fresh and inspiring journaling prompts. "
        "Your prompts should encourage new ideas and creativity, without referring to the user's previous entries."
    )
    user_prompt = (
        "Generate a fresh, inspiring journaling prompt that invites the user to explore new thoughts or ideas. "
        "Do not reference any past journal entries. Respond with only the prompt text."
    )
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]
    response = client.chat.completions.create(
        model=chat_model,
        messages=messages,
        max_tokens=50,
        temperature=0.7
    )
    
    result = response.choices[0].message.content.strip()
    return result

def generate_personalized_prompt(user_id, recent_entries):

    entries_text = "".join(entry["entry_text"] for entry in recent_entries)
    relevant_past_entries = ""
    relevant_past_entries = get_relevant_long_term_entries(user_id, entries_text)

    if relevant_past_entries:
        relevant_past_entries = [f"Response: {entry['entry']}" for entry in relevant_past_entries]

    combined_context = "Here’s what you’ve shared recently:\n" + "".join(entries_text) + "\n\n"
    combined_context += "Based on your previous journal entries:\n" + "\n".join(relevant_past_entries)

    system_prompt = (
                        " You are an AI journaling assistant that specializes in creating concise,"
                        " personalized journal prompts. Use any provided context to generate a clear"
                        " and engaging prompt that encourages users to reflect on their personal growth "
                        " and daily experiences. Your output should be a single, brief statement or question"
                        " without additional commentary."
    )
    
        # (
        #         "You are a personalized journaling assistant. Your task is to generate a journaling prompt "
        #         "that is tailored to the user's long term experiences and recent reflections. "
        #         "Inspire deeper thought and forward-looking reflection."
    
    # print(f"Combined Context: {combined_context}")
    user_prompt = (
        f"Based on the following context, generate a concise personalized journaling prompt that encourages "
        f"the user to reflect their personal experience. Do not repeat information verbatim; "
        f"instead, synthesize the themes to inspire deeper reflection.\n\n{combined_context}\n\n"
        f"Respond with only the prompt text."
    )

    messages = [
        {"role": "system", "content":  system_prompt},
        {"role": "user", "content":user_prompt}
        ]

    prompt_response = client.chat.completions.create(model=chat_model, 
    messages=messages,
    max_tokens=100,
    temperature=0.7)

    return prompt_response.choices[0].message.content.strip()


def get_relevant_long_term_entries(user_id, query_text):
    query_embedding = client.embeddings.create(input=[query_text], model=embedding_model).data[0].embedding

    query_embedding_sql = "ARRAY[" + ",".join(map(str, query_embedding)) + "]"

    query = text(f"""
        WITH query AS (
            SELECT {query_embedding_sql}::vector(1536) AS query_embedding
        )
        SELECT 
            r.entry_text,
            (1 - (r.embedding_vector <-> query.query_embedding)) AS response_similarity
        FROM entry r, query
        WHERE r.user_id = :user_id
        ORDER BY response_similarity DESC
        LIMIT 3;
    """)

    results = db.session.execute(query, {'user_id': user_id}).fetchall()

    relevant_entries = [{"entry": row[0], "similarity": row[1]} for row in results]

    return relevant_entries

def generate_hybrid_prompt():
    pass