# DMTA Orchestration Agent

Design-Make-Test-Analyze (DMTA) cycle orchestration agent for Cablivi (Caplacizumab) optimization using active learning approaches.

## Overview

This agent helps orchestrate iterative experimental cycles to improve vWF A1 domain binding affinity through active learning approaches. It provides tools for:

- **Plan Project**: Create initial project setup and active learning strategy
- **Design Variants**: Generate nanobody variants using acquisition functions (EI/UCB)
- **Make Test**: Execute expression and SPR binding assays with FactorX simulation
- **Analyze Results**: Analyze results using Gaussian Process modeling and recommend next steps

## Prerequisites

1. **AWS Account**: You need an AWS account with appropriate permissions
2. **Bedrock Access**: Request access to the following models:
   - Anthropic Claude 3.5 Sonnet v2
3. **Bedrock Agent Service Role**: Create an IAM role for Bedrock Agent service

### Create Bedrock Agent Service Role

```bash
# Create trust policy
cat > bedrock-agent-trust-policy.json << EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "bedrock.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF

# Create the role
aws iam create-role \
    --role-name AmazonBedrockExecutionRoleForAgents_DMTA \
    --assume-role-policy-document file://bedrock-agent-trust-policy.json

# Attach the required policy
aws iam attach-role-policy \
    --role-name AmazonBedrockExecutionRoleForAgents_DMTA \
    --policy-arn arn:aws:iam::aws:policy/AmazonBedrockFullAccess

# Get the role ARN (you'll need this for deployment)
aws iam get-role \
    --role-name AmazonBedrockExecutionRoleForAgents_DMTA \
    --query 'Role.Arn' \
    --output text
```

## Deployment

1. **Set Environment Variable**:
   ```bash
   export BEDROCK_AGENT_SERVICE_ROLE_ARN="arn:aws:iam::YOUR-ACCOUNT-ID:role/AmazonBedrockExecutionRoleForAgents_DMTA"
   ```

2. **Deploy the Stack**:
   ```bash
   ./deploy.sh
   ```

   Or manually using AWS CLI:
   ```bash
   aws cloudformation deploy \
       --template-file dmta-orchestration-agent-cfn.yaml \
       --stack-name dmta-orchestration-agent \
       --region us-west-2 \
       --capabilities CAPABILITY_NAMED_IAM \
       --parameter-overrides \
           BedrockAgentServiceRoleArn=$BEDROCK_AGENT_SERVICE_ROLE_ARN \
           ProjectName=DMTA-Orchestration
   ```

## Architecture

The solution creates:

- **S3 Bucket**: For storing experimental data and project plans (auto-generated unique name)
- **DynamoDB Tables**: For tracking projects, cycles, and variants
- **Lambda Functions**: Four functions for each DMTA phase
- **Bedrock Agent**: Orchestrates the DMTA workflow
- **IAM Roles**: Appropriate permissions for all components

### Data Storage Structure

#### S3 Bucket Organization
```
s3://dmta-orchestration-agent-{region}-{account-id}/
└── projects/
    └── {project_id}/
        ├── project_plan.md                     # Comprehensive project plan (Markdown)
        ├── experiments/
        │   └── {experiment_id}/
        │       └── results.json                 # SPR binding assay results
        └── analysis/
            └── {analysis_id}/
                └── detailed_results.json       # GP model analysis results
```

#### DynamoDB Tables
- **ProjectTable**: Project metadata and status tracking (PK: project_id)
- **CycleTable**: DMTA cycle information and progress (PK: project_id, SK: cycle_number)
- **VariantTable**: Nanobody variant designs and results (PK: project_id, SK: variant_id)

## Usage

After deployment, you can interact with the agent through:

1. **AWS Console**: Navigate to Amazon Bedrock > Agents
2. **AWS CLI**: Use the Bedrock Runtime API
3. **SDK**: Integrate with your applications

### Data Management

#### Project Plan Documents
Each project generates a comprehensive plan document stored in S3:
- **Location**: `s3://bucket/projects/{project_id}/project_plan.json`
- **Contents**: 
  - Project overview and objectives
  - Experimental design and methodology
  - Knowledge base insights
  - Timeline and deliverables
  - Risk assessment and mitigation strategies

