# Architecture Overview

## System Architecture

The Medical Device Management Agent follows a modern cloud-native architecture deployed on AWS:

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Internet      │    │  Application     │    │   ECS Fargate   │
│   Users         │───▶│  Load Balancer   │───▶│   Container     │
│                 │    │  (Public)        │    │   (Private)     │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                                         │
                       ┌──────────────────┐             │
                       │   Amazon         │◀────────────┘
                       │   Bedrock        │
                       │   (Claude 3)     │
                       └──────────────────┘
                                │
                       ┌──────────────────┐
                       │   External APIs  │
                       │   • PubMed       │
                       │   • ClinicalTrials│
                       └──────────────────┘
```

## Components

### Frontend Layer
- **Streamlit Application**: Interactive web interface
- **Real-time Streaming**: WebSocket-based AI response streaming
- **Responsive Design**: Works on desktop and mobile devices

### Application Layer  
- **Medical Coordinator Agent**: Main orchestrator using Strands framework
- **Tool Integration**: Modular tools for different data sources
- **Session Management**: Maintains conversation context

### Infrastructure Layer
- **AWS Fargate**: Serverless container hosting
- **Application Load Balancer**: High availability and health checks
- **VPC**: Network isolation with public/private subnets
- **CloudWatch**: Logging and monitoring

### Data Layer
- **SQLite Database**: Sample medical device data (demo)
- **External APIs**: PubMed and ClinicalTrials.gov integration
- **Amazon Bedrock**: AI model access

## Security Architecture

### Network Security
- Private subnets for application containers
- NAT Gateway for outbound internet access
- Security groups with minimal required access
- ALB as single public entry point

### Identity & Access Management
- ECS task roles with least privilege
- Bedrock access limited to specific models
- No hardcoded credentials
- CloudWatch logs access for debugging

### Data Protection
- All traffic encrypted in transit
- Container images scanned for vulnerabilities
- No sensitive data in logs
- Secure handling of medical device information

## Scalability Considerations

### Current Configuration (Demo)
- Single ECS task for simplicity
- SQLite for device data
- Basic health checks

### Production Recommendations
- Multiple ECS tasks across AZs
- Amazon RDS for device database
- ElastiCache for session storage
- CloudFront for global distribution
- Auto Scaling based on CPU/memory
- Enhanced monitoring and alerting

## Integration Points

### Internal Integrations
- Strands Agents framework for AI orchestration
- Streamlit for web interface
- SQLite for device data storage

### External Integrations
- **NCBI eUtils API**: PubMed literature search
- **ClinicalTrials.gov API**: Clinical trial information
- **Amazon Bedrock**: Claude 3 Sonnet model access

## Deployment Pipeline

1. **Build Phase**: Docker image creation with multi-stage build
2. **Push Phase**: Image pushed to Amazon ECR
3. **Deploy Phase**: CDK deploys infrastructure and updates ECS service
4. **Health Checks**: ALB verifies application health
5. **Traffic Routing**: Gradual traffic shift to new version

## Monitoring & Observability

### Logging
- Application logs to CloudWatch
- ECS task logs for debugging
- ALB access logs for traffic analysis

### Metrics
- ECS service metrics (CPU, memory, task count)
- ALB metrics (request count, latency, errors)
- Custom application metrics via CloudWatch

### Health Checks
- ALB target group health checks
- ECS service health monitoring
- Container-level health checks

## Cost Optimization

### Current Costs
- ECS Fargate: Pay per vCPU/memory used
- ALB: Hourly charge + LCU pricing
- Bedrock: Pay per token processed
- CloudWatch: Log storage and API calls

### Optimization Strategies
- Right-size container resources
- Use Spot instances for development
- Implement request caching
- Monitor and optimize Bedrock usage
- Set up billing alerts