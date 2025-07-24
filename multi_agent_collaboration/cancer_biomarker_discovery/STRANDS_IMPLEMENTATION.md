# Cancer Biomarker Discovery with Strands Agents

This implementation demonstrates how to replicate the cancer biomarker discovery multi-agent system using Strands agents instead of Amazon Bedrock agents, while retaining the same underlying infrastructure and Lambda functions.

## Architecture Overview

### Original Bedrock Agents Architecture
- **Supervisor Agent**: Orchestrates multiple specialized Bedrock agents
- **Specialized Agents**: Each with action groups that invoke Lambda functions
- **Infrastructure**: CloudFormation-deployed databases, Lambda functions, S3 buckets

### New Strands Agents Architecture
- **Orchestrator Agent**: Coordinates specialized Strands agents using "Agents as Tools" pattern
- **Specialized Agents**: Each wrapping Lambda function calls as custom tools
- **Infrastructure**: Same CloudFormation-deployed resources (no changes needed)

## Key Components

### 1. Custom Tools for Lambda Integration
Each existing Lambda function is wrapped as a Strands `@tool`:

```python
@tool
def query_biomarker_database(sql_query: str) -> str:
    """Execute a SQL query against the biomarker database."""
    payload = {
        "actionGroup": "sqlActionGroup",
        "apiPath": "/queryredshift", 
        "httpMethod": "GET",
        "parameters": [{"name": "query", "type": "string", "value": sql_query}]
    }
    response = lambda_client.invoke(
        FunctionName=LAMBDA_FUNCTIONS['database_query'],
        Payload=json.dumps(payload)
    )
    return json.dumps(json.loads(response['Payload'].read()), indent=2)
```

### 2. Specialized Agents as Tools
Following the "Agents as Tools" pattern from the Strands example:

```python
@tool
def biomarker_database_analyst(query: str) -> str:
    """Analyze biomarker database queries and generate SQL to retrieve relevant data."""
    database_agent = Agent(
        system_prompt=DATABASE_ANALYST_PROMPT,
        tools=[get_database_schema, query_biomarker_database, refine_sql_query]
    )
    response = database_agent(query)
    return str(response)
```

### 3. Orchestrator Agent
Main agent that coordinates all specialized agents:

```python
biomarker_orchestrator = Agent(
    system_prompt=BIOMARKER_ORCHESTRATOR_PROMPT,
    tools=[
        biomarker_database_analyst,
        statistician_agent,
        clinical_evidence_researcher,
        medical_imaging_expert
    ]
)
```

## Specialized Agents

### 1. Biomarker Database Analyst
- **Tools**: `get_database_schema`, `query_biomarker_database`, `refine_sql_query`
- **Lambda Functions**: `querydatabaselambda`
- **Capabilities**: SQL generation, database queries, schema analysis

### 2. Statistician Agent  
- **Tools**: `perform_survival_analysis`, `create_bar_chart`
- **Lambda Functions**: `survivaldataprocessinglambda`, `MatPlotBarChartLambda`
- **Capabilities**: Survival analysis, statistical modeling, data visualization

### 3. Clinical Evidence Researcher
- **Tools**: `search_pubmed`
- **Lambda Functions**: `PubMedQueryFunction`
- **Capabilities**: Literature search, evidence synthesis, citation analysis

### 4. Medical Imaging Expert
- **Tools**: `process_medical_images`
- **Lambda Functions**: `imaging-biomarker-lambda`
- **Capabilities**: Image processing, radiomics analysis, biomarker extraction

## Setup Instructions

### 1. Deploy Infrastructure
```bash
# Deploy the original CloudFormation stack (no changes needed)
aws cloudformation deploy --template-file agent_build.yaml --stack-name biomarker-agents
```

### 2. Install Strands SDK
```bash
pip install strands-agents-sdk boto3
```

### 3. Configure Lambda Function Names
Update the `LAMBDA_FUNCTIONS` dictionary in the notebook with your actual deployed function names:

```python
LAMBDA_FUNCTIONS = {
    'database_query': 'your-actual-querydatabaselambda-name',
    'survival_analysis': 'your-actual-survivaldataprocessinglambda-name',
    'bar_chart': 'your-actual-MatPlotBarChartLambda-name',
    'pubmed_query': 'your-actual-PubMedQueryFunction-name',
    'imaging_biomarker': 'your-actual-imaging-biomarker-lambda-name'
}
```

### 4. Set AWS Configuration
```python
AWS_REGION = 'your-deployment-region'  # e.g., 'us-west-2'
```

## Example Usage

The notebook includes examples that mirror the original Bedrock agent capabilities:

```python
# Database query
query1 = "What is the average age of patients diagnosed with Adenocarcinoma?"
response1 = biomarker_orchestrator(query1)

# Statistical analysis with visualization  
query2 = "What are the top 5 biomarkers with lowest p-value for overall survival?"
response2 = biomarker_orchestrator(query2)

# Literature research
query3 = "What imaging properties are associated with EGFR pathway?"
response3 = biomarker_orchestrator(query3)

# Multi-agent collaboration
query4 = "Find high POSTN patients, analyze survival, and search literature evidence"
response4 = biomarker_orchestrator(query4)
```

## Benefits of Strands Approach

### Cost Effectiveness
- No Bedrock agent infrastructure costs
- Pay only for Lambda function executions
- No agent alias or knowledge base charges

### Flexibility
- Easy to modify agent behavior and prompts
- Simple to add new specialized agents
- No complex infrastructure updates required

### Transparency
- Full visibility into agent decision-making
- Access to conversation history and tool usage
- Easy debugging and optimization

### Portability
- Runs in any Python environment with AWS access
- No vendor lock-in to Bedrock agents
- Can be deployed in various compute environments

## Key Differences from Bedrock Agents

| Aspect | Bedrock Agents | Strands Agents |
|--------|----------------|----------------|
| **Infrastructure** | Managed service | Self-managed |
| **Cost** | Agent + usage fees | Lambda execution only |
| **Customization** | Limited by service | Full control |
| **Debugging** | Limited visibility | Full transparency |
| **Deployment** | CloudFormation complex | Simple Python deployment |
| **Scaling** | Automatic | Manual configuration |

## Files Structure

```
├── strands_multi_agent_biomarker.ipynb  # Main implementation notebook
├── STRANDS_IMPLEMENTATION.md            # This documentation
├── agent-as-tools.ipynb                 # Reference Strands example
├── connecting-with-aws-services.ipynb   # AWS integration example
└── multi_agent_biomarker.ipynb         # Original Bedrock implementation
```

## Next Steps

1. **Run the notebook**: Execute `strands_multi_agent_biomarker.ipynb` after configuring your Lambda function names
2. **Test queries**: Try the example queries to verify functionality
3. **Customize agents**: Modify system prompts and add new capabilities as needed
4. **Monitor performance**: Track Lambda execution times and costs
5. **Scale as needed**: Add more specialized agents or enhance existing ones

This implementation provides the same biomarker discovery capabilities as the original Bedrock agents solution while offering greater flexibility, cost control, and transparency.
