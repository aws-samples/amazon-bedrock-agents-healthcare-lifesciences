# Safety Signal Detection Agent

## 1. Summary

This agent helps medical professionals detect and evaluate safety signals from adverse event reports using OpenFDA data, PubMed literature, and FDA label information. It provides automated analysis of adverse event data and evidence assessment for potential safety signals.

## 2. Agent Details

### 2.1. Instructions

> You are an expert pharmacovigilance professional specializing in safety signal detection and evaluation. Help users analyze adverse event data and detect potential safety signals using OpenFDA data and supporting evidence from literature.
>
> You have access to the following tools:
>
> - analyze_adverse_events: Analyze adverse events from OpenFDA data, perform trend analysis, and detect safety signals using PRR calculation.
> - assess_evidence: Gather and assess evidence for detected signals using PubMed literature and FDA label information.
> - generate_report: Create comprehensive reports with visualizations of the analysis results.
>
> Analysis Process
>
> 1. Begin by understanding what safety analysis the user is seeking.
> 2. Use analyze_adverse_events to retrieve and analyze adverse event data for the specified product.
> 3. Present initial findings and highlight any detected safety signals.
> 4. Use assess_evidence to gather supporting evidence for significant signals.
> 5. Use generate_report to create a comprehensive report with visualizations.
> 6. Present findings with appropriate pharmacovigilance context.
>
> Response Guidelines
>
> - Provide scientifically accurate analysis based on available data
> - Explain pharmacovigilance concepts in accessible language while maintaining precision
> - Include relevant visualizations and statistical analysis
> - Highlight the strength of evidence for detected signals
> - Make appropriate interpretations considering data limitations
> - Suggest follow-up actions when warranted

### 2.2. Tools

```json
{
  name: "analyze_adverse_events",
  description: "Analyze adverse events from OpenFDA data, perform trend analysis, and detect safety signals using PRR calculation.",
  inputSchema: {
    type: "object",
    properties: {
      product_name: { type: "string", description: "Name of the product to analyze"},
      time_period: { type: "integer", description: "Analysis period in months (default: 6)"},
      signal_threshold: { type: "number", description: "PRR threshold for signal detection (default: 2.0)"}
    },
    required: ["product_name"]
  }
},
{
  name: "assess_evidence",
  description: "Gather and assess evidence for detected signals using PubMed literature and FDA label information.",
  inputSchema: {
    type: "object",
    properties: {
      product_name: { type: "string", description: "Product name"},
      adverse_event: { type: "string", description: "Adverse event term to assess"},
      include_pubmed: { type: "boolean", description: "Include PubMed literature search"},
      include_label: { type: "boolean", description: "Include FDA label information"}
    },
    required: ["product_name", "adverse_event"]
  }
},
{
  name: "generate_report",
  description: "Generate comprehensive safety signal detection report with visualizations.",
  inputSchema: {
    type: "object",
    properties: {
      analysis_results: { type: "string", description: "Results from adverse event analysis"},
      evidence_data: { type: "string", description: "Evidence assessment data"},
      include_graphs: { type: "boolean", description: "Include data visualizations"}
    },
    required: ["analysis_results", "evidence_data"]
  }
}
```

## 3. Installation

1. Verify your AWS credentials are available in your current session:

```bash
aws sts get-caller-identity
```

2. Navigate to the `Safety-Signal-Detection-Agent` folder:

```bash
cd agents_catalog/22-Safety-Signal-Detection-Agent
```

3. Deploy the agent using the provided script:

```bash
# Set required environment variables
export BUCKET_NAME="<YOUR_S3_BUCKET_NAME>"        # S3 bucket for Lambda function code
export REGION="<YOUR_REGION>"                     # AWS region for deployment
export BEDROCK_AGENT_SERVICE_ROLE_ARN="<YOUR_BEDROCK_AGENT_ROLE_ARN>"  # IAM role for Bedrock Agent

# Run the deployment script
./deploy.sh
```

The script will:

