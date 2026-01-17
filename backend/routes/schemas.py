import json
from datetime import datetime, timedelta
from flask import request, jsonify
from routes.db import lookup_patient_email


def parse_llm_response(content: str):
    parsed = json.loads(content)
    return parsed


def build_event_payload_from_state(draft):
    fmt = "%d/%m/%Y %H:%M:%S"
    start = datetime.strptime(draft["start_time_local"], fmt)
    duration = int(draft.get("duration_minutes") or 30)
    end = start + timedelta(minutes=duration)

    email = lookup_patient_email(draft["attendee_name"])
    if not email:
        raise ValueError(f"Patient not found: {draft['attendee_name']}")

    return {
        "title": draft.get("title") or "Patient appointment",
        "notes": draft.get("notes") or "",
        "attendee_name": draft["attendee_name"],
        "attendee_email": email,
        "start_time": start.strftime("%Y-%m-%dT%H:%M:%S"),
        "end_time": end.strftime("%Y-%m-%dT%H:%M:%S")
    }
