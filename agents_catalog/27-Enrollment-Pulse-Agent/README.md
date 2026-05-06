# 🎯 Enrollment Pulse - Clinical Trial Enrollment Optimization Agent

AI-powered clinical operations assistant that analyzes Veeva CTMS data to provide enrollment insights and recommend targeted interventions for study managers.

## 📋 **Project Status**
✅ **COMPLETE - Backend + Agent System**
- Phase 1: Backend Data Processing ✅
- Phase 2: Strands Agent + CLI Interface ✅  
- Phase 3: AWS Lambda Deployment ✅

## ✨ Key Features

- **🤖 Natural Language Interface** - Ask questions in plain English
- **📊 Site-Specific Analysis** - Detailed per-site performance and recommendations
- **📈 Historical Performance** - Track enrollment trends over time
- **🔄 Alternative Site Recommendations** - Backup sites for underperforming locations
- **🎯 Targeted Interventions** - Specific recommendations for each site
- **⚡ Real-time Analysis** - Live CTMS data processing

## 🏗️ System Architecture

```
CLI Interface ──→ Strands Agent ──→ AWS Bedrock Claude
      │                    │
      ▼                    ▼
FastAPI Backend ──→ CTMS Data Processing
      │
      ▼
AWS Lambda Deployment
```

## 🎯 Demo Data Results
Based on the ONCO-2025-117 trial data:
- **Overall Status**: 91/120 subjects enrolled (75.8%)
- **Top Performers**: Dana-Farber (96%), MD Anderson (92%), Memorial Sloan (90%)
- **Underperformers**: UCLA (45%), Mayo Clinic (40%)
- **CRA Performance Gap**: 36.7% between Thomas Nguyen and Amanda Garcia's sites
- **Projected Shortfall**: 19 subjects without intervention

## 🚀 Quick Start

### AWS Deployment
```bash
# Deploy backend to AWS Lambda
cd backend
./build.sh
./deploy_only.sh
```

## 📁 Project Structure

```
enrollment-agent/
├── backend/                  # Complete backend system
│   ├── src/                 # Backend source code
│   │   ├── agent/          # Strands Agent integration
│   │   ├── data/           # CTMS data processing
│   │   └── analysis/       # Clinical analytics
│   ├── data/               # Demo CTMS data
│   ├── backend_api.py      # FastAPI application
│   ├── enrollment_lambda.py # Lambda handler
│   ├── template.yaml       # SAM CloudFormation template
│   ├── build.sh           # Build script
│   ├── deploy_only.sh     # Deploy script
│   └── requirements.txt   # Python dependencies
├── tests/                   # Test suite
│   ├── README.md           # Test documentation
│   └── test_*.py           # Test files
└── .kiro/                   # Kiro steering documents
```

## 💬 Natural Language Capabilities

**The agent automatically responds at the granular site level for every question**, providing detailed analysis for each individual site.

Ask questions like:
- "What is the current enrollment status?" → *Gets site-by-site breakdown*
- "Which sites are underperforming?" → *Detailed analysis per underperforming site*
- "Show me enrollment trends" → *Historical trends for each site individually*
- "What are your recommendations?" → *Site-specific interventions for each location*
- "How is performance?" → *Individual site performance with specific metrics*

## 📊 Site-Specific Analysis Features

- **Individual Site Metrics**: Current performance, enrollment rates, risk levels
- **Historical Trends**: Monthly enrollment patterns, performance trajectories
- **Tailored Recommendations**: Site-specific intervention strategies
- **Alternative Sites**: Backup options for underperforming locations
- **CRA Performance**: Correlation analysis between CRA assignments and site success

## 🛠️ Technology Stack

- **Language**: Python 3.12
- **Agent Framework**: Strands Agent SDK
- **AI Model**: AWS Bedrock Claude Sonnet 4.5
- **Backend**: FastAPI
- **Interface**: Lambda Function URLs
- **Data Processing**: Pandas, Pydantic
- **Deployment**: AWS SAM (Lambda + API Gateway)

## 📊 AWS Deployment

### Architecture
- **Backend**: FastAPI on AWS Lambda + Function URLs
- **AI**: AWS Bedrock Claude Sonnet 4.5
- **Cost**: ~$33-140/month

### Quick Deploy
```bash
cd backend
./build.sh              # Build Lambda package
./deploy_only.sh        # Deploy to AWS
```

See `backend/README.md` for detailed deployment documentation.

## 🔧 Development

### Local Setup
```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r backend/requirements.txt

# Set AWS credentials (for Bedrock access)
export AWS_ACCESS_KEY_ID=your_key
export AWS_SECRET_ACCESS_KEY=your_secret
export AWS_DEFAULT_REGION=us-west-2
```

### Testing
```bash
# Test data processing
python tests/test_data_processing.py

# Test AWS deployment (with IAM auth)
python tests/test_query_endpoint.py
```

## 🔌 Usage

### AWS Lambda Function URL
- Direct HTTP access to deployed Lambda function
- FastAPI backend with automatic documentation
- 15-minute timeout for complex analysis
- Requires IAM authentication for security

## 📚 Documentation

- **`backend/README.md`** - Complete AWS deployment guide
- **`tests/README.md`** - Test suite documentation
