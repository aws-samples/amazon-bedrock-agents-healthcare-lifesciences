# Medical Device Management Agent on Strands Agents (CDK TypeScript)

## Introduction

This example deploys a medical device management agent built with the Strands Agents SDK using AWS CDK TypeScript. The agent provides a Streamlit web interface for medical device organizations to monitor devices, search medical literature, and find clinical trials.

### Features

- **Medical Device Monitoring**: Check device status, maintenance schedules, and locations
- **PubMed Literature Search**: Research medical literature and evidence-based information  
- **Clinical Trials Lookup**: Search ClinicalTrials.gov for relevant studies
- **Multi-Agent Architecture**: Coordinated AI agents for comprehensive medical support
- **Streaming UI**: Real-time response updates with Streamlit
- **Basic Authentication**: Secure username/password authentication
- **Fargate Deployment**: Scalable containerized deployment on AWS

### Tools

#### Device Status Management
- `get_device_status`: Retrieve current status of a medical device by ID
- `list_all_devices`: List all medical devices with their status and maintenance info

#### PubMed Integration  
- `search_pubmed`: Search PubMed database for medical literature using NCBI eUtils API

#### Clinical Trials
- `search_clinical_trials`: Search ClinicalTrials.gov for relevant clinical studies

## Prerequisites

- [AWS CLI](https://aws.amazon.com/cli/) installed and configured
- [Node.js](https://nodejs.org/) 18+ and npm
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed and running
- Python 3.11+ for local development

## Project Structure

```
25-Medical-Device-Agent/
├── cdk/                    # CDK infrastructure code
│   ├── stacks/            # CDK stack definitions
│   └── constant.ts        # Configuration constants
├── agents/                # Strands agent definitions
├── tools/                 # Agent tools and integrations
├── app.py                 # Streamlit web application
├── Dockerfile             # Container configuration
├── requirements.txt       # Python dependencies
└── README.md             # This file
```

## Setup and Deployment

1. **Install dependencies:**

```bash
cd agents_catalog/25-Medical-Device-Agent

# Install CDK dependencies
npm install

# Install Python dependencies (for local development)
pip install -r requirements.txt
```

2. **Bootstrap CDK (if not already done):**

```bash
npx cdk bootstrap
```

3. **Configure Authentication:**

Copy the example environment file and set secure credentials:

```bash
cp .env.example .env
# Edit .env with your secure username and password
```

4. **Deploy to AWS:**

```bash
npm run deploy
```

5. **Access the application:**

After deployment completes, the output will show:
- Application Load Balancer DNS name for accessing the Streamlit application
- Authentication credentials (username/password)

⚠️ **IMPORTANT**: Change the default credentials immediately after first deployment!

**First-time setup:**
1. Configure authentication credentials (see Security section below)
2. Access the application URL and sign in with your credentials

## Usage

### Web Interface

Access the deployed Streamlit application through the ALB URL. The interface provides:

- **Chat Interface**: Ask questions about medical devices, literature, or clinical trials
- **Real-time Streaming**: See AI responses as they're generated
- **Multi-modal Queries**: Combine device status checks with literature research

### Sample Queries

- "What's the status of device DEV001?"
- "List all medical devices in the system"
- "Search PubMed for MRI safety protocols"
- "Find clinical trials for cardiac devices"
- "What maintenance is due this month?"

### Local Development

Run the application locally for development:

```bash
# Ensure .env file is configured with credentials
npm run local
```

## Architecture

### Components

- **Streamlit Frontend**: Interactive web interface for medical professionals
- **Medical Coordinator Agent**: Main orchestrator using Claude 3 Sonnet
- **Device Management**: SQLite database with sample medical device data
- **External APIs**: PubMed (NCBI eUtils) and ClinicalTrials.gov integration
- **AWS Fargate**: Containerized deployment with auto-scaling
- **Application Load Balancer**: Public access with health checks

### AWS Services Used

- **Amazon ECS Fargate**: Container hosting
- **Application Load Balancer**: Load balancing and health checks
- **Amazon VPC**: Network isolation
- **Basic Authentication**: Username/password authentication
- **CloudWatch Logs**: Application logging
- **Amazon ECR**: Container image registry
- **Amazon Bedrock**: Claude 3 Sonnet model access

## Configuration

### Authentication

The application uses Basic Authentication with username/password. See `SECURITY.md` for detailed security configuration.

### Environment Variables

The application uses these environment variables:

- `ENABLE_AUTHENTICATION`: Enable/disable authentication (default: true)
- `AUTH_TYPE`: Authentication type (default: basic)
- `BASIC_AUTH_USERNAME`: Username for authentication
- `BASIC_AUTH_PASSWORD`: Password for authentication
- `AWS_DEFAULT_REGION`: AWS region
- `LOG_LEVEL`: Logging level (default: INFO)

### Model Configuration

The agent uses Claude 3 Sonnet (`anthropic.claude-3-sonnet-20240229-v1:0`) by default. To use a different model, update `agents/medical_coordinator.py`.

### Database

The application includes a sample SQLite database with medical device data. In production, this should be replaced with a proper database service like Amazon RDS.

## Security Considerations

- **IAM Roles**: Least privilege access for Bedrock and CloudWatch
- **VPC**: Private subnets with NAT gateway for outbound access
- **Security Groups**: Restricted access between components
- **ALB**: Public access only through load balancer
- **Container Security**: Non-root user in container

## Cleanup

To remove all resources:

```bash
npx cdk destroy
```

## Customization

### Adding New Tools

1. Create a new tool in the `tools/` directory
2. Import and add to the agent in `agents/medical_coordinator.py`
3. Update the system prompt if needed

### Modifying the UI

The Streamlit interface is defined in `app.py`. Customize the layout, add new features, or integrate additional data sources as needed.

### Scaling

The deployment is configured for development/demo use. For production:

- Increase ECS service `desiredCount`
- Use Amazon RDS instead of SQLite
- Add CloudFront for global distribution
- Implement stronger authentication (OAuth, SAML)
- Add IP restrictions and rate limiting
- Add monitoring and alerting
- Set up proper SSL certificates

## Additional Resources

- [Strands Agents Documentation](https://github.com/strands-agents)
- [AWS CDK TypeScript Documentation](https://docs.aws.amazon.com/cdk/latest/guide/work-with-cdk-typescript.html)
- [Amazon Bedrock Documentation](https://docs.aws.amazon.com/bedrock/)
- [Streamlit Documentation](https://docs.streamlit.io/)