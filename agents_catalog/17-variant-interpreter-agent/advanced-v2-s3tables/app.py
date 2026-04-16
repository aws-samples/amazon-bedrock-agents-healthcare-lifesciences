"""Streamlit UI for deployed A2A Variant Interpreter Agent on AgentCore."""

import os
import json
import time
import uuid
import urllib.parse

import boto3
import requests
import streamlit as st
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest

st.set_page_config(page_title="Genomics Variant Analysis", page_icon="🧬", layout="wide")
st.markdown("<style>.stAppDeployButton{display:none;}#MainMenu{visibility:hidden;}</style>", unsafe_allow_html=True)

AWS_REGION = os.environ.get("AWS_REGION", "us-west-2")
AGENT_ARN = os.environ.get("AGENT_ARN", "")


def _signed_request(method, url, data=None):
    """Make a SigV4-signed request to AgentCore."""
    session = boto3.Session(region_name=AWS_REGION)
    creds = session.get_credentials().get_frozen_credentials()
    headers = {"Content-Type": "application/json"} if data else {}
    req = AWSRequest(method=method, url=url, data=data, headers=headers)
    SigV4Auth(creds, "bedrock-agentcore", AWS_REGION).add_auth(req)
    if method == "GET":
        return requests.get(url, headers=dict(req.headers), timeout=30)
    return requests.post(url, data=data, headers=dict(req.headers), timeout=300)


def _get_base_url():
    encoded = urllib.parse.quote(AGENT_ARN, safe="")
    return f"https://bedrock-agentcore.{AWS_REGION}.amazonaws.com/runtimes/{encoded}/invocations"


def send_message(text):
    """Send a message to the A2A agent and return the response text."""
    url = f"{_get_base_url()}?qualifier=DEFAULT"
    payload = json.dumps({
        "jsonrpc": "2.0",
        "id": str(uuid.uuid4()),
        "method": "message/send",
        "params": {
            "message": {
                "role": "user",
                "parts": [{"kind": "text", "text": text}],
                "messageId": str(uuid.uuid4()),
            }
        },
    })
    resp = _signed_request("POST", url, payload)
    if resp.status_code != 200:
        return f"❌ Error (HTTP {resp.status_code}): {resp.text[:200]}"

    try:
        body = resp.json()
    except (json.JSONDecodeError, ValueError):
        return f"❌ Invalid JSON response: {resp.text[:200]}"

    result = body.get("result", {})
    parts = []
    for artifact in result.get("artifacts", []):
        for p in artifact.get("parts", []):
            if p.get("kind") == "text":
                parts.append(p["text"])
    return "\n".join(parts) if parts else "No response from agent."


def main():
    st.title("🧬 Genomics Variant Analysis Agent")

    with st.sidebar:
        st.subheader("Agent")
        # Check connectivity
        try:
            card_url = f"{_get_base_url()}/.well-known/agent-card.json?qualifier=DEFAULT"
            resp = _signed_request("GET", card_url)
            if resp.status_code == 200:
                card = resp.json()
                st.success(f"✅ Connected: {card['name']}")
                for s in card.get("skills", []):
                    st.caption(f"🔧 {s['name']}")
            else:
                st.error(f"❌ Agent returned {resp.status_code}")
        except Exception as e:
            st.error(f"❌ Cannot reach agent: {e}")

        st.caption(f"Region: {AWS_REGION}")
        st.caption(f"ARN: {AGENT_ARN[-40:]}")

        if st.button("🗑️ Clear Chat"):
            st.session_state.messages = []
            st.rerun()

        st.divider()
        st.subheader("💡 Sample Questions")
        for i, q in enumerate([
            "How many samples are in the cohort?",
            "Show me PASS variants on chromosome 22",
            "What are the distinct chromosomes?",
            "Show variants for sample HG00096 on chr22",
            "What is the quality distribution?",
        ]):
            if st.button(f"📝 {q}", key=f"s_{i}", use_container_width=True):
                st.session_state["selected"] = q

    if "messages" not in st.session_state:
        st.session_state.messages = []

    for msg in st.session_state.messages:
        avatar = "🧑‍⚕️" if msg["role"] == "user" else "🤖"
        with st.chat_message(msg["role"], avatar=avatar):
            st.markdown(msg["content"])
            if "elapsed" in msg:
                st.caption(f"⏱️ {msg['elapsed']:.1f}s")

    if "selected" in st.session_state:
        prompt = st.session_state.pop("selected")
        _process(prompt)
        st.rerun()

    if prompt := st.chat_input("Ask about genomic variants..."):
        _process(prompt)


def _process(prompt):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user", avatar="🧑‍⚕️"):
        st.markdown(prompt)

    with st.chat_message("assistant", avatar="🤖"):
        placeholder = st.empty()
        start = time.time()
        with st.spinner("🔧 Querying agent..."):
            try:
                response = send_message(prompt)
            except requests.exceptions.ReadTimeout:
                response = "⏱️ Request timed out (>5 min). Try a more specific query, e.g. add 'LIMIT 10' or filter by position range."
            except Exception as e:
                response = f"❌ Error: {e}"
        elapsed = time.time() - start
        placeholder.markdown(response)
        st.caption(f"⏱️ {elapsed:.1f}s")

    st.session_state.messages.append({"role": "assistant", "content": response, "elapsed": elapsed})


if __name__ == "__main__":
    main()
