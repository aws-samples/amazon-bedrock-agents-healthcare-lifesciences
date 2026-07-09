# Prior Authorization Processing System

## Overview

The `run_prior_auth.py` script is an AI-powered healthcare prior authorization processing system that automates the analysis of patient data against healthcare billing guides and fee schedules to determine claim approval and cost calculations.

## Features

- **Automated Specialty Selection**: Analyzes patient FHIR data to determine the most appropriate medical specialty
- **Document Retrieval**: Downloads the latest billing guides and fee schedules from healthcare authorities
- **PDF Processing**: Extracts and parses content from billing guide PDFs
- **Fee Schedule Analysis**: Processes Excel-based fee schedules using AWS Bedrock AI
- **Cost Calculation**: Determines claim costs and approval status based on official fee schedules
- **AI-Powered Analysis**: Uses Claude 3.5 Sonnet for intelligent document analysis and decision making

## Prerequisites

### Required Dependencies
```bash
pip install -r requirements.txt
```

### AWS Configuration
- AWS credentials configured (via AWS CLI, environment variables, or IAM roles)
- Access to Amazon Bedrock services
- Permissions for Amazon Titan Text Express model

### Required Files
- `patient_data/fhir_encounter_bundle.json` - Patient FHIR data
- `resources/hca_billing_guides_structured.json` - Healthcare billing guides metadata

## Usage

### Basic Execution
```bash
python run_prior_auth.py sample_patient_data/fhir_encounter_bundle.json
```

The script will:
1. Load patient data from the FHIR bundle
2. Analyze the data to determine appropriate medical specialty
3. Download relevant billing guides and fee schedules
4. Parse documents and calculate costs
5. Provide approval/denial decision with cost breakdown

### Input Data Format

#### Patient Data (FHIR Format)
The script expects patient data in FHIR (Fast Healthcare Interoperability Resources) format located at:
```
patient_data/fhir_encounter_bundle.json
```

#### Billing Guides Structure
Healthcare billing guides metadata should be structured as:
```json
{
  "categories": {
    "specialty_name": {
      "items": [
        {
          "title": "Document Title",
          "url": "https://example.com/document.pdf"
        }
      ]
    }
  }
}
```

## Core Functions

### Document Management
- `get_guidance_document_list(specialty)` - Retrieves available documents for a specialty
- `download_appropriate_document(download_dict)` - Downloads PDFs and fee schedules
- `parse_pdf(pdf_file)` - Extracts text content from PDF documents

### Data Processing
- `parse_fee_schedule(fee_schedule_file)` - Processes Excel fee schedules using AI
- `calculate_claim_approval(parsed_data, fee_schedule)` - Determines approval status and costs

## Output

The system provides:
- **SUCCESS/FAILURE** status for document downloads
- **Total cost** calculation with line-item breakdown
- **Approval/Denial** decision with reasoning
- **Cost modifiers** based on fee schedule data
- **Detailed explanations** for each cost component

## File Structure

```
hca_agent/
├── run_prior_auth.py              # Main script
├── xlsx_processor_bedrock.py      # Excel processing with Bedrock
├── patient_data/
│   └── fhir_encounter_bundle.json # Patient FHIR data
├── resources/
│   └── hca_billing_guides_structured.json # Billing guides metadata
└── downloaded_files/              # Downloaded documents (auto-created)
```

## Configuration

### Logging
Uncomment the logging configuration in the script to enable debug output:
```python
logging.getLogger("strands").setLevel(logging.DEBUG)
logging.basicConfig(
    format="%(levelname)s | %(name)s | %(message)s", 
    handlers=[logging.StreamHandler()]
)
```

### AI Model Configuration
The script uses Claude 3.5 Sonnet by default. To change the model:
```python
agent = Agent(
    tools=[...],
    system_prompt=system_prompt,
    model="your-preferred-model-id"
)
```

## Error Handling

The system handles various error scenarios:
- Missing or invalid patient data files
- Network issues during document downloads
- PDF parsing failures
- AWS service errors
- Invalid fee schedule formats

## Security Considerations

- Ensure AWS credentials are properly secured
- Patient data should be handled according to HIPAA compliance requirements
- Downloaded documents are stored locally - consider cleanup policies
- Network requests are made to external healthcare authority websites

## Troubleshooting

### Common Issues

1. **AWS Credentials Error**
   - Verify AWS credentials are configured
   - Check IAM permissions for Bedrock services

2. **File Not Found Errors**
   - Ensure patient data file exists at the specified path
   - Verify billing guides metadata file is present

3. **Download Failures**
   - Check internet connectivity
   - Verify URLs in billing guides metadata are accessible

4. **PDF Parsing Issues**
   - Ensure PyPDF2 is installed and up to date
   - Some PDFs may have protection that prevents text extraction

## Integration

This script can be integrated into larger healthcare systems by:
- Modifying input data sources (database, API endpoints)
- Customizing output formats (JSON, XML, database records)
- Adding webhook notifications for approval/denial decisions
- Implementing batch processing for multiple patients

## Compliance

This system is designed to work with official healthcare billing guides and fee schedules to ensure compliance with healthcare authority regulations. Always verify that the latest documents are being used and that calculations align with current healthcare policies.