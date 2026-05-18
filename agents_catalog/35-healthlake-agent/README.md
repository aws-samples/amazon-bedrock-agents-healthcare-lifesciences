# HealthLake AI Assistant - AgentCore Implementation

An intelligent healthcare agent built on AWS Bedrock AgentCore, providing natural language access to FHIR R4 clinical data and healthcare documents stored in AWS HealthLake.

## Overview

The HealthLake AI Assistant enables healthcare professionals to query patient records, search clinical data, and access medical guidelines through conversational AI, eliminating the need for technical FHIR expertise.

## Agent Capabilities

The agent provides the following capabilities through 7 specialized tools:

| Capability | Description |
|---|---|
| **FHIR Resource Search** | Search across all FHIR R4 resource types (Patient, Condition, Observation, Medication, Procedure, Coverage, Claim, AllergyIntolerance, MedicationRequest, etc.) with flexible query parameters |
| **Patient Record Retrieval** | Retrieve a complete patient record using the FHIR `$patient-everything` operation with optional date range filtering |
| **Resource Detail Lookup** | Read any individual FHIR resource by type and ID with automatic FHIR code translation to human-readable text |
| **Datastore Metadata** | Query HealthLake datastore status, FHIR version, endpoint, and configuration |
| **Clinical Document Access** | List, read, and retrieve clinical documents (guidelines, notes, reports) stored in S3 buckets |
| **Presigned URL Generation** | Generate time-limited secure download links for S3 documents (up to 7-day expiration) |
| **S3 URI Resolution** | Automatically parse and follow `s3://` URIs found in FHIR DocumentReference resources |

Additional runtime features:
- Session-based conversation memory (30-day retention)
- Role-based access control (patient, doctor, nurse, admin)
- Real-time streaming responses with tool execution visibility
- Automatic retry with exponential backoff for AWS API calls

## Input Data Sources

The agent connects to the following data sources:

### Primary: AWS HealthLake (FHIR R4 Datastore)

