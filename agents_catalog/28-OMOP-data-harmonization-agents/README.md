# OMOP Structure and Harmonization Agent(s)

This project provides AI-powered harmonization of healthcare data to the OMOP Common Data Model using semantic similarity and embeddings.

## Project Setup

### Prerequisites

- Python 3.11+
- uv (Python package manager)
- AWS CLI configured with appropriate credentials
- Node.js and npm (for CDK)
- AWS CDK CLI

### Install Prerequisites

#### 1. Install uv (Python package manager)
```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

```

#### 2. Install Node.js and npm
```bash

brew install node

```

#### 3. Install AWS CLI
```bash

brew install awscli

```

#### 4. Install AWS CDK CLI

**Option 1: Install via npm (Recommended)**
```bash
# Install globally via npm
npm install -g aws-cdk

# Verify installation
cdk --version
```

**Option 2: Install via pip (Python)**
```bash
# Install via pip
pip install aws-cdk-lib

# For CDK v1 (legacy)
pip install aws-cdk
```

**Verify CDK Installation**
```bash
# Check CDK version
cdk --version

# Should output something like: 2.x.x (build xxxxxxx)

# Check CDK help
cdk --help
```

**CDK Prerequisites Check**
```bash
# Ensure Node.js version is compatible (14.x or later)
node --version

# Ensure npm is available
npm --version

# Check AWS CLI is configured
aws sts get-caller-identity
```

#### 5. Configure AWS CLI
```bash
# Configure your AWS credentials
aws configure

# Or set environment variables
export AWS_ACCESS_KEY_ID=your_access_key
export AWS_SECRET_ACCESS_KEY=your_secret_key
export AWS_DEFAULT_REGION=us-east-1
```

### 1. UV Project Setup

```bash
# Clone the repository
git clone <repository-url>
cd agents_catalog/28-OMOP-data-harmonization-agents

# Install dependencies using uv
uv sync

```

### 2. CDK Infrastructure Setup

```bash
# Navigate to infrastructure directory
cd infra

# Bootstrap CDK (first time only)
uv run cdk bootstrap

# Deploy the OMOP ontology stack
uv run cdk deploy 

# Note the Neptune Graph ID from the output
```

### 3. Populate Neptune database with OMOP ontology data
```
cd ..
uv run python omop-ontology/load_omop.py --graph-id <your-neptune-graph-id> --table-file ./data/OMOP_CDMv5.4_Table_Level.csv --field-file ./data/OMOP_CDMv5.4_Field_Level.csv --region <your-region>
```

**Important**: After CDK deployment, you must run `load_omop.py` to populate the Neptune database with OMOP ontology data before using the agents.

## Running the Agents

### OMOP Structure Agent

Query the OMOP CDM structure and relationships:

```bash
uv run python agents/omop_structure_agent.py --neptune-endpoint <your-neptune-graph-id> --region <your-region>
```

Example queries:
- "What tables are in the OMOP CDM?"
- "Show me the fields in the person table"
- "What are the relationships between condition_occurrence and person?"

### OMOP Harmonization Agent

Harmonize data terms to OMOP fields using semantic similarity:

```bash
uv run python agents/omop_harmonization_agent.py --input-source test-data/CMS_PDE_Data_Dictionary.csv --neptune-endpoint <your-neptune-graph-id> 
```

This will:
1. Load the input CSV file
2. Process each row (Label and Table Description)
3. Find similar OMOP fields using embeddings
4. Generate harmonization recommendations
5. Save results to `<input-file>_harmonization_results.json`

### Input Data Format

The harmonization agent expects CSV files with the following columns:
- `Label`: The field name to harmonize
- `Table Description`: Context about the data source

Example test data files are provided in the `test-data/` directory:
- `CMS_PDE_Data_Dictionary.csv`
- `CMS_Inpatient_Claims_Data_Dictionary.csv`
- `CMS_Outpatient_Claims_Data_Dictionary.csv`

## Project Structure

```
├── agents/
│   ├── omop_harmonization_agent.py    # Main harmonization agent
│   └── omop_structure_agent.py        # OMOP structure query agent
├── omop-ontology/
│   ├── OMOP_ontology.py              # OMOP ontology class
│   └── load_omop.py                  # Data loading utilities
├── infra/
│   └── omop_ontology_stack.py        # CDK infrastructure
├── test-data/                        # Sample data files
├── pyproject.toml                    # UV project configuration
└── README.md                         # This file
```

## Key Features

### Harmonization Agent
- **Embedding-based similarity**: Uses Amazon Bedrock Titan embeddings for semantic matching
- **Foreign key analysis**: Identifies relationships between OMOP fields
- **Contextual recommendations**: Considers data source context for better matches
- **Batch processing**: Processes entire CSV files automatically
- **Detailed results**: Saves comprehensive harmonization results with confidence scores

### Structure Agent
- **Interactive queries**: Ask questions about OMOP CDM structure
- **Relationship exploration**: Discover connections between tables and fields
- **Real-time responses**: Direct queries to Neptune graph database

## Architecture

The project uses:
- **Amazon Neptune Analytics**: Graph database for OMOP CDM structure
- **Amazon Bedrock**: AI models for embeddings and harmonization
- **Strands Framework**: Agent orchestration and tool integration
- **UV**: Modern Python package management
- **AWS CDK**: Infrastructure as code

## Troubleshooting

### Common Issues

1. **Neptune connection errors**: Ensure your AWS credentials are configured and the Neptune graph is accessible
2. **Embedding errors**: Verify Bedrock access and model availability in your region
3. **Import errors**: Make sure all dependencies are installed with `uv sync`

### Logging

The agents use structured logging:
- Strands framework: DEBUG level
- Other components: INFO level

Check logs for detailed error information and processing status.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test with sample data
5. Submit a pull request

## License

[Add your license information here]