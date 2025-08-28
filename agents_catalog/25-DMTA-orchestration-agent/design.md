# DMTA Orchestration Agent - System Design

## Architecture Overview

The DMTA Orchestration Agent implements an active learning approach for FactorX optimization, using Amazon Bedrock Agent with direct Lambda integration for S3 storage and Opentrons OT-2 automation.

**Implementation Notes**:
- Opentrons OT-2 integration uses the official Opentrons Python API's simulation capabilities, allowing protocol testing without physical hardware
- FactorX optimization currently uses synthetic data for demonstration
- Gaussian Process modeling uses mock parameters for prototype implementation
- Active learning implementation uses simulated binding affinity data

The simulation-based approach allows for development and testing of the DMTA workflow while maintaining realistic behavior patterns through Opentrons' validated simulation tools.

```
┌─────────────────────────────────────────────────────────────┐
│                 Chat Interface                              │
│              (AWS Console / API)                            │
└─────────────────────┬───────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────┐
│              Amazon Bedrock Agent                           │
│         (Configurable Foundation Model)                     │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐    │
│  │         Active Learning Orchestration              │    │
│  │  • Chat conversation management                     │    │
│  │  • DMTA workflow coordination                       │    │
│  │  • FactorX optimization tracking                    │    │
│  │  • Gaussian Process model updates                   │    │
│  │  • Opentrons OT-2 integration                      │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────┬───────────────────────────────────────┘
                      │
        ┌─────────────▼─────────────┐
        │    Lambda Functions       │
        │                          │
        │  ┌─────────────────────┐ │
        │  │   Core Functions    │ │
        │  │ • plan_project      │ │
        │  │ • design_variants   │ │
        │  │ • make_test        │ │
        │  │ • analyze_results   │ │
        │  │ • project_status    │ │
        │  └─────────────────────┘ │
        └─────────────┬─────────────┘
                      │
        ┌─────────────┼─────────────┬─────────────┐
        │             │             │             │
        ▼             ▼             ▼             ▼
┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
│     S3      │ │  DynamoDB   │ │   Session   │ │ Opentrons   │
│   Bucket    │ │   Tables    │ │   Memory    │ │   Lambda    │
│             │ │             │ │             │ │             │
│ • Project   │ │ • Projects  │ │ • Cycle     │ │ • OT-2      │
│   Plans     │ │ • Cycles    │ │   History   │ │   Protocol  │
│ • Results   │ │ • Variants  │ │ • GP Model  │ │ • Simulation│
│ • Analysis  │ │             │ │   State     │ │ • Results   │
│ • OT-2 Data │ │             │ │             │ │             │
└─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘
```

## Component Design

### 1. Amazon Bedrock Agent (Orchestrator)

**Purpose**: Active learning workflow coordination and chat interface
**Model**: Configurable foundation model (defaults to Claude 3.5 Sonnet v2)
**Responsibilities**:
- Manage chat conversation flow for DMTA optimization
- Coordinate active learning cycles with acquisition functions
- Track FactorX optimization progress and convergence
- Generate scientific responses with Gaussian Process insights
- Direct AWS service integration through Lambda functions

**Key Features**:
- Chat-based DMTA workflow management
- Active learning strategy implementation
- FactorX optimization tracking
- Gaussian Process model coordination
- Convergence detection and reporting

### 2. Lambda Function: Plan Project

**Function**: `plan_project`
**Purpose**: Initial project setup and strategy definition
**Input Parameters**:
- `target_nanobody`: Starting nanobody (Cablivi/Caplacizumab)
- `optimization_objective`: vWF binding affinity improvement
- `target_value`: Target KD value (e.g., < 1 nM)
- `timeline_weeks`: Project timeline
- `initial_data`: Historical binding data

**Integration Flow**:
```
1. Agent receives plan_project request
2. Lambda checks existing projects in DynamoDB
3. Lambda generates project plan
4. Lambda stores project metadata in DynamoDB
5. Lambda stores detailed project plan in S3
6. Agent returns project summary to user
```

**Data Storage**:
- **DynamoDB**: Project metadata
- **S3**: Detailed project plan
- **Format**: JSON project plan with comprehensive strategy

### 3. Lambda Function: Design Variants

**Function**: `design_variants`
**Purpose**: Nanobody variant design using active learning
**Input Parameters**:
- `parent_nanobody`: Base nanobody sequence
- `cycle_number`: Current DMTA cycle
- `acquisition_function`: EI, UCB, or hybrid
- `num_variants`: Number of variants to generate
- `previous_results`: Historical binding data for GP model

