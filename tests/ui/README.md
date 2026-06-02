# UI Tests — Nova Act

Automated end-to-end UI testing for AgentCore agents using Amazon Nova Act.

## How it works

1. Launches the Streamlit app (`agentcore_template/app.py`)
2. Nova Act navigates the UI using natural language commands
3. Selects each agent, sends test queries, verifies responses
4. Runs headless in CI/CD (no browser window needed)

## Prerequisites

```bash
pip install nova-act pytest boto3
```

- Nova Act API key from [nova.amazon.com/act](https://nova.amazon.com/act)
- Agents deployed to AgentCore
- Streamlit app running

## Run

```bash
# Start Streamlit (in another terminal)
cd agentcore_template
streamlit run app.py

# Run UI tests
export NOVA_ACT_API_KEY="your-key"
export STREAMLIT_URL="http://localhost:8501"
export AWS_PROFILE="your-profile"
pytest tests/ui/ -m ui -v

# Headless mode (CI/CD)
HEADLESS=true pytest tests/ui/ -m ui -v
```

## Test Scenarios

| Agent | Scenario | Validates |
|-------|----------|-----------|
| Enrollment Pulse | Ask for enrollment status | Response contains site names |
| Clinical Prior Auth | Submit patient for prior auth | Agent processes specialty selection |
| Clinical PVQ | Start questionnaire | Agent asks follow-up questions |
| Medical Device | List devices | Response contains device IDs |
