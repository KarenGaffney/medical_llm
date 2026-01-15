from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import requests
import os
from openai import AzureOpenAI
import json



app = Flask(__name__)
CORS(app)

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
    print("TENANT_ID:", os.getenv("TENANT_ID"))
    print("CLIENT_ID:", os.getenv("CLIENT_ID"))
    print("CLIENT_SECRET exists:", bool(os.getenv("CLIENT_SECRET")))
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
    print(token)
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
    user_input = request.json.get("message", "")

    ai_response = call_azure_openai(user_input)
    parsed = parse_llm_response(ai_response)

    if parsed["intent"] == "create_calendar_event":
        event = create_calendar_event(parsed["data"])
        return jsonify({
            "status": "success",
            "event_id": event["id"]
        })

    return jsonify({"status": "noop"})

## helper function to parse intent from ai response
def parse_llm_response(ai_response):
    try:
        content = ai_response.choices[0].message.content
        parsed = json.loads(content)

        # Minimal validation
        if "intent" not in parsed:
            raise ValueError("Missing intent")

        return parsed

    except json.JSONDecodeError:
        return {
            "intent": "none",
            "confidence": 0.0,
            "error": "Invalid JSON from LLM"
        }

    except Exception as e:
        return {
            "intent": "none",
            "confidence": 0.0,
            "error": str(e)
        }


def call_azure_openai(prompt):

    deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT")

    client = AzureOpenAI(
    api_version=os.getenv("API_VERSION"),
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    )

    response = client.chat.completions.create(
        messages=[
            {
                "role": "system",
                "content": """
                    You are an AI scheduling assistant for doctors.

                    Your job is to extract structured intent from user input.
                    You MUST respond with valid JSON only.
                    Do NOT include explanations or markdown.

                    Supported intents:
                    - create_calendar_event
                    - cancel_calendar_event
                    - list_events
                    - none

                    If required information is missing, include it in missing_fields.

                    DateTimes must be ISO-8601 (YYYY-MM-DDTHH:MM:SS).
                    Assume Pacific Time unless stated otherwise.
                    """,
            },
            {
                "role": "user",
                "content": prompt,
            }
        ],
        max_tokens=4096,
        temperature=1.0,
        top_p=1.0,
        model=deployment
    )

    print(response.choices[0].message.content)


    return response


if __name__ == "__main__":
    print("🔥 LOADED THIS app.py FILE 🔥")
    app.run(host="0.0.0.0", port=5000, debug=True)
