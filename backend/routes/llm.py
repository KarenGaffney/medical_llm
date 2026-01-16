import os
import json
from datetime import date
from openai import AzureOpenAI
from flask import Blueprint, request, jsonify

llm_bp = Blueprint("llm", __name__, url_prefix="/llm")

SYSTEM_PROMPT_STATE = """
You are a cheery scheduling assistant for doctors.

You will be given:
1) The user's message
2) The current draft appointment state (may have missing fields)
3) Whether we are awaiting confirmation

Return ONLY valid JSON with this schema:
{
  "assistant_message": string,
  "updates": {
    "attendee_name": string | null,
    "start_time_local": string | null,  // format DD/MM/YYYY HH:MM:SS
    "duration_minutes": number | null,
    "title": string | null,
    "notes": string | null
  },
  "confirm_intent": "yes" | "no" | "unknown"
}

Rules:
- Use the draft state to avoid asking for info already provided.
- If the user provides new info (time, duration, attendee), include it under updates.
- If a required field is missing (attendee_name, start_time_local or duration_minutes), ask a concise question in assistant_message, and leave missing field null in updates.
- Once all required fields are filled, ask the user to confirm the appointment by setting the "assistant_message" to this EXACTLY:
  "Could you please confirm your appointment with [atendee_name] on [start_time_local] for [duration_minutes] minutes?"
- if the user replies affirmativley, set confirm_intent = "yes"
- If the user replies "no", "cancel", set confirm_intent="no". and ask a follow up question in assistant_message to clarify.
- For relative dates like "tomorrow", resolve using today's date: {TODAY_DATE}.
- Assume timezone America/Los_Angeles unless user says otherwise.
- JSON only. No markdown. No extra text.
"""

def call_azure_openai_state(user_message, draft_event, awaiting_confirmation):
    deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT")
    client = AzureOpenAI(
        api_version=os.getenv("API_VERSION"),
        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
        api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    )

    today = date.today().isoformat()
    system_prompt = SYSTEM_PROMPT_STATE.replace("{TODAY_DATE}", today)

    user_payload = {
        "user_message": user_message,
        "draft_event": draft_event,
        "awaiting_confirmation": awaiting_confirmation
    }
    model_message = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": json.dumps(user_payload)}
        ]
    print(model_message)
    response = client.chat.completions.create(
        model=deployment,
        messages=model_message,
        temperature=0.0,
        max_tokens=500
    )

    content = response.choices[0].message.content
    print("RAW LLM:", content, flush=True)
    return content
