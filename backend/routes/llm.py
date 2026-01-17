import os
import json
from datetime import date
from openai import AzureOpenAI
from flask import request, jsonify


SYSTEM_PROMPT_SCHEDULE = """
You are a assistant helping a doctor add a patient to a directory. Follow these rules exactly.

You will be given:
1) The user's message
3) The user's intent
2) The current draft state (may have missing fields)
3) Whether we are awaiting confirmation

Return ONLY valid JSON with this schema:
{
  "assistant_message": string,
  "updates": {
    "attendee_name": string | null,
    "start_time_local": string | null,  // format DD/MM/YYYY HH:MM:SS
    "duration_minutes": number | null,
    "title": string | null,
    "notes": string | null,
    "intent": string | null
  },
  "confirm_intent": "yes" | "no" | "unknown"
}

Rules: 
- Use the draft state to avoid asking for info already provided. DO NOT ASK FOR INFO ALREADY IN THE DRAFT. 
- DO NOT ASK FOR LAST NAMES
- If the user provides new info (time, duration, attendee), include it under updates.
- If the user changes their intent from scheduling an appointment to one of the following: "add_patient", "change_appointment", "cancel_appointment", set updates.intent accordingly.
- If a required field is missing (attendee_name, start_time_local or duration_minutes), ask a concise question in assistant_message, and leave missing field null in updates.
- Once all required fields are filled, ask the user to confirm the appointment by setting the "assistant_message" to this EXACTLY:
  "Could you please confirm your appointment with [atendee_name] on [start_time_local] for [duration_minutes] minutes?"
- if the user replies affirmativley, set confirm_intent = "yes". examples of affirmative replies: "yes", "confirm", "go ahead", "book it".
- If the user replies "no", "cancel", set confirm_intent="no". and ask a follow up question in assistant_message to clarify.
- For relative dates like "tomorrow", resolve using today's date: {TODAY_DATE}.
- Assume timezone America/Los_Angeles unless user says otherwise.
- JSON only. No markdown. No extra text.
"""

SYSTEM_PROMPT_ADD_PATIENT = """
You are a assistant helping a doctor add a patient to a directory. Follow these rules exactly.

Return ONLY valid JSON with this schema:
{
  "assistant_message": string,
  "updates": {
    "name": string | null,
    "email": string | null,
    "phone": string | null,
    "dob": string | null  // YYYY-MM-DD,
    "intent": string | null
  },
  "confirm_intent": "yes" | "no" | "unknown"
}

Rules:

- Use the pending_patient to avoid asking for info already provided. DO NOT ASK FOR INFO ALREADY IN THE DRAFT. 
- If the user changes their intent from adding a patient to one of the following: "schedule", "change", "cancel", set updates.intent accordingly.
- If the user provides new info (name, email, phone, dob), include it under updates.
- format date of birth from user input if provided, to YYYY-MM-DD and update under updates.
- format phone numbers to only digits, e.g. (123) 456-7890 -> 1234567890 and update under updates.
- If a required field is missing (name, email), ask a concise question in assistant_message, and leave missing field null in updates.
- Once all required fields are filled, ask the user to confirm the appointment by setting the "assistant_message" to this EXACTLY:
  "Could you please confirm you want to add [name] with email [email] to your patient directory?"
- if the user replies "yes", set confirm_intent = "yes" examples of acceptable replies: "yes", "confirm", "go ahead".
- If the user replies "no", "cancel", set confirm_intent="no". and ask a follow up question in assistant_message to clarify.
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
    system_prompt = SYSTEM_PROMPT_SCHEDULE.replace("{TODAY_DATE}", today)

    user_payload = {
        "user_message": user_message,
        "draft_event": draft_event,
        "awaiting_confirmation": awaiting_confirmation
    }
    model_message = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": json.dumps(user_payload)}
        ]
    
    response = client.chat.completions.create(
        model=deployment,
        messages=model_message,
        temperature=0.1,
        max_tokens=500
    )

    content = response.choices[0].message.content
    #print(system_prompt, flush=True)
    print('draft event', draft_event, flush=True)
    print('awaiting conf', awaiting_confirmation, flush=True)
    print("RAW LLM:", content, flush=True)
    return content

def call_azure_openai_add_patient(user_message, pending_patient, awaiting_confirmation):
    deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT")
    client = AzureOpenAI(
        api_version=os.getenv("API_VERSION"),
        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
        api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    )

    system_prompt = SYSTEM_PROMPT_ADD_PATIENT

    user_payload = {
        "user_message": user_message,
        "pending_patient": pending_patient,
        "awaiting_confirmation": awaiting_confirmation
    }
    print('pending_patient:', pending_patient, flush=True)
    print('awaiting_confirmation:', awaiting_confirmation, flush=True)
    model_message = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": json.dumps(user_payload)}
        ]
    
    response = client.chat.completions.create(
        model=deployment,
        messages=model_message,
        temperature=0.1,
        max_tokens=500
    )

    content = response.choices[0].message.content
    print(pending_patient, flush=True)
    print(awaiting_confirmation, flush=True)
    print("RAW LLM:", content, flush=True)
    return content