#### Experimental Data
SPR binding assay results are stored under each project:
- **Location**: `s3://bucket/projects/{project_id}/experiments/{experiment_id}/results.json`
- **Contents**:
  - Expression data (yield, purity, aggregation)
  - SPR binding kinetics (ka, kd, KD, Rmax)
  - Quality assessment scores
  - Assay conditions and parameters

#### Analysis Results
Gaussian Process modeling and optimization analysis:
- **Location**: `s3://bucket/projects/{project_id}/analysis/{analysis_id}/detailed_results.json`
- **Contents**:
  - Cycle summary and statistics
  - GP model performance metrics
  - Optimization progress assessment
  - Next cycle recommendations

### Example Conversation

```
User: "I want to optimize Cablivi for better vWF binding affinity. Can you help me plan a DMTA project?"

Agent: "I'll help you create a DMTA optimization project for Cablivi. Let me start by planning the project..."
[Calls plan_project function]

Agent: "Project created! Now let's design the first set of variants..."
[Calls design_variants function]
```

## Resource Naming

All resources are automatically named with unique identifiers to avoid conflicts:

- S3 Bucket: AWS auto-generates unique name
- DynamoDB Tables: `{StackName}-{TableType}`
- Lambda Functions: `{StackName}-{FunctionName}`
- IAM Role: `{StackName}-Lambda-Role`

## Data Access and Management

### Accessing Stored Data

#### List All Projects
```bash
aws s3 ls s3://dmta-orchestration-agent-{region}-{account-id}/projects/
```

#### List Project Contents
```bash
aws s3 ls s3://dmta-orchestration-agent-{region}-{account-id}/projects/{project_id}/ --recursive
```

#### Download Project Plan
```bash
aws s3 cp s3://dmta-orchestration-agent-{region}-{account-id}/projects/{project_id}/project_plan.json ./
```

#### Download All Project Data
```bash
aws s3 sync s3://dmta-orchestration-agent-{region}-{account-id}/projects/{project_id}/ ./project_data/
```

#### Query DynamoDB Tables
```bash
# List all projects
aws dynamodb scan --table-name dmta-orchestration-agent-ProjectTable

# Get specific project
aws dynamodb get-item --table-name dmta-orchestration-agent-ProjectTable --key '{"project_id":{"S":"your-project-id"}}'
```

### File Formats

#### Project Plan Document Structure
```json
{
  "project_overview": {
    "project_id": "uuid",
    "title": "DMTA Optimization of Cablivi",
    "objective": "Improve vWF binding affinity",
    "target_kd_nm": 0.5,
    "timeline_weeks": 8
  },
  "experimental_design": {
    "active_learning_strategy": "Expected Improvement (EI)",
    "cycles_planned": 3,
    "variants_per_cycle": 8
  },
  "methodology": {
    "phase_1_design": {...},
    "phase_2_make": {...},
    "phase_3_test": {...},
    "phase_4_analyze": {...}
  },
  "timeline": {...}
}
```

## Cleanup

To remove all resources:

```bash
aws cloudformation delete-stack \
    --stack-name dmta-orchestration-agent \
    --region us-west-2
```

**Note**: S3 bucket contents are not automatically deleted. To remove all data:

```bash
aws s3 rm s3://dmta-orchestration-agent-{region}-{account-id}/ --recursive
```

## Security Considerations

- All S3 buckets have public access blocked
- DynamoDB tables use encryption at rest
- Lambda functions follow least privilege principle
- IAM roles have minimal required permissions

## Cost Considerations

This solution uses:
- Amazon Bedrock (pay-per-use)
- AWS Lambda (pay-per-invocation)
- DynamoDB (on-demand billing)
- S3 (pay-per-use)

Estimated cost for typical usage: $10-50/month depending on usage patterns.

## Troubleshooting

### Common Issues

1. **Stack Creation Failed**: Check that the Bedrock Agent Service Role ARN is correct
2. **Permission Denied**: Ensure your AWS credentials have sufficient permissions
3. **Model Access**: Verify you have access to Claude 3.5 Sonnet v2 in Bedrock

### Getting Help

Check CloudFormation events for detailed error messages:

```bash
aws cloudformation describe-stack-events \
    --stack-name dmta-orchestration-agent \
    --region us-west-2
```

## License

This project is licensed under the MIT-0 License.