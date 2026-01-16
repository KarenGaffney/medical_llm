from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import requests
import os
from openai import AzureOpenAI
import json
from datetime import datetime, timedelta, date



app = Flask(__name__)
CORS(app)

#### System Prompt
SYSTEM_PROMPT = """
        You are a cheery scheduling assistant for doctors.

        Return ONLY valid JSON with this exact schema:
        {
        "assistant_message": string,
        "intent": "create_calendar_event" | "none",
        "data": {
            "attendee_name": string | null,
            "start_time_local": string | null,  // local datetime DD/MM/YYYY HH:MM:SS 
            "duration_minutes": number | null,
            "title": string | null,
            "notes": string | null // or any notes the user provided,
            "confirmed": boolean // true if user confirms the appointment details, False if not yet confirmed
        },
        "missing_fields": string[]
        }

        Rules:
        - If the user asks to schedule, set intent=create_calendar_event.
            - If any required fields are missing (attendee_name, start_time_local), put them in missing_fields and set assistant_message to a polite question.
            - If all required fields are present, set an assistant_message with the appointment details (attendee_name, start_time_local, duration_minutes) and ask for confirmation.
            - If the user confirms the details, set data.confirmed to true, and reply "Great! I have booked your appointment with [atendee_name] at X am/pm on Month Day Year for [duration_minutes] minutes."
            - If the user does not confirm, set data.confirmed to false, and set assistant_message to a polite message asking for corrections.
            - If the user provides corrections, update the data fields accordingly, set confirmed to false, and ask for confirmation again.
        - Use prior messages in the conversation to fill missing_fields. Do not ask for information the user already provided earlier in the conversation
        - For relative dates like "tomorrow", resolve them using today's date: {TODAY_DATE}.
        - Assume timezone America/Los_Angeles unless user states otherwise.
        - No markdown, no explanations, JSON only!!!!
        - Return ONLY valid JSON with this exact above schema!!!
        """

###
### TEST FUNCTIONS
###
## Function to get graph token
@app.route("/test/graph-token", methods=["GET"])
def test_graph_token():
    token = get_graph_token()
    return jsonify({
        "token_preview": token[:30] + "...",
        "length": len(token)
    })

@app.route("/test/graph-user", methods=["GET"])
def test_graph_user():
    token = get_graph_token()
    object_id = os.getenv("OBJECT_ID")

    headers = {"Authorization": f"Bearer {token}"}
    url = f"https://graph.microsoft.com/v1.0/users/{object_id}?$select=id,displayName,userPrincipalName,mail"

    r = requests.get(url, headers=headers)
    return (r.text, r.status_code, {"Content-Type": "application/json"})


@app.route("/test/graph-token-full", methods=["GET"])
def test_graph_token_full():
    return jsonify({"token": get_graph_token()})

@app.route("/test/create-event", methods=["POST"])
def test_create_event():
    dummy_event = {
        "title": "Test Appointment",
        "attendee_name": "Test Patient",
        "attendee_email": "test.patient@email.com",
        "start_time": "2026-01-14T13:00:00",
        "end_time": "2026-01-14T13:30:00",
        "notes": "Created via test endpoint"
    }

    event = create_calendar_event(dummy_event)
    return jsonify(event)

#### 
#### MAIN FUNCTIONS
####
def get_graph_token():
    # print("TENANT_ID:", os.getenv("TENANT_ID"))
    # print("CLIENT_ID:", os.getenv("CLIENT_ID"))
    # print("CLIENT_SECRET exists:", bool(os.getenv("CLIENT_SECRET")))
    url = f"https://login.microsoftonline.com/{os.getenv('TENANT_ID')}/oauth2/v2.0/token"

    payload = {
        "client_id": os.getenv("CLIENT_ID"),
        "client_secret": os.getenv("CLIENT_SECRET"),
        "scope": "https://graph.microsoft.com/.default",
        "grant_type": "client_credentials"
    }

    response = requests.post(url, data=payload)
    response.raise_for_status()

    token = response.json()["access_token"]
    # print(token)
    return token


    return response.json()["access_token"]

## Endpoint to create calendar event
def create_calendar_event(event_data):
    token = get_graph_token()

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    event = {
        "subject": event_data["title"],
        "body": {
            "contentType": "HTML",
            "content": event_data.get("notes", "")
        },
        "start": {
            "dateTime": event_data["start_time"],
            "timeZone": "Pacific Standard Time"
        },
        "end": {
            "dateTime": event_data["end_time"],
            "timeZone": "Pacific Standard Time"
        },
        "attendees": [
            {
                "emailAddress": {
                    "address": event_data["attendee_email"],
                    "name": event_data["attendee_name"]
                },
                "type": "required"
            }
        ]
    }
    object_id = os.getenv("OBJECT_ID")
    #url = f"https://graph.microsoft.com/v1.0/users/{object_id}/events"
    url = f"https://graph.microsoft.com/v1.0/users/{object_id}/calendar/events"



    response = requests.post(url, headers=headers, json=event)
    response.raise_for_status()

    return response.json()

## Endpoint to handle AI requests
@app.route("/ai/ping", methods=["POST"])
def ai_ping():
    body = request.json or {}
    messages = body.get("messages", [])


    llm_text = call_azure_openai(messages)   
    parsed = json.loads(llm_text)

    # If missing info, just return the assistant message + missing fields
    if parsed.get("missing_fields"):
        return jsonify({
            "status": "needs_clarification",
            "assistant_message": parsed["assistant_message"],
            "parsed": parsed
        })

    if parsed.get("intent") == "create_calendar_event" and parsed["data"].get("confirmed") == True:
        event_data = build_event_payload(parsed)
        print("Event data built:", event_data)
        event = create_calendar_event(event_data)

        return jsonify({
            "status": "success",
            "assistant_message": parsed["assistant_message"],
            "event_id": event["id"],
            "event_data": event_data,
            "parsed": parsed
        })

    return jsonify({
        "status": "noop",
        "assistant_message": parsed.get("assistant_message", "I can help with scheduling."),
        "parsed": parsed
    })


## helper function to parse intent from ai response

def parse_llm_response(content: str):
    parsed = json.loads(content)
    return parsed

def build_event_payload(parsed):
    print("Building event payload from parsed:")
    data = parsed["data"]
    date_string = "14/09/2024 15:45:30"
    format_code = "%d/%m/%Y %H:%M:%S"
    start = datetime.strptime(data["start_time_local"], format_code) 
    duration = int(data.get("duration_minutes") or 30)
    end = start + timedelta(minutes=duration)
    #lookup_email = {'Shelly':'ksgafney@gmail.com'}
    payload = {
        "title": data.get("title") or "Patient appointment",
        "notes": data.get("notes") or "created via AI scheduling assistant",
        "attendee_name": data["attendee_name"],
        # you will look up attendee_email from your patient DB later
        "attendee_email": 'ksgafney@gmail.com',
        "start_time": start.strftime("%Y-%m-%dT%H:%M:%S"),
        "end_time": end.strftime("%Y-%m-%dT%H:%M:%S")
    }
    print(payload)
    return payload


def call_azure_openai(messages):

    deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT")

    client = AzureOpenAI(
    api_version=os.getenv("API_VERSION"),
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    )

    
    today = date.today().isoformat()
    #print(today)
    system_prompt = SYSTEM_PROMPT.replace("{TODAY_DATE}", today)
    #print(system_prompt)

    model_messages = [{"role": "system", "content": system_prompt}] + messages
    print("MODEL MESSAGES:", model_messages, flush=True)
    response = client.chat.completions.create(
        messages=model_messages,
        max_tokens=800,
        temperature=0.1,
        top_p=1.0,
        model=deployment
    )

    content = response.choices[0].message.content
    print("RAW LLM:", content, flush=True)
    return content


if __name__ == "__main__":
    print("🔥 LOADED THIS app.py FILE 🔥")
    app.run(host="0.0.0.0", port=5000, debug=True)