- Package Lambda function code and upload to S3
- Deploy the CloudFormation stack with all required resources
- Create the Bedrock Agent with configured action groups

Required Resources:

- An S3 bucket in the target region
- An IAM role for Bedrock Agent with appropriate permissions
- AWS CLI configured with credentials having necessary permissions

Note: The CloudFormation template uses relative paths to reference Lambda function code, which is automatically packaged and uploaded to S3 during deployment.

## 4. Usage Examples

### Example 1: Basic Analysis

```
Input: "Analyze adverse events for metformin over the past 6 months"

Output:
Analysis Results for metformin
Analysis Period: 2025-01-01 to 2025-06-30
Total Reports: 100

Top Safety Signals:
- Acute kidney injury: PRR=39.0, Reports=39 (95% CI: 0.294-0.486)
- Lactic acidosis: PRR=36.0, Reports=36 (95% CI: 0.266-0.454)
- Headache: PRR=19.0, Reports=19 (95% CI: 0.113-0.267)
...

Trend Analysis:
Report dates: 20250106 to 20250328
Peak daily reports: 17
```

### Example 2: Evidence Assessment

```
Input: "Assess evidence for lactic acidosis with metformin"

Output:
Evidence Assessment for metformin - lactic acidosis

Literature Evidence:
- Title: Risk factors for metformin-associated lactic acidosis (2024, PMID: 12345678)
  Abstract: This study identified key risk factors...

FDA Label Information:
Boxed Warnings:
WARNING: LACTIC ACIDOSIS...

Causality Assessment:
Evidence Level: Strong
Causality Score: 5
Assessment Date: 2025-06-30T10:15:00
```

## 5. Troubleshooting

### Common Issues and Solutions

#### Issue: "Module Import Error"

**Possible Causes:**

- ZIP file contains incorrect directory structure
- Lambda function code not properly packaged

**Solutions:**

- Create ZIP file without directory structure: `zip function.zip lambda_function.py`
- Avoid using `-r` option when creating ZIP file
- Verify ZIP file contents before deployment

#### Issue: "OpenFDA API Error"

**Possible Causes:**

- API rate limits exceeded
- Invalid search parameters
- Network connectivity issues

**Solutions:**

- Implement appropriate error handling and retries
- Verify search parameters format
- Check OpenFDA service status

#### Issue: "S3 Access Denied"

**Possible Causes:**

- Insufficient IAM permissions
- S3 bucket not configured properly

**Solutions:**

- Verify IAM roles have necessary permissions
- Check S3 bucket configuration
- Review CloudWatch logs for specific errors

### Performance Tips

- Use specific search terms for more relevant results
- Implement appropriate error handling
- Cache results when possible
- Monitor API rate limits

## 6. API Rate Limiting and Best Practices

### OpenFDA API Guidelines

The OpenFDA API has usage guidelines to ensure fair access:

#### Rate Limiting

- **Anonymous access**: 240 requests per minute, per IP address
- **API key access**: 240 requests per minute, per key
- **Maximum results**: 5000 records per request
- **Pagination**: Use skip parameter for large result sets

#### Data Retrieval Strategy

- **Batch size**: 100 records per request
- **Maximum total**: 1000 records (10 batches)
- **Process**:
  1. First batch retrieves total available records count
  2. Subsequent batches use skip parameter
  3. Stops after reaching 1000 records or when no more data
- **Progress tracking**: Logs number of records retrieved in each batch

#### Best Practices

**Search Optimization:**

- Use specific search parameters
- Implement pagination for large result sets
- Cache frequently accessed data
- Monitor response times

**Error Handling:**

- Implement exponential backoff
- Handle HTTP 429 responses
- Log errors appropriately
- Validate input parameters

### Data Usage and Attribution

When using data retrieved through this agent:

1. **Cite OpenFDA**: Include appropriate citations
2. **Respect terms of service**: Follow OpenFDA usage guidelines
3. **Acknowledge sources**: Mention use of OpenFDA API in publications
4. **Stay updated**: Check for API updates regularly

For more information, visit: <https://open.fda.gov/apis/>
