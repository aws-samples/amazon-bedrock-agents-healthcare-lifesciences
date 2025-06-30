# Safety Signal Detection Agent

## 1. Summary

Detect and evaluate safety signals from adverse event reports using OpenFDA, PubMed, and FDA Label data. This agent helps pharmacovigilance professionals analyze adverse event trends, detect potential safety signals using statistical methods, gather supporting evidence, and generate comprehensive reports with visualizations to answer questions like "Are there any emerging safety concerns for this drug?"

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

### 2.2. Guardrails

| Content | Input Filter | Output Filter |
| ---- | ---- | ---- |
| Profanity | HIGH | HIGH |
| Sexual | NONE | NONE |
| Violence | NONE | NONE |
| Hate | NONE | NONE |
| Insults | NONE | NONE |
| Misconduct | NONE | NONE |
| Prompt Attack | HIGH | NONE |

### 2.3. Tools

```json
{
  name: "analyze_adverse_events",
  description: "Analyze adverse events and detect safety signals using OpenFDA data",
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
  description: "Gather and assess evidence for safety signals using PubMed and FDA label data",
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
  description: "Generate comprehensive safety signal detection report with visualizations",
  inputSchema: {
    type: "object",
    properties: {
      analysis_results: { type: "object", description: "Results from adverse event analysis"},
      evidence_data: { type: "object", description: "Evidence assessment data"},
      include_graphs: { type: "boolean", description: "Include data visualizations"}
    },
    required: ["analysis_results", "evidence_data"]
  }
}
```

## 3. Installation

1. (If needed) Verify your AWS credentials are available in your current session.

`aws sts get-caller-identity`

2. (If needed) Create a Amazon S3 bucket to store the agent template.

`aws s3 mb s3://YOUR_S3_BUCKET_NAME`

3. Navigate to the `Safety-Signal-Detection-Agent` folder

`cd agents_catalog/22-Safety-Signal-Detection-Agent`

4. Package and deploy the agent template

```bash
export BUCKET_NAME="<REPLACE>"
export NAME="<REPLACE>"
export REGION="<REPLACE>"
export BEDROCK_AGENT_SERVICE_ROLE_ARM="<REPLACE>"

aws cloudformation package --template-file "safety-signal-detection-agent-cfn.yaml" \
  --s3-bucket $BUCKET_NAME \
  --output-template-file "safety-signal-detection-agent-cfn-packaged.yaml"
aws cloudformation deploy --template-file "safety-signal-detection-agent-cfn-packaged.yaml" \
  --capabilities CAPABILITY_IAM \
  --stack-name $NAME \
  --region $REGION \
  --parameter-overrides \
  AgentAliasName="Latest" \
  AgentIAMRoleArn=$BEDROCK_AGENT_SERVICE_ROLE_ARM
rm safety-signal-detection-agent-cfn-packaged.yaml
```

## 4. Usage Examples

### Example 1: Basic Safety Signal Analysis
**User Query:** "Analyze adverse events for metformin in the last 6 months"

**Agent Response:**
```
Analysis Results for Metformin (Last 6 Months)
=============================================

SUMMARY:
- Total Reports: 2,543
- Serious Events: 892 (35.1%)
- Death Reports: 124 (4.9%)

TOP ADVERSE EVENTS (by PRR):
1. Lactic acidosis (PRR: 4.2)
   - Reports: 156
   - Statistical Significance: p < 0.001
2. Diarrhea (PRR: 2.8)
   - Reports: 423
   - Statistical Significance: p < 0.001
3. Vitamin B12 deficiency (PRR: 2.3)
   - Reports: 89
   - Statistical Significance: p < 0.01

[Time Series Graph of Report Counts]
[Bar Chart of Top Adverse Events]
[Heat Map of Signal Strength]

EVIDENCE ASSESSMENT:
- Lactic acidosis: Known risk, listed in current labeling
- Diarrhea: Known common side effect
- Vitamin B12 deficiency: Documented in literature, monitoring recommended

Report URL: [Link to detailed report]
```

