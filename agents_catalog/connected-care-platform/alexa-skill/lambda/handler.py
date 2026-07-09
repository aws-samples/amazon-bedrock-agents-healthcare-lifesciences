"""
Alexa Skill Lambda Handler for Connected Care Platform.

Translates voice intents into agent queries, sends them to the existing
AgentCore proxy, and formats responses for speech output.
"""

import json
import os
import boto3
from botocore.config import Config as BotoConfig

# The existing AgentCore proxy Lambda -- we invoke it directly (faster than HTTP)
lambda_client = boto3.client("lambda",
    region_name=os.environ.get("AWS_REGION", "us-east-1"),
    config=BotoConfig(read_timeout=120, connect_timeout=10))

PROXY_FUNCTION_NAME = os.environ.get("PROXY_FUNCTION_NAME", "connected-care-agentcore-proxy")

# Room to patient mapping (matches seed data)
ROOM_TO_PATIENT = {
    "ICU-412": {"patient_id": "P-10001", "name": "Margaret Chen"},
    "Floor3-308": {"patient_id": "P-10002", "name": "James Rodriguez"},
    "Floor2-215": {"patient_id": "P-10003", "name": "Aisha Patel"},
    "Floor1-102": {"patient_id": "P-10004", "name": "Robert Kim"},
    "Floor1-118": {"patient_id": "P-10005", "name": "Linda Okafor"},
}

# Normalize room input (Alexa might hear "412" or "ICU 412" or "ICU-412")
ROOM_ALIASES = {}
for room_id, patient in ROOM_TO_PATIENT.items():
    ROOM_ALIASES[room_id] = room_id
    ROOM_ALIASES[room_id.lower()] = room_id
    # Extract just the number part
    num = room_id.split("-")[-1] if "-" in room_id else room_id
    ROOM_ALIASES[num] = room_id


def resolve_room(room_input: str) -> tuple:
    """Resolve a room input to (room_id, patient_info) or (None, None)."""
    if not room_input:
        return None, None
    cleaned = room_input.strip()
    room_id = ROOM_ALIASES.get(cleaned) or ROOM_ALIASES.get(cleaned.lower())
    if room_id:
        return room_id, ROOM_TO_PATIENT.get(room_id)
    # Try partial match
    for alias, rid in ROOM_ALIASES.items():
        if cleaned.lower() in alias.lower() or alias.lower() in cleaned.lower():
            return rid, ROOM_TO_PATIENT.get(rid)
    return None, None


def query_agent(agent: str, prompt: str) -> str:
    """Send a prompt to an agent via the existing proxy Lambda and return the text response."""
    payload = {
        "requestContext": {"http": {"method": "POST"}},
        "body": json.dumps({
            "agent": agent,
            "prompt": prompt,
            "session_id": f"alexa-{agent}-voice",
            "sync": True,
        }),
    }

    response = lambda_client.invoke(
        FunctionName=PROXY_FUNCTION_NAME,
        InvocationType="RequestResponse",
        Payload=json.dumps(payload).encode(),
    )

    result = json.loads(response["Payload"].read().decode())
    body = json.loads(result.get("body", "{}"))
    return body.get("response", "I wasn't able to get that information right now.")


def format_for_speech(text: str, max_words: int = 90) -> str:
    """Use Bedrock to rewrite the agent response for natural spoken delivery."""
    import re

    # First try LLM rewrite for natural speech
    try:
        bedrock_runtime = boto3.client("bedrock-runtime",
            region_name=os.environ.get("AWS_REGION", "us-east-1"))

        rewrite_prompt = (
            "Rewrite this clinical summary for a nurse listening via voice assistant. "
            "Rules: under 80 words, lead with the most critical finding, no bullet points "
            "or numbered lists, no markdown, conversational but professional tone, "
            "include specific numbers only when clinically important (vitals, scores, times). "
            "Do not add any preamble like 'Here is the rewritten summary'. "
            "Just output the spoken text directly.\n\n"
            f"Clinical summary to rewrite:\n{text[:2000]}"
        )

        response = bedrock_runtime.converse(
            modelId="us.anthropic.claude-sonnet-4-20250514-v1:0",
            messages=[{"role": "user", "content": [{"text": rewrite_prompt}]}],
            inferenceConfig={"maxTokens": 200, "temperature": 0.3},
        )

        rewritten = response["output"]["message"]["content"][0]["text"].strip()
        if rewritten and len(rewritten) > 20:
            return rewritten

    except Exception:
        pass  # Fall back to regex stripping

    # Fallback: strip markdown mechanically
    text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)
    text = re.sub(r'\*([^*]+)\*', r'\1', text)
    text = re.sub(r'#{1,4}\s*', '', text)
    text = re.sub(r'\|[^\n]+\|', '', text)
    text = re.sub(r'[-]{3,}', '', text)
    text = re.sub(r'`([^`]+)`', r'\1', text)
    text = re.sub(r'```[^`]*```', '', text, flags=re.DOTALL)
    text = re.sub(r'\n{2,}', '. ', text)
    text = re.sub(r'\n', ' ', text)
    text = re.sub(r'\s{2,}', ' ', text)
    text = text.strip()

    words = text.split()
    if len(words) > max_words:
        text = ' '.join(words[:max_words]) + '.'

    return text


