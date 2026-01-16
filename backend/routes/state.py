
import threading
from flask import Blueprint, request, jsonify

state_bp = Blueprint("state", __name__, url_prefix="/state")

SESSION_STORE = {}
SESSION_LOCK = threading.Lock()

def get_state(session_id: str):
    with SESSION_LOCK:
        if session_id not in SESSION_STORE:
            SESSION_STORE[session_id] = {
                "draft_event": {
                    "attendee_name": None,
                    "start_time_local": None,  # "DD/MM/YYYY HH:MM:SS"
                    "duration_minutes": None,
                    "title": "Patient appointment",
                    "notes": ""
                },
                "awaiting_confirmation": False,
                "last_event_id": None
            }
        return SESSION_STORE[session_id]