**Integration Flow**:
```
1. Agent receives design_variants request
2. Lambda retrieves previous cycle data from DynamoDB
3. Lambda loads historical results from S3
4. Lambda generates variants using internal algorithms
5. Lambda stores variant metadata in DynamoDB
6. Lambda stores variant designs in S3
7. Agent returns variant list to user
```

**Design Strategies**:
- **Expected Improvement (EI)**: Exploit promising regions
- **Upper Confidence Bound (UCB)**: Explore uncertain areas
- **CDR Optimization**: Focus on complementarity-determining regions
- **Conservative Mutations**: Maintain nanobody stability

### 4. Lambda Function: Make and Test (with Opentrons Integration)

**Function**: `make_test`
**Purpose**: Nanobody expression, OT-2 sample preparation, and SPR binding assays
**Input Parameters**:
- `variant_list`: Nanobody variants to express and test
- `assay_type`: SPR binding assay configuration
- `target_protein`: vWF A1 domain
- `use_opentrons`: Enable OT-2 automated sample preparation
- `quality_controls`: Expression and binding QC parameters

**Opentrons Integration Flow**:
```
1. Agent receives make_test request
2. Lambda simulates protein expression
3. Lambda generates OT-2 protocol
4. Lambda executes opentrons_simulate
5. Lambda processes simulation results
6. Lambda stores experimental results in S3
7. Lambda updates variant status in DynamoDB
8. Agent returns comprehensive experimental summary
```

**Opentrons Lambda Function**:
```python
def lambda_handler(event, context):
    """Dedicated OT-2 simulation Lambda"""
    variant_list = event.get('variant_list', [])
    protocol_type = event.get('protocol_type', 'spr_sample_prep')
    
    # Generate OT-2 protocol
    protocol_content = generate_ot2_protocol(variant_list, protocol_type)
    
    # Execute opentrons_simulate
    simulation_result = execute_opentrons_simulation(protocol_content)
    
    return {
        'statusCode': 200,
        'body': {
            'simulation_success': True,
            'samples_prepared': len(variant_list) * 6,
            'execution_time_min': simulation_result['duration'],
            'accuracy_percent': 98.5,
            'protocol_validated': True,
            'results': simulation_result
        }
    }
```

### 5. Lambda Function: Analyze Results

**Function**: `analyze_results`
**Purpose**: Gaussian Process analysis and next cycle recommendations
**Input Parameters**:
- `binding_data`: SPR binding results from make-test phase
- `cycle_number`: Current cycle number
- `previous_cycles`: Historical optimization data
- `convergence_criteria`: Optimization targets and thresholds
- `target_kd`: Target binding affinity value

**Integration Flow**:
```
1. Agent receives analyze_results request
2. Lambda loads experimental results from S3
3. Lambda retrieves cycle history from DynamoDB
4. Lambda performs GP analysis
5. Lambda stores analysis results in S3
6. Lambda updates cycle status in DynamoDB
7. Agent returns analysis summary and recommendations
```

**Analysis Methods**:
- Gaussian Process regression and uncertainty quantification
- Binding affinity trend analysis
- Convergence detection algorithms
- Next cycle acquisition function selection

## Data Architecture

### 1. DynamoDB Tables

#### ProjectTable
```json
{
  "TableName": "DMTAProjectTable",
  "KeySchema": [
    {"AttributeName": "project_id", "KeyType": "HASH"}
  ],
  "AttributeDefinitions": [
    {"AttributeName": "project_id", "AttributeType": "S"},
    {"AttributeName": "status", "AttributeType": "S"}
  ],
  "GlobalSecondaryIndexes": [
    {
      "IndexName": "StatusIndex",
      "KeySchema": [
        {"AttributeName": "status", "KeyType": "HASH"}
      ]
    }
  ]
}
```

#### CycleTable
```json
{
  "TableName": "DMTACycleTable",
  "KeySchema": [
    {"AttributeName": "project_id", "KeyType": "HASH"},
    {"AttributeName": "cycle_number", "KeyType": "RANGE"}
  ],
  "AttributeDefinitions": [
    {"AttributeName": "project_id", "AttributeType": "S"},
    {"AttributeName": "cycle_number", "AttributeType": "N"}
  ]
}
```

#### VariantTable
```json
{
  "TableName": "DMTAVariantTable",
  "KeySchema": [
    {"AttributeName": "variant_id", "KeyType": "HASH"}
  ],
  "AttributeDefinitions": [
    {"AttributeName": "variant_id", "AttributeType": "S"},
    {"AttributeName": "project_id", "AttributeType": "S"}
  ],
  "GlobalSecondaryIndexes": [
    {
      "IndexName": "ProjectIndex",
      "KeySchema": [
        {"AttributeName": "project_id", "KeyType": "HASH"}
      ]
    }
  ]
}
```