def build_response(speech: str, should_end: bool = True) -> dict:
    """Build an Alexa skill response."""
    return {
        "version": "1.0",
        "response": {
            "outputSpeech": {
                "type": "SSML",
                "ssml": f"<speak>{speech}</speak>",
            },
            "shouldEndSession": should_end,
        },
    }


def handler(event, context):
    """Main Alexa skill handler."""
    request_type = event.get("request", {}).get("type", "")
    intent_name = event.get("request", {}).get("intent", {}).get("name", "")
    slots = event.get("request", {}).get("intent", {}).get("slots", {})

    print(f"ALEXA_REQUEST: type={request_type} intent={intent_name} slots={json.dumps({k: v.get('value') for k, v in slots.items()} if slots else {})}")

    # Launch request
    if request_type == "LaunchRequest":
        return build_response(
            "Welcome to Connected Care. You can ask about fall risk, "
            "pressure injury status, patient updates, or current alerts. "
            "What would you like to know?",
            should_end=False,
        )

    # Help
    if intent_name == "AMAZON.HelpIntent":
        return build_response(
            "You can say things like: what's the fall risk for Room 412, "
            "when was Room 308 last repositioned, give me a status on Margaret Chen, "
            "or any alerts right now. What would you like to know?",
            should_end=False,
        )

    # Stop / Cancel
    if intent_name in ("AMAZON.StopIntent", "AMAZON.CancelIntent"):
        return build_response("Goodbye.")

    # Fallback
    if intent_name == "AMAZON.FallbackIntent":
        return build_response(
            "I didn't catch that. Try asking about fall risk for a room, "
            "pressure injury status, or current alerts.",
            should_end=False,
        )

    # === Clinical Intents ===

    if intent_name == "FallRiskIntent":
        room_input = slots.get("room", {}).get("value", "")
        room_id, patient = resolve_room(room_input)
        if not patient:
            return build_response(f"I couldn't find a patient in room {room_input}. "
                                  "Try saying the full room number, like ICU 412 or Floor 3 308.",
                                  should_end=False)

        prompt = (f"Assess the fall risk for patient {patient['name']} ({patient['patient_id']}) "
                  f"in {room_id}. Check their current vitals, blood pressure trends, "
                  f"medications that could cause dizziness or orthostatic hypotension, "
                  f"and any smart bed data showing bed exits or restlessness. "
                  f"Give a concise risk assessment.")
        response_text = query_agent("patient-monitoring", prompt)
        speech = format_for_speech(response_text)
        return build_response(speech)

    if intent_name == "PressureRiskIntent":
        room_input = slots.get("room", {}).get("value", "")
        room_id, patient = resolve_room(room_input)
        if not patient:
            return build_response(f"I couldn't find a patient in room {room_input}.",
                                  should_end=False)

        prompt = (f"Check the smart bed telemetry for patient {patient['name']} ({patient['patient_id']}) "
                  f"in {room_id}. When were they last repositioned? What's their current pressure "
                  f"distribution? What's their Braden score? Are they overdue for repositioning?")
        response_text = query_agent("device-management", prompt)
        speech = format_for_speech(response_text)
        return build_response(speech)

    if intent_name == "PatientStatusIntent":
        patient_input = slots.get("patient", {}).get("value", "")
        # Find patient by name
        matched = None
        for room_id, p in ROOM_TO_PATIENT.items():
            if patient_input.lower() in p["name"].lower():
                matched = p
                break
        if not matched:
            return build_response(f"I couldn't find a patient named {patient_input}.",
                                  should_end=False)

        prompt = (f"Give me a complete status report for patient {matched['name']} "
                  f"({matched['patient_id']}). Include current vitals, any concerning trends, "
                  f"and risk level.")
        response_text = query_agent("patient-monitoring", prompt)
        speech = format_for_speech(response_text)
        return build_response(speech)

    if intent_name == "AlertSummaryIntent":
        # For now, return the demo alerts. In production, this would query the notifications table.
        speech = ("You have 2 active alerts. "
                  "First: HIGH fall risk for Margaret Chen in ICU 412. "
                  "Bed exit detected at 2:14 AM with blood pressure trending down and "
                  "Lisinopril orthostatic risk. "
                  "Second: MEDIUM pressure injury risk for James Rodriguez in Floor 3 308. "
                  "3 hours 12 minutes since last repositioning with elevated sacral pressure. "
                  "Would you like details on either alert?")
        return build_response(speech, should_end=False)

    if intent_name == "FleetStatusIntent":
        response_text = query_agent("device-management", "Give me the fleet health summary.")
        speech = format_for_speech(response_text)
        return build_response(speech)

    if intent_name == "SmartBedStatusIntent":
        room_input = slots.get("room", {}).get("value", "")
        room_id, patient = resolve_room(room_input)
        if not patient:
            return build_response(f"I couldn't find a smart bed in room {room_input}.",
                                  should_end=False)

        prompt = (f"Get the smart bed telemetry for patient {patient['name']} ({patient['patient_id']}). "
                  f"Show bed position, pressure zones, repositioning status, and Braden score.")
        response_text = query_agent("device-management", prompt)
        speech = format_for_speech(response_text)
        return build_response(speech)

    # Unknown intent
    return build_response("I'm not sure how to help with that. Try asking about fall risk, "
                          "pressure status, or current alerts.", should_end=False)
