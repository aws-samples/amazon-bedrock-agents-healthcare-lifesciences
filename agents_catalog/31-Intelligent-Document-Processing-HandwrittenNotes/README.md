# IDP Agent for Hand-written Documents

## Problem Statement

Intelligent Document Processin (IDP) is extracting structured data from unstructured text. 
Unstructured data comprises 80% of enterprise data and largely untapped due to its complexity. This content represents a rich source of insights that can drive better decision-making, enhance customer experiences, and uncover new business opportunities. And yet, only about 18% of organizations are actually able to take advantage of their unstructured data at scale.

Organisations process hundreds of unstructured forms daily, requiring manual data validation or extraction that is:
- **Time-consuming**: 200-300 forms/day with manual review that could take 10-15 min per form. Manual processing is consuming 50-70% of employee time with error rates up to 4%. 
- **Current Solutions are Costly and Insufficient**: OCR accuracy is 70% and the cost is $5-15 per documents
- **Inefficient**: Incomplete workflows mean that employees need to search for information in different systems. No ability to ask follow-up questions without re-reading entire documents



## Solution Overview

A Bedrock Data Automation powered IDP agent that:
1. **Extracts structured data** from handwritten medical forms with confidence scores
2. **Enables natural language queries** - ask follow-up questions without reprocessing
3. **Maintains conversation context** - remembers extracted data across questions
4. **Processes multimodal content** - handles checkboxes, handwriting, and printed text

### Key Features
- ✅ Handwritten text recognition
- ✅ Checkbox detection
- ✅ Confidence scoring per field
- ✅ JSON structured output
- ✅ Sub-90 second processing time
- ✅ Conversational follow-up questions

## Demo

<video src="demo/IDP_Agent_Demo.mp4" controls></video>

## Technology Stack

### Amazon Bedrock AgentCore
Serverless runtime for deploying and scaling AI agents with:
- Automatic scaling and load balancing
- Built-in observability and monitoring
- IAM-based security and access control

### Strands Agent SDK
Multi-agent orchestration framework providing:
- Agent loop with reasoning and tool use
- Conversation state management
- Flexible tool integration (Python, MCP, community tools)

### Bedrock Data Automation (BDA) MCP
Multimodal document processing via Model Context Protocol:
- PDF to structured data conversion
- Handwriting recognition
- Visual element extraction (checkboxes, tables, signatures)

## Architecture

```
User Question → Streamlit UI → AgentCore Runtime → Strands Agent
                                                         ↓
                                                   BDA MCP Server
                                                         ↓
                                                  Extract Data
                                                         ↓
                                                  Cache Results (for follow-up questions)
                                                         ↓
                                                Return JSON and the answer
```
![Architecture](architecture/IDP_Agent_Architecture.png)

## Deployment Steps

### Prerequisites
- AWS CLI configured with credentials
- Python 3.11+
- `uv` package manager installed
- Access to Amazon Bedrock AgentCore

### 1. Configure Agent

```bash
cd agent
uv run agentcore configure -e agent.py
```

### 2. Deploy to AgentCore

```bash
uv run agentcore launch
```

This will:
- Build ARM64 container in AWS CodeBuild
- Push to Amazon ECR
- Deploy to AgentCore Runtime
- Configure IAM roles and permissions

### 3. Run Streamlit UI

```bash
cd ..
streamlit run app.py
```

The UI will open at `http://localhost:8501`

### 4. Test the Agent

**First message**: "extract all data from the medical intake form. The output should be in JSON format and include the confidence scores for each field"
- Processes document (~20-30 seconds)
- Returns structured JSON with confidence scores
- Caches results for session

**Follow-up questions**: "what is the patient name?" or "does the patient have diabetes?"
- Instant responses (<2 seconds)
- Uses cached extraction data
- No document reprocessing needed

## Project Structure

```
.
├── streamlit-chat/
│   ├── app.py                          # Streamlit chat interface
│   ├── example/
│   │   ├── agent.py                    # Main agent implementation
│   │   ├── Dockerfile                  # Container configuration
│   │   ├── requirements.txt            # Python dependencies
│   │   └── .bedrock_agentcore.yaml    # AgentCore configuration
│   └── static/                         # UI assets
├── data/                               # Sample input documents
└── README.md                           # This file
```

## Key Implementation Details

### Why is Bedrock Data Automation MCP Required?
Testing showed that even the latest LLMs cannot extract handwritten notes from medical forms without specialized tools. We tested with Claude Sonnet 3.5 and Haiku 3.5 models via the Bedrock Playground, and both returned the same response indicating the PDF file was empty or unreadable.

This demonstrates that standard LLM vision capabilities are insufficient for processing complex handwritten documents, making Bedrock Data Automation MCP essential for accurate data extraction.

![Test via Bedrock Playground](images/Test-via-Bedrock-Playground.png) 

### File Caching
Files are downloaded from S3 once and cached in `/tmp/` for reuse across invocations within the same container instance.

### Conversation Memory
Extracted data is stored in-memory per session ID, enabling instant follow-up questions without reprocessing.

### Error Handling
- Automatic retry logic for transient failures
- Graceful fallback for missing data
- Detailed error messages for debugging

## Performance Metrics

- **Initial extraction**: 20-30 seconds (includes S3 download + BDA processing)
- **Follow-up questions**: <2 seconds (uses cached data)
- **Throughput**: Supports 200-300 documents/day
- **Accuracy**: Confidence scores provided per field

## Cost Optimization

1. **File caching** reduces S3 API calls
2. **Conversation memory** eliminates redundant LLM invocations
3. **Serverless runtime** scales to zero when idle
4. **Efficient prompting** minimizes token usage

## Next Steps

- [ ] Add support for multiple document types
- [ ] Implement batch processing for high-volume scenarios
- [ ] Add human-in-the-loop review workflow
- [ ] Export extracted data to database/API
- [ ] Add audit logging and compliance features

## Resources

- [Amazon Bedrock AgentCore Documentation](https://docs.aws.amazon.com/bedrock-agentcore/)
- [Strands Agents Framework](https://github.com/awslabs/strands-agents)
- [Bedrock Data Automation](https://aws.amazon.com/bedrock/data-automation/)
- [Model Context Protocol (MCP)](https://modelcontextprotocol.io/)
