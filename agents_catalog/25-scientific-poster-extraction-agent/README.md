# Scientific Poster Extraction with AI

Extract structured insights from scientific posters using Amazon Bedrock Data Automation and Strands Agent SDK.

## Problem Statement

Scientific conferences generate thousands of research posters containing valuable insights, but extracting structured information is traditionally manual and time-consuming. This solution automates the digitization and analysis of poster content.

## Solution

This implementation combines two powerful technologies:

- **Amazon Bedrock Data Automation**: Enterprise-grade multimodal processing with advanced OCR, layout understanding, and AI-powered content extraction
- **Strands Agent SDK**: Workflow orchestration framework with Model Context Protocol (MCP) integration for seamless tool connectivity

## Key Features

- **Multimodal Processing**: Handles PDFs, images, and documents with intelligent layout understanding
- **Structured Extraction**: Automatically identifies titles, authors, methods, results, figures, and tables
- **High Accuracy**: Leverages foundation models trained on scientific content
- **Scalable**: Processes individual files or batches efficiently
- **Production Ready**: Built-in error handling, logging, and monitoring

## Use Cases

- **Research Institutions**: Digitize poster sessions from conferences
- **Pharmaceutical Companies**: Analyze clinical trial posters and findings
- **Academic Libraries**: Create searchable databases of research presentations
- **Grant Agencies**: Review and categorize funded research outcomes

## Quick Start

### Prerequisites
- AWS account with Bedrock Data Automation access
- Python 3.8+ environment
- S3 bucket for temporary storage

### Installation
```bash
pip install strands mcp boto3
```

### Configuration
```bash
export AWS_PROFILE=default
export AWS_REGION=us-east-1
export AWS_BUCKET_NAME=your-bucket-name
```

### Run the Notebook
```bash
jupyter notebook scientific_poster_extraction.ipynb
```

## Sample Output

The system extracts:
- **Metadata**: Document statistics (52 elements, 1 table, 20 figures detected)
- **Structured Content**: Markdown-formatted text with preserved hierarchy
- **Visual Elements**: Automatic figure and table identification
- **Rich Context**: Semantic understanding of scientific terminology

## Architecture

1. **Document Upload**: PDF automatically uploaded to S3
2. **Multimodal Processing**: BDA analyzes text and visual elements
3. **Structure Extraction**: Identifies document hierarchy and relationships
4. **Content Analysis**: AI models extract semantic meaning
5. **Structured Output**: Results returned in JSON with rich metadata

## Sample Data

Example poster: [Tumor-Infiltrating Leukocytes Research](https://cdn.stemcell.com/media/files/poster/SP00240-Isolation_of_Tumor_Infiltrating_Leukocytes_from_Mouse_Tumors.pdf)

## Next Steps

- **Batch Processing**: Handle multiple posters simultaneously
- **Custom Schemas**: Define specific extraction templates
- **Semantic Search**: Build searchable indexes with vector embeddings
- **Integration**: Connect with research databases and LIMS systems

For production deployment, consider Amazon Bedrock AgentCore for enhanced scalability and enterprise features.