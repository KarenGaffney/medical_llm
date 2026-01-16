import json
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify

schema_bp = Blueprint("schema", __name__, url_prefix="/schema")

def parse_llm_response(content: str):
    parsed = json.loads(content)
    return parsed


def build_event_payload_from_state(draft):
    fmt = "%d/%m/%Y %H:%M:%S"
    start = datetime.strptime(draft["start_time_local"], fmt)
    duration = int(draft.get("duration_minutes") or 30)
    end = start + timedelta(minutes=duration)

    lookup_email = {"Shelly": "ksgafney@gmail.com"}  # replace later

    return {
        "title": draft.get("title") or "Patient appointment",
        "notes": draft.get("notes") or "",
        "attendee_name": draft["attendee_name"],
        "attendee_email": lookup_email.get(draft["attendee_name"], "unknown@example.com"),
        "start_time": start.strftime("%Y-%m-%dT%H:%M:%S"),
        "end_time": end.strftime("%Y-%m-%dT%H:%M:%S")
    }
