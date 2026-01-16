
import os
from flask import Flask, app, request, jsonify, Blueprint
from flask_cors import CORS
import requests

graph_bp = Blueprint("graph", __name__, url_prefix="/graph")

@graph_bp.route("/test/graph-token", methods=["GET"])
def test_graph_token():
    token = get_graph_token()
    return jsonify({
        "token_preview": token[:30] + "...",
        "length": len(token)
    })

@graph_bp.route("/test/graph-user", methods=["GET"])
def test_graph_user():
    token = get_graph_token()
    object_id = os.getenv("OBJECT_ID")

    headers = {"Authorization": f"Bearer {token}"}
    url = f"https://graph.microsoft.com/v1.0/users/{object_id}?$select=id,displayName,userPrincipalName,mail"

    r = requests.get(url, headers=headers)
    return (r.text, r.status_code, {"Content-Type": "application/json"})


@graph_bp.route("/test/graph-token-full", methods=["GET"])
def test_graph_token_full():
    return jsonify({"token": get_graph_token()})

@graph_bp.route("/test/create-event", methods=["POST"])
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