### Example 2: Evidence Assessment
**User Query:** "Evaluate evidence for lactic acidosis with metformin"

**Agent Response:**
```
Evidence Assessment: Metformin and Lactic Acidosis
================================================

LITERATURE REVIEW:
- 15 relevant publications identified
- 3 systematic reviews
- 4 observational studies
- 8 case reports

KEY FINDINGS:
1. Systematic Reviews:
   - Rare but serious adverse event
   - Risk factors identified
   - Incidence: 4.3 cases per 100,000 patient-years

2. FDA Label Status:
   - Listed as boxed warning
   - Contraindicated in severe renal impairment
   - Risk factors and monitoring requirements specified

3. Biological Plausibility:
   - Mechanism well understood
   - Related to renal clearance
   - Risk factors align with pharmacology

[Forest Plot of Study Results]
[Evidence Quality Assessment Chart]

Report URL: [Link to detailed report]
```

### Example 3: Trend Analysis
**User Query:** "Show adverse event trends for aspirin over the past year"

**Agent Response:**
```
Adverse Event Trends: Aspirin (Last 12 Months)
============================================

TREND ANALYSIS:
- Overall reporting trend: Stable
- Seasonal variation detected
- No significant new signals identified

QUARTERLY BREAKDOWN:
Q1: 1,234 reports
Q2: 1,456 reports
Q3: 1,345 reports
Q4: 1,289 reports

[Time Series Plot with Trend Line]
[Seasonal Decomposition Plot]
[Signal Detection Heat Map]

KEY OBSERVATIONS:
1. Consistent reporting pattern
2. Expected seasonal increase in Q2
3. No emerging safety signals

Report URL: [Link to detailed report]
```

## Common Use Cases

### For Signal Detection
- "Analyze adverse events for [drug name]"
- "Check for safety signals in [time period]"
- "Compare adverse event rates between products"

### For Evidence Assessment
- "Evaluate evidence for [adverse event] with [drug]"
- "Check literature support for signal"
- "Assess biological plausibility of [adverse event]"

### For Trend Analysis
- "Show adverse event trends for [drug]"
- "Track reporting patterns over time"
- "Analyze seasonal variations in reports"

### For Report Generation
- "Generate safety report for [drug]"
- "Create visualization of signal detection results"
- "Summarize evidence for detected signals"

## 5. Troubleshooting

### Common Issues and Solutions

#### Issue: "No adverse events found"
**Possible Causes:**
- Drug name misspelled
- No reports in specified time period
- API connection issues

**Solutions:**
- Check drug name spelling
- Extend time period
- Verify API connectivity

#### Issue: "Error accessing OpenFDA API"
**Possible Causes:**
- API key issues
- Rate limiting
- Network connectivity

**Solutions:**
- Verify API key
- Implement rate limiting
- Check network connection

#### Issue: "Report generation failed"
**Possible Causes:**
- Invalid data format
- Missing required information
- S3 permissions

**Solutions:**
- Verify data structure
- Provide all required fields
- Check S3 access

## 6. API Rate Limiting and Best Practices

### OpenFDA API Guidelines

#### Rate Limiting
- Standard API key: 240 requests per minute
- No API key: 1 request per second
- Implement exponential backoff for failures

#### Best Practices
- Cache frequently accessed data
- Use efficient query parameters
- Handle rate limits gracefully
- Monitor API response times

### Data Usage and Attribution

When using data retrieved through this agent:

1. **Cite OpenFDA**: Include appropriate citations
2. **Respect data limitations**: Acknowledge reporting biases
3. **Use appropriate disclaimers**: Note preliminary nature of signals
4. **Follow up appropriately**: Verify signals through proper channels

### Recommended Citation

```
This analysis uses data from the FDA Adverse Event Reporting System (FAERS) 
database through the OpenFDA API. The data may be incomplete or contain 
reporting biases. All findings should be verified through appropriate 
pharmacovigilance procedures.
