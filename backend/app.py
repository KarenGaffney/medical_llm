from flask import Flask, request, jsonify
from flask_cors import CORS
import os
from openai import AzureOpenAI
import json
from datetime import datetime, timedelta, date
import uuid
import threading
from routes.state import get_state, state_bp
from routes.llm import call_azure_openai_state, llm_bp
from routes.schemas import build_event_payload_from_state, parse_llm_response, schema_bp
from routes.graph import create_calendar_event, graph_bp



app = Flask(__name__)
CORS(app)

app.register_blueprint(graph_bp)
app.register_blueprint(state_bp)
app.register_blueprint(schema_bp)
app.register_blueprint(llm_bp)

###
### TEST FUNCTIONS
###
## Function to get graph token
## Endpoint to handle AI requests
@app.route("/ai/ping", methods=["POST"])
def ai_ping():
    body = request.json or {}
    session_id = body.get("session_id")
    user_msg = (body.get("message") or "").strip()

    if not session_id:
        return jsonify({"status": "error", "assistant_message": "Missing session_id"}), 400
    if not user_msg:
        return jsonify({"status": "error", "assistant_message": "Please enter a message."}), 400

    state = get_state(session_id)

    # Ask LLM for updates to the draft + confirmation detection
    llm_text = call_azure_openai_state(user_msg, state["draft_event"], state["awaiting_confirmation"])

    # Safe parse (never crash)
    try:
        parsed = json.loads(llm_text)
    except json.JSONDecodeError:
        return jsonify({
            "status": "needs_clarification",
            "assistant_message": llm_text,
            "debug": {"raw": llm_text}
        }), 200

    updates = parsed.get("updates") or {}
    confirm_intent = (parsed.get("confirm_intent") or "unknown").lower()

    # Apply updates into draft_event
    for k, v in updates.items():
        if k in state["draft_event"] and v is not None:
            state["draft_event"][k] = v


    missing = []
    if not state["draft_event"]["attendee_name"]:
        missing.append("attendee_name")
    if not state["draft_event"]["start_time_local"]:
        missing.append("start_time_local")

    # If missing info, ask follow-up and keep awaiting_confirmation False
    if missing:
        state["awaiting_confirmation"] = False
        return jsonify({
            "status": "needs_clarification",
            "assistant_message": parsed.get("assistant_message") or f"Missing: {', '.join(missing)}",
            "state": {"draft_event": state["draft_event"], "missing_fields": missing}
        }), 200

    # If we have enough info, prompt for confirmation unless already awaiting it
    if not state["awaiting_confirmation"] and confirm_intent != "yes":
        state["awaiting_confirmation"] = True
        d = state["draft_event"]
        return jsonify({
            "status": "awaiting_confirmation",
            "assistant_message": parsed.get("assistant_message") or
                f"Great — I have {d['attendee_name']} on {d['start_time_local']} for {d['duration_minutes']} minutes. Should I book it?",
            "state": {"draft_event": d}
        }), 200

    # If user confirmed, create the calendar event
    if confirm_intent == "yes":
        event_data = build_event_payload_from_state(state["draft_event"])
        event = create_calendar_event(event_data)

        state["awaiting_confirmation"] = False
        state["last_event_id"] = event["id"]

        return jsonify({
            "status": "success",
            "assistant_message": f"✅ Booked! {state['draft_event']['attendee_name']} at {state['draft_event']['start_time_local']} for {state['draft_event']['duration_minutes']} minutes.",
            "event_id": event["id"],
            "event_data": event_data
        }), 200

    # Otherwise, just respond with the assistant message
    return jsonify({
        "status": "ok",
        "assistant_message": parsed.get("assistant_message", "Okay."),
        "state": {"draft_event": state["draft_event"], "awaiting_confirmation": state["awaiting_confirmation"]}
    }), 200




if __name__ == "__main__":
    print("🔥 LOADED THIS app.py FILE 🔥")
    app.run(host="0.0.0.0", port=5000, debug=True)
