from flask import Flask, request, jsonify
from flask_cors import CORS
import os
from openai import AzureOpenAI
import json
from datetime import datetime, timedelta, date
import uuid
import threading
from routes.state import get_state
from routes.llm import call_azure_openai_state, call_azure_openai_add_patient
from routes.schemas import build_event_payload_from_state, parse_llm_response
from routes.graph import create_calendar_event, graph_bp
from routes.db import add_patient
app = Flask(__name__)
CORS(app)

app.register_blueprint(graph_bp)

###
### TEST FUNCTIONS
###
## Function to get graph token
## Endpoint to handle AI requests
@app.route("/ai/ping", methods=["POST"])
def ai_ping():
    '''
    AI endpoint to handle user messages for scheduling and patient management.

    combines user message with current session state and passes it to AI
    switches between scheduling mode and add_patient mode based on state
    1) scheduling mode: manages draft_event, prompts for missing info, confirms booking
    2) add_patient mode: adds pending_patient, prompts for missing info, confirms addition
    mode is switched to add_patient when scheduling encounters unknown patient
    '''
    body = request.json or {}
    session_id = body.get("session_id")
    user_msg = (body.get("message") or "").strip()

    if not session_id:
        return jsonify({"status": "error", "assistant_message": "Missing session_id"}), 400
    if not user_msg:
        return jsonify({"status": "error", "assistant_message": "Please enter a message."}), 400

    state = get_state(session_id)

    ####
    #### Logic for adding a patient
    ####
    if state.get("mode") == "add_patient":
        print('add', state)
        llm_text = call_azure_openai_add_patient(user_msg, state["pending_patient"], state["awaiting_confirmation"])
        # with open(f"/app/llm_debug_{session_id}.log", "a") as f:
        #     f.write("----\n")
        #     f.write(state["mode"] + "\n")
        #     f.write(llm_text + "\n")
        parsed = json.loads(llm_text)

        updates = parsed.get("updates") or {}
        for k, v in updates.items():
            if k in state["pending_patient"] and v is not None:
                state["pending_patient"][k] = v

        missing = []
        if not state["pending_patient"]["name"]:
            missing.append("name")
        if not state["pending_patient"]["email"]:
            missing.append("email")

        if missing:
            state["awaiting_confirmation"] = False
            return jsonify({
                "status": "needs_clarification",
                "assistant_message": parsed.get("assistant_message"),
                "state": {"mode": "add_patient", "missing_fields": missing, "pending_patient": state["pending_patient"]}
            }), 200

        confirm_intent = (parsed.get("confirm_intent") or "unknown").lower()
        print('confirm_intent:', confirm_intent, flush=True)
        if not state["awaiting_confirmation"] and confirm_intent != "yes":
            state["awaiting_confirmation"] = True 
            p = state["pending_patient"]
            return jsonify({
                "status": "awaiting_confirmation",
                "assistant_message": parsed.get("assistant_message") or f"Please confirm you want to add {p['name']} with email {p['email']}.",
                "state": {"mode": "add_patient", "pending_patient": p}
            }), 200

        if confirm_intent == "yes":
            p = state["pending_patient"]
            add_patient(p["name"], p["email"], p.get("phone"), p.get("dob"))

            # switch back to scheduling, keep the draft_event intact
            state["mode"] = "schedule"
            state["awaiting_confirmation"] = True
            state["pending_patient"] = {"name": None, "email": None, "phone": None, "dob": None}

            # Now that patient exists, move right back into scheduling UX:
            d = state["draft_event"]
            return jsonify({
                "status": "ok",
                "assistant_message": f"✅ Added {p['name']}. Now, should I book the appointment with {d['attendee_name']} on {d['start_time_local']} for {d['duration_minutes']} minutes?",
                "state": {"mode": "schedule", "draft_event": d, "awaiting_confirmation": True}
            }), 200
        
        # Otherwise, just respond with the assistant message
        return jsonify({
            "status": "ok",
            "assistant_message": parsed.get("assistant_message", "Okay."),
            "state": {"mode": "add_patient", "pending_patient": state["pending_patient"], "awaiting_confirmation": state["awaiting_confirmation"]}
        }), 200
        
    ####
    #### Logic for scheduling an appointment
    ####

    # Ask LLM for updates 
    else:
        print(state.get("mode"))
        print(state)
        llm_text = call_azure_openai_state(user_msg, state["draft_event"], state["awaiting_confirmation"])

        # write each message to a text file that persists in the volume for debugging
        with open(f"/app/llm_debug_{session_id}.log", "a") as f:
            f.write("----\n")
            f.write(state["mode"] + "\n")
            f.write(llm_text + "\n")

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
        print('confirm_intent:', confirm_intent, flush=True)
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
            try:
                event_data = build_event_payload_from_state(state["draft_event"])
            except ValueError:
                # patient not found -> switch modes
                state["mode"] = "add_patient"
                state["awaiting_confirmation"] = False
                state["pending_patient"]["name"] = state["draft_event"]["attendee_name"]

                return jsonify({
                    "status": "needs_clarification",
                    "assistant_message": f"I couldn’t find {state['draft_event']['attendee_name']} in your directory. What’s their email so I can add them?",
                    "state": {"mode": "add_patient", "pending_patient": state["pending_patient"]}
                }), 200

            event = create_calendar_event(event_data)

            return_status = jsonify({
                "status": "success",
                "assistant_message": f"✅ Booked {event_data['attendee_name']} at {state['draft_event']['start_time_local']} for {event_data.get('duration_minutes', 30)} minutes.",
                "event_id": event.get("id"),
                "event_data": event_data
            }), 200

            # reset state
            state["draft_event"] = {
            "attendee_name": None,
            "start_time_local": None,
            "duration_minutes": 30,
            "title": "Patient appointment",
            "notes": None
    }

            return return_status


        # Otherwise, just respond with the assistant message
        return jsonify({
            "status": "ok",
            "assistant_message": parsed.get("assistant_message", "Okay."),
            "state": {"draft_event": state["draft_event"], "awaiting_confirmation": state["awaiting_confirmation"]}
        }), 200




if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
