# Connected Care -- Alexa Voice Interface

Voice interface for the Connected Care Platform. Nurses interact hands-free with patient data, fall risk assessments, pressure injury monitoring, and proactive alerts.

## Sample Utterances

```
"Alexa, ask Connected Care what's the fall risk for Room 412"
"Alexa, ask Connected Care when was Room 308 last repositioned"
"Alexa, ask Connected Care give me a status on Margaret Chen"
"Alexa, ask Connected Care any alerts right now"
"Alexa, ask Connected Care what's the fleet status"
"Alexa, ask Connected Care smart bed status for Room 412"
```

## Architecture

```
Alexa --> Alexa Skill --> Lambda (handler.py)
                              |
                              | Invokes existing proxy Lambda directly
                              v
                         AgentCore Proxy --> AgentCore Runtime --> Agent
                              |
                              v
                         Response formatted for speech (no markdown)
                              |
                              v
                         Alexa speaks the clinical summary
```

No new agents, tools, or data sources. The Alexa skill is a thin voice adapter over the existing platform.

## Deployment

### Step 1: Deploy the Lambda

The Alexa Lambda is part of the ConnectedCareAgentCoreStack:

```bash
cd infrastructure
npx cdk deploy ConnectedCareAgentCoreStack --require-approval never
```

Save the `AlexaSkillLambdaArn` from the output.

### Step 2: Create the Alexa Skill

1. Go to the [Alexa Developer Console](https://developer.amazon.com/alexa/console/ask)
2. Click "Create Skill"
3. Name: "Connected Care"
4. Model: "Custom"
5. Hosting: "Provision your own" (we use our own Lambda)
6. Click "Create Skill", then choose "Start from Scratch"

### Step 3: Configure the Interaction Model

1. In the skill builder, go to "JSON Editor" (left sidebar under Interaction Model)
2. Paste the contents of `interactionModels/custom/en-US.json`
3. Click "Save Model" then "Build Model"

### Step 4: Set the Endpoint

1. Go to "Endpoint" in the left sidebar
2. Select "AWS Lambda ARN"
3. Paste the `AlexaSkillLambdaArn` from Step 1 into the "Default Region" field
4. Click "Save Endpoints"

### Step 5: Test

1. Go to the "Test" tab in the Alexa Developer Console
2. Enable testing for "Development"
3. Type or speak: "ask connected care any alerts right now"

You can also test on any Echo device linked to the same Amazon account.

## Intents

| Intent | What it does | Agent used |
|---|---|---|
| FallRiskIntent | Fall risk assessment for a room | Patient Monitoring |
| PressureRiskIntent | Repositioning and pressure status | Device Management |
| PatientStatusIntent | Full patient status by name | Patient Monitoring |
| AlertSummaryIntent | List current proactive alerts | Demo data (future: notifications table) |
| FleetStatusIntent | Device fleet health summary | Device Management |
| SmartBedStatusIntent | Smart bed telemetry for a room | Device Management |

## Speech Response Formatting

Agent responses are formatted for voice:
- Markdown stripped (no tables, headers, bold, code blocks)
- Truncated to ~90 words (~30 seconds of speech)
- SSML wrapping for Alexa speech synthesis