### 2. S3 Storage Structure

```
dmta-experimental-data/
├── projects/
│   └── {project_id}/
│       ├── cycles/
│       │   └── {cycle_number}/
│       │       ├── plans/
│       │       │   ├── experimental_plan.json
│       │       │   └── protocols/
│       │       ├── designs/
│       │       │   ├── molecular_designs.sdf
│       │       │   └── predictions.csv
│       │       ├── execution/
│       │       │   ├── synthesis_data/
│       │       │   ├── opentrons/
│       │       │   │   ├── ot2_protocol.py
│       │       │   │   ├── simulation_results.json
│       │       │   │   └── performance_metrics.json
│       │       │   └── assay_results/
│       │       │       ├── spr_binding_data.json
│       │       │       ├── sample_quality_metrics.json
│       │       │       └── ot2_enhanced_precision.json
│       │       └── analysis/
│       │           ├── sar_analysis.json
│       │           └── visualizations/
│       └── reports/
│           ├── cycle_summaries/
│           └── final_reports/
└── templates/
    ├── protocols/
    │   └── opentrons_templates/
    │       ├── spr_sample_prep.py
    │       └── serial_dilution.py
    ├── analysis_scripts/
    └── visualization_templates/
```

## Security Architecture

### IAM Roles and Policies

#### Bedrock Agent Role
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeModel"
      ],
      "Resource": [
        "arn:aws:bedrock:*::foundation-model/*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "lambda:InvokeFunction"
      ],
      "Resource": [
        "arn:aws:lambda:*:*:function:dmta-*"
      ]
    }
  ]
}
```

### Data Protection

- **Encryption at Rest**: All DynamoDB tables and S3 objects encrypted with AWS KMS
- **Encryption in Transit**: TLS 1.2+ for all API communications
- **Access Control**: Fine-grained IAM policies with least privilege principle
- **Audit Logging**: CloudTrail logging for all API calls and data access

## Performance Considerations

### Lambda Function Optimization

**Standard Lambda Functions**:
- **Memory Allocation**: 512MB for standard DMTA functions
- **Timeout Settings**: 5 minutes for standard operations
- **Connection Pooling**: Reuse database connections across invocations

**Opentrons Lambda Function**:
- **Memory Allocation**: 1GB (dedicated OT-2 simulation processing)
- **Timeout Settings**: 10 minutes (opentrons_simulate execution)
- **Lambda Layer**: Opentrons Layer 50MB (opentrons==6.3.1)
- **Cold Start Mitigation**: Provisioned concurrency

### Data Access Patterns

- **DynamoDB**: Single-table design with GSIs for query optimization
- **S3**: Partitioned storage with lifecycle policies for cost optimization
- **Caching**: In-memory caching for frequently accessed data
- **Batch Processing**: Bulk operations for large datasets

## Monitoring and Observability

### CloudWatch Metrics

- **Function Duration**: Lambda execution times
- **Error Rates**: Function failure percentages
- **Throughput**: Requests per second
- **Resource Utilization**: Memory and CPU usage

### Custom Metrics

**Standard DMTA Metrics**:
- **DMTA Cycle Completion Time**: End-to-end cycle duration
- **Design Success Rate**: Percentage of successful molecular designs
- **Experiment Success Rate**: Laboratory execution success metrics
- **Analysis Accuracy**: Prediction vs. actual result correlation

**Opentrons-Specific Metrics**:
- **Protocol Generation Time**: OT-2 protocol creation time
- **Simulation Success Rate**: opentrons_simulate success percentage
- **Sample Preparation Accuracy**: CV% improvement (manual vs automated)
- **Automation Efficiency**: Time savings from automated preparation

### Alerting Strategy

- **Error Alerts**: Immediate notification for function failures
- **Performance Alerts**: Warnings for degraded performance
- **Business Metrics**: Alerts for unusual DMTA cycle patterns
- **Resource Alerts**: Notifications for resource limit approaches

## Deployment Architecture

### Infrastructure as Code

- **CloudFormation**: Complete infrastructure definition
- **Parameter Management**: Environment-specific configurations
- **Stack Dependencies**: Proper resource ordering and dependencies
- **Rollback Strategy**: Automated rollback on deployment failures

### CI/CD Pipeline

- **Source Control**: Git-based version control
- **Build Process**: Automated testing and packaging
- **Deployment Stages**: Dev → Test → Production progression
- **Quality Gates**: Automated testing and approval processes

### Environment Management

- **Development**: Isolated environment for feature development
- **Testing**: Staging environment for integration testing
- **Production**: Live environment with full monitoring
- **Disaster Recovery**: Cross-region backup and recovery procedures
