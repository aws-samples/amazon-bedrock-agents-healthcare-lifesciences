# Safety Signal Detection Agent

This agent helps medical professionals detect and evaluate safety signals from adverse event reports using OpenFDA data, PubMed literature, and FDA label information.

## Overview

The Safety Signal Detection Agent provides automated analysis of adverse event data and evidence assessment for potential safety signals. It combines data from multiple authoritative sources to provide comprehensive safety signal detection and evaluation.

## Features

- **Adverse Event Analysis**: Analyzes OpenFDA data to detect safety signals using Proportional Reporting Ratio (PRR)
- **Evidence Assessment**: Gathers supporting evidence from PubMed literature and FDA labels
- **Report Generation**: Creates comprehensive reports with analysis results and evidence summaries

## Architecture

The agent is implemented using three AWS Lambda functions:

1. **AdverseEventAnalysis**: Retrieves and analyzes adverse event data from OpenFDA
2. **EvidenceAssessment**: Searches PubMed and FDA labels for supporting evidence
3. **ReportGeneration**: Generates text reports and stores them in S3

## Usage

The agent can be used through natural language interactions. Here are some example prompts and their expected outputs:

### Basic Analysis
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

### Evidence Assessment
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

### Report Generation
```
Input: "Generate a safety report for metformin adverse events"

Output:
Report generated and uploaded to s3://safety-signal-detection-reports/reports/metformin/signal_detection_20250630_104200.txt
```

### Advanced Queries
```
Input: "Analyze metformin adverse events for the past 12 months"
Input: "Compare adverse events between 2024 and 2025"
Input: "Assess evidence for both kidney injury and lactic acidosis with metformin"
```

## Implementation Details

### Adverse Event Analysis

- Uses OpenFDA API to retrieve adverse event reports
- Calculates PRR for signal detection
- Performs trend analysis over specified time periods
- Identifies top adverse events by frequency and severity

### Evidence Assessment

- Searches PubMed for relevant literature
- Retrieves FDA label information
- Performs basic causality assessment
- Combines evidence from multiple sources

### Report Generation

- Creates standardized text reports
- Includes analysis results and evidence summaries
- Stores reports in S3 for future reference

## Dependencies

- AWS Lambda (Python 3.12)
- Amazon Bedrock
- OpenFDA API
- PubMed E-utilities
- AWS S3 (for report storage)

## Deployment

The agent is deployed using AWS CloudFormation. The template creates:

- Amazon Bedrock Agent
- Lambda functions for each action group
- Required IAM roles and policies
- S3 bucket for report storage

## Limitations

- Limited to publicly available data
- Basic statistical signal detection only
- Preliminary recommendations require expert review
- API rate limits may affect performance

## Contributing

See [CONTRIBUTING.md](../../CONTRIBUTING.md) for details on how to contribute to this project.

## License

This project is licensed under the Apache-2.0 License - see the [LICENSE](../../LICENSE) file for details.
