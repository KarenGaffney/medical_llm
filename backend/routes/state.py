
import threading
from flask import request, jsonify


SESSION_STORE = {}
SESSION_LOCK = threading.Lock()

def get_state(session_id: str):
    with SESSION_LOCK:
        if session_id not in SESSION_STORE:
            SESSION_STORE[session_id] = {
                "draft_event": {
                    "attendee_name": None,
                    "start_time_local": None,
                    "duration_minutes": 30,
                    "title": "Patient appointment",
                    "notes": None
                },
                "awaiting_confirmation": False,
                "mode": "schedule",          # "schedule" | "add_patient"
                "pending_patient": {
                    "name": None,
                    "email": None,
                    "phone": None,
                    "dob": None
                }
                }

        return SESSION_STORE[session_id]