All clinical data is read from an [AWS HealthLake](https://aws.amazon.com/healthlake/) datastore via signed FHIR REST API calls. Supported FHIR resource types include:

- **Patient** — Demographics, identifiers, contact information
- **Condition** — Diagnoses, clinical status, onset dates
- **Observation** — Lab results, vital signs, measurements
- **MedicationRequest** — Prescriptions, dosage, status
- **Procedure** — Surgical and clinical procedures performed
- **Coverage** — Insurance and payer information
- **Claim** — Billing claims and adjudication
- **AllergyIntolerance** — Allergies and adverse reactions
- **DocumentReference** — Pointers to clinical documents (often S3 URIs)

Data access is authenticated via AWS SigV4 signing against the HealthLake FHIR endpoint.

### Secondary: Amazon S3 (Clinical Documents)

Clinical documents referenced by FHIR resources (or queried directly) are stored in S3:

- Preventive care guidelines (JSON)
- Clinical notes and encounter summaries (text)
- Medical reports and imaging results
- Any document referenced via `s3://` URIs in FHIR `DocumentReference` resources

### AI Model: Amazon Bedrock

- **Claude Opus 4.5** (`anthropic.claude-opus-4-5-20250514`) for reasoning and natural language generation
- Configurable model, temperature, and max tokens via environment variables

## Architecture

![HealthLake AI Assistant Architecture](docs/generated-diagrams/healthlake_agentcore_architecture.png)

The solution uses AWS Bedrock AgentCore with a serverless Lambda runtime, providing:
- Zero infrastructure management
- Automatic scaling
- Built-in observability with CloudWatch
- Cost-effective pay-per-invocation model

### Architecture Layers

**Client Layer:**
- AgentCore CLI for command-line invocation
- Web Chatbot for browser-based interaction
- FastAPI Backend for REST API integration

**AgentCore Runtime:**
- Serverless Lambda execution (ARM64)
- 30-day session memory retention
- Container image stored in Amazon ECR
- IAM-based access control

**Data & AI Layer:**
- AWS HealthLake for FHIR R4 clinical data
- Amazon Bedrock with Claude Opus 4.5
- Amazon S3 for clinical documents
- CloudWatch for logging and metrics

For detailed architecture documentation, see [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Prerequisites

- AWS CLI configured with appropriate credentials
- AWS Bedrock AgentCore CLI installed: `pip install bedrock-agentcore`
- Docker installed and running
- Python 3.11 or higher
- AWS HealthLake datastore with FHIR R4 data

## Quick Start

### 1. Configure Environment

Create a `.env` file:

```bash
# AWS Configuration
AWS_PROFILE=your-aws-profile
AWS_REGION=us-west-2

# HealthLake Configuration
HEALTHLAKE_DATASTORE_ID=your-datastore-id

# Bedrock Configuration
BEDROCK_MODEL_ID=anthropic.claude-opus-4-5-20250514
BEDROCK_TEMPERATURE=0.7
BEDROCK_MAX_TOKENS=4096

# S3 Configuration (optional)
S3_BUCKET_NAME=your-s3-bucket-name
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure AgentCore

```bash
agentcore configure --entrypoint agent_agentcore.py --name healthlake_agent
```

### 4. Deploy to AWS

```bash
agentcore deploy --agent healthlake_agent
```

### 5. Add IAM Permissions

Run the provided script or manually add permissions:

```bash
.\add_healthlake_permissions.ps1
```

### 6. Test the Agent

```bash
agentcore invoke '{"prompt": "What is the HealthLake datastore information?"}' --agent healthlake_agent
```

## Project Structure

```
healthlake-agent/
├── agent.py                      # Strands agent with 7 tools
├── agent_agentcore.py            # AgentCore entrypoint wrapper
├── config.py                     # Configuration management
├── requirements.txt              # Python dependencies
├── Dockerfile                    # AgentCore container image
├── .bedrock_agentcore.yaml       # AgentCore configuration
│
├── models/
│   ├── session.py                # SessionContext and UserRole
│   ├── agent_response.py         # Response models
│   └── interaction_log.py        # Logging models
│
├── utils/
│   ├── auth_helpers.py           # Authorization validation
│   ├── retry_handler.py          # Retry logic for AWS calls
│   └── fhir_code_translator.py   # FHIR code translation
│
├── prompts/
│   └── healthcare_assistant_prompt.py  # System prompt
│
├── scripts/
│   ├── deploy_agentcore.ps1      # Deployment script
│   ├── configure_agent.ps1       # Configuration script
│   ├── add_healthlake_permissions.ps1  # IAM permissions
│   └── test_agentcore_agent.ps1  # Testing script
│
├── docs/
│   ├── ARCHITECTURE.md           # Architecture documentation
│   ├── DEPLOYMENT.md             # Deployment guide
│   └── QUICKSTART.md             # Quick reference
│
└── examples/
    ├── chatbot_agentcore.html    # Web chatbot interface
    └── api.py                    # FastAPI integration example
```

## Usage Examples

### CLI Invocation

```bash
# Basic query
agentcore invoke '{"prompt": "Search for patients with diabetes"}' --agent healthlake_agent

# With session context
agentcore invoke '{"prompt": "Show me patient details", "context": {"user_id": "doctor-001", "user_role": "doctor"}}' --agent healthlake_agent

# With session ID for conversation continuity
agentcore invoke '{"prompt": "Tell me more about the first patient", "session_id": "session-123"}' --agent healthlake_agent
```

### Web Chatbot

Open `examples/chatbot_agentcore.html` in a browser for an interactive interface.

### API Integration

See `examples/api.py` for FastAPI integration example.

## Available Tools

The agent includes 7 specialized tools organized into two categories:

**FHIR Tools (HealthLake):**
| Tool | Description | Input |
|---|---|---|
| `get_datastore_info` | Retrieve datastore metadata (status, FHIR version, endpoint) | None |
| `search_fhir_resources` | Search for FHIR resources with query parameters | `resource_type`, `search_params`, `count` |
| `read_fhir_resource` | Read a complete FHIR resource by ID (with code translation) | `resource_type`, `resource_id` |
| `patient_everything` | Get all resources for a patient (`$patient-everything`) | `patient_id`, `start_date`, `end_date` |

**S3 Tools (Clinical Documents):**
| Tool | Description | Input |
|---|---|---|
| `list_s3_documents` | List documents in an S3 bucket/prefix | `bucket_name`, `prefix` |
| `read_s3_document` | Read document content (text or base64, up to 50MB) | `bucket_name`, `document_key`, `max_size_mb` |
| `generate_s3_presigned_url` | Create a time-limited secure download link | `bucket_name`, `document_key`, `expiration` |

## Monitoring

### View Logs

```bash
aws logs tail /aws/bedrock-agentcore/runtimes/healthlake_agent-UNIQUE_ID-DEFAULT --follow --region REGION --profile YOUR_PROFILE
```

### Check Agent Status

```bash
agentcore status --agent healthlake_agent --verbose
```

### CloudWatch Dashboard

Access the GenAI Observability dashboard in AWS Console:
- Navigate to CloudWatch → GenAI Observability → Agent Core

## Security

- IAM-based access control with least-privilege permissions
- Role-based authorization at application layer
- Encryption at rest and in transit
- HIPAA-eligible services (HealthLake, Bedrock, S3, Lambda)
- CloudTrail logging for audit compliance

## Cost Estimate

**Monthly costs for moderate usage (~1,000 queries):**
- AgentCore Runtime: ~$0.02
- Memory (STM): ~$0.03
- CloudWatch Logs: ~$2.50
- ECR Storage: ~$0.20
- Bedrock (Claude Opus 4.5): ~$27.50
- **Total: ~$30/month**

## Troubleshooting

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for detailed troubleshooting guide.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Contributing

Contributions are welcome! Please read the contributing guidelines before submitting pull requests.

## Support

- AWS Documentation: Refer to AWS Bedrock AgentCore documentation
- CloudWatch Dashboard: Monitor agent performance and costs
- AWS Support: Contact AWS Support for infrastructure issues
