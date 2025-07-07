# DMTA Orchestration Agent - System Design

## Architecture Overview

The DMTA Orchestration Agent implements an active learning approach for FactorX optimization, using Amazon Bedrock Agent with two specialized Lambda functions for planning and analysis phases.

```
┌─────────────────────────────────────────────────────────────┐
│                 Chat Interface                              │
│              (AWS Console / API)                            │
└─────────────────────┬───────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────┐
│              Amazon Bedrock Agent                           │
│            (Claude 3.5 Sonnet v2)                          │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐    │
│  │         Active Learning Orchestration              │    │
│  │  • Chat conversation management                     │    │
│  │  • DMTA workflow coordination                       │    │
│  │  • FactorX optimization tracking                    │    │
│  │  • Gaussian Process model updates                   │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────┬───────────────────────────────────────┘
                      │
        ┌─────────────┼─────────────┼─────────────┐
        │             │             │             │
        ▼             ▼             ▼             ▼
┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
│    Plan     │ │   Design    │ │ Make + Test │ │   Analyze   │
│   Project   │ │  Variants   │ │ Execution   │ │  Results    │
│             │ │             │ │             │ │             │
│ • Strategy  │ │ • CDR Muts  │ │ • Express   │ │ • GP Model  │
│ • Timeline  │ │ • EI/UCB    │ │ • SPR Test  │ │ • Analysis  │
│ • Resources │ │ • Ranking   │ │ • FactorX   │ │ • Next Rec  │
│             │ │             │ │             │ │             │
│ Lambda      │ │ Lambda      │ │ Lambda      │ │ Lambda      │
│ Function    │ │ Function    │ │ Function    │ │ Function    │
└─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘
        │             │             │             │
        └─────────────┼─────────────┼─────────────┘
                      │
        ┌─────────────▼─────────────┐
        │      Session Memory      │
        │                          │
        │  • Cycle History         │
        │  • GP Model State        │
        │  • Compound Library      │
        │  • Optimization Progress │
        └──────────────────────────┘
```

## Component Design

### 1. Amazon Bedrock Agent (Orchestrator)

**Purpose**: Active learning workflow coordination and chat interface
**Model**: Claude 3.5 Sonnet v2
**Responsibilities**:
- Manage chat conversation flow for DMTA optimization
- Coordinate active learning cycles with acquisition functions
- Track FactorX optimization progress and convergence
- Generate scientific responses with Gaussian Process insights
- Handle multi-cycle optimization workflow

**Key Features**:
- Chat-based DMTA workflow management
- Active learning strategy implementation
- FactorX optimization tracking
- Gaussian Process model coordination
- Convergence detection and reporting

### 2. Action Group: Plan Project

**Lambda Function**: `plan-project/lambda_function.py`
**Purpose**: Initial project setup and strategy definition
**Input Parameters**:
- `target_nanobody`: Starting nanobody (Cablivi/Caplacizumab)
- `optimization_objective`: vWF binding affinity improvement
- `target_value`: Target KD value (e.g., < 1 nM)
- `timeline_weeks`: Project timeline
- `initial_data`: Historical binding data

**Core Algorithms**:
```python
def create_project_plan(nanobody, objective, target, timeline):
    """
    Generate Cablivi optimization project plan
    """
    # 1. Analyze current Cablivi performance
    baseline_analysis = analyze_baseline_performance(nanobody)
    
    # 2. Define optimization strategy
    strategy = define_active_learning_strategy(objective, target)
    
    # 3. Estimate resource requirements
    resources = estimate_nanobody_resources(timeline)
    
    # 4. Create cycle framework
    cycle_plan = create_dmta_framework(strategy)
    
    return {
        'project_id': generate_project_id(),
        'baseline': baseline_analysis,
        'strategy': strategy,
        'timeline': timeline,
        'resources': resources,
        'cycle_framework': cycle_plan
    }
```

**Output Format**:
- Project overview and objectives
- Active learning strategy definition
- Resource allocation and timeline
- DMTA cycle framework

### 3. Action Group: Design Variants

**Lambda Function**: `design-variants/lambda_function.py`
**Purpose**: Nanobody variant design using active learning
**Input Parameters**:
- `parent_nanobody`: Base nanobody sequence
- `cycle_number`: Current DMTA cycle
- `acquisition_function`: EI, UCB, or hybrid
- `num_variants`: Number of variants to generate
- `previous_results`: Historical binding data for GP model

**Core Algorithms**:
```python
def design_nanobody_variants(parent, cycle, acq_func, num_variants, history):
    """
    Generate nanobody variants using active learning
    """
    # 1. Update Gaussian Process model
    gp_model = update_gp_model(history)
    
    # 2. Identify CDR mutation sites
    cdr_sites = identify_cdr_sites(parent)
    
    # 3. Generate candidate mutations
    candidates = generate_cdr_mutations(cdr_sites)
    
    # 4. Apply acquisition function
    if acq_func == 'EI':
        scores = expected_improvement(candidates, gp_model)
    elif acq_func == 'UCB':
        scores = upper_confidence_bound(candidates, gp_model)
    
    # 5. Select top variants
    selected = select_top_variants(candidates, scores, num_variants)
    
    return {
        'variants': selected,
        'predictions': predict_binding_affinity(selected, gp_model),
        'acquisition_scores': scores
    }
```

**Design Strategies**:
- **Expected Improvement (EI)**: Exploit promising regions
- **Upper Confidence Bound (UCB)**: Explore uncertain areas
- **CDR Optimization**: Focus on complementarity-determining regions
- **Conservative Mutations**: Maintain nanobody stability

### 4. Action Group: Make and Test

**Lambda Function**: `make-test/lambda_function.py`
**Purpose**: Nanobody expression and SPR binding assays with FactorX simulation
**Input Parameters**:
- `variant_list`: Nanobody variants to express and test
- `assay_type`: SPR binding assay configuration
- `target_protein`: vWF A1 domain
- `quality_controls`: Expression and binding QC parameters

**Workflow Management**:
```python
def execute_make_test(variants, assay_type, target, qc_params):
    """
    Simulate nanobody expression and SPR binding assays
    """
    # 1. Simulate expression (Make phase)
    expression_results = simulate_expression(variants)
    
    # 2. Generate FactorX expression data
    expression_data = generate_expression_factorx_data(variants)
    
    # 3. Simulate SPR binding assays (Test phase)
    binding_results = simulate_spr_assays(variants, target)
    
    # 4. Generate FactorX binding data
    binding_data = generate_binding_factorx_data(variants, expression_data)
    
    # 5. Quality control assessment
    qc_results = assess_quality_control(expression_data, binding_data, qc_params)
    
    return {
        'expression_results': expression_data,
        'binding_results': binding_data,
        'qc_assessment': qc_results,
        'ready_for_analysis': True
    }
```

**FactorX Data Generation**:
- Realistic expression yields and purity
- SPR binding kinetics (kon, koff, KD)
- Experimental variance and noise
- Correlation with predicted values

### 5. Action Group: Analyze Results

**Lambda Function**: `analyze-results/lambda_function.py`
**Purpose**: Gaussian Process analysis and next cycle recommendations
**Input Parameters**:
- `binding_data`: SPR binding results from make-test phase
- `cycle_number`: Current cycle number
- `previous_cycles`: Historical optimization data
- `convergence_criteria`: Optimization targets and thresholds
- `target_kd`: Target binding affinity value

**Analysis Pipeline**:
```python
def analyze_binding_results(binding_data, cycle_num, history, criteria, target):
    """
    Analyze SPR results and recommend next cycle strategy
    """
    # 1. Data preprocessing and validation
    cleaned_data = preprocess_binding_data(binding_data)
    
    # 2. Update Gaussian Process model
    updated_gp = update_gaussian_process(cleaned_data, history)
    
    # 3. Identify best variants
    best_variants = identify_top_performers(cleaned_data, target)
    
    # 4. Assess convergence
    convergence = assess_convergence(cleaned_data, history, criteria)
    
    # 5. Generate next cycle recommendations
    if not convergence['converged']:
        next_strategy = recommend_next_cycle(updated_gp, best_variants)
    else:
        next_strategy = finalize_optimization(best_variants)
    
    # 6. Calculate improvement metrics
    improvement = calculate_improvement_metrics(cleaned_data, history)
    
    return {
        'best_variants': best_variants,
        'model_performance': updated_gp.performance_metrics,
        'convergence_status': convergence,
        'improvement_metrics': improvement,
        'next_cycle_strategy': next_strategy,
        'recommendations': generate_detailed_recommendations(next_strategy)
    }
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

**Sample Record**:
```json
{
  "project_id": "cablivi-opt-001",
  "target_nanobody": "Caplacizumab",
  "optimization_objective": "vWF binding affinity improvement",
  "target_kd": 1.0,
  "baseline_kd": 3.2,
  "status": "in_progress",
  "created_at": "2025-01-15T10:00:00Z",
  "current_cycle": 2,
  "best_variant": {
    "variant_id": "N2-008",
    "kd_value": 0.8
  }
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

**Sample Record**:
```json
{
  "project_id": "cablivi-opt-001",
  "cycle_number": 1,
  "status": "completed",
  "variants_tested": 8,
  "best_kd": 1.8,
  "gp_model_r2": 0.74,
  "acquisition_function": "EI",
  "completed_at": "2025-01-15T14:00:00Z"
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

**Sample Record**:
```json
{
  "variant_id": "N1-001",
  "project_id": "cablivi-opt-001",
  "cycle_number": 1,
  "mutations": ["S101A"],
  "predicted_kd": 2.1,
  "actual_kd": 1.8,
  "expression_yield": 12.4,
  "status": "tested"
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
│       │       │   └── assay_results/
│       │       └── analysis/
│       │           ├── sar_analysis.json
│       │           └── visualizations/
│       └── reports/
│           ├── cycle_summaries/
│           └── final_reports/
└── templates/
    ├── protocols/
    ├── analysis_scripts/
    └── visualization_templates/
```

## Security Architecture

### 1. IAM Roles and Policies

#### Bedrock Agent Role
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "lambda:InvokeFunction"
      ],
      "Resource": [
        "arn:aws:lambda:*:*:function:DMTA-*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeModel"
      ],
      "Resource": [
        "arn:aws:bedrock:*::foundation-model/anthropic.claude-3-5-sonnet-*"
      ]
    }
  ]
}
```

#### Lambda Execution Role
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "dynamodb:GetItem",
        "dynamodb:PutItem",
        "dynamodb:UpdateItem",
        "dynamodb:Query"
      ],
      "Resource": [
        "arn:aws:dynamodb:*:*:table/DMTAWorkflowState",
        "arn:aws:dynamodb:*:*:table/CompoundRegistry"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:PutObject"
      ],
      "Resource": [
        "arn:aws:s3:::dmta-experimental-data/*"
      ]
    }
  ]
}
```

### 2. Data Protection

- **Encryption at Rest**: All DynamoDB tables and S3 objects encrypted with AWS KMS
- **Encryption in Transit**: TLS 1.2+ for all API communications
- **Access Control**: Fine-grained IAM policies with least privilege principle
- **Audit Logging**: CloudTrail logging for all API calls and data access

## Performance Considerations

### 1. Lambda Function Optimization

- **Memory Allocation**: 512MB-1GB based on computational requirements
- **Timeout Settings**: 5-15 minutes depending on function complexity
- **Cold Start Mitigation**: Provisioned concurrency for critical functions
- **Connection Pooling**: Reuse database connections across invocations

### 2. Data Access Patterns

- **DynamoDB**: Single-table design with GSIs for query optimization
- **S3**: Partitioned storage with lifecycle policies for cost optimization
- **Caching**: In-memory caching for frequently accessed data
- **Batch Processing**: Bulk operations for large datasets

### 3. Scalability Design

- **Horizontal Scaling**: Lambda auto-scaling based on demand
- **Database Scaling**: DynamoDB on-demand billing for variable workloads
- **Storage Scaling**: S3 automatic scaling with intelligent tiering
- **API Rate Limiting**: Throttling to prevent resource exhaustion

## Monitoring and Observability

### 1. CloudWatch Metrics

- **Function Duration**: Lambda execution times
- **Error Rates**: Function failure percentages
- **Throughput**: Requests per second
- **Resource Utilization**: Memory and CPU usage

### 2. Custom Metrics

- **DMTA Cycle Completion Time**: End-to-end cycle duration
- **Design Success Rate**: Percentage of successful molecular designs
- **Experiment Success Rate**: Laboratory execution success metrics
- **Analysis Accuracy**: Prediction vs. actual result correlation

### 3. Alerting Strategy

- **Error Alerts**: Immediate notification for function failures
- **Performance Alerts**: Warnings for degraded performance
- **Business Metrics**: Alerts for unusual DMTA cycle patterns
- **Resource Alerts**: Notifications for resource limit approaches

## Deployment Architecture

### 1. Infrastructure as Code

- **CloudFormation**: Complete infrastructure definition
- **Parameter Management**: Environment-specific configurations
- **Stack Dependencies**: Proper resource ordering and dependencies
- **Rollback Strategy**: Automated rollback on deployment failures

### 2. CI/CD Pipeline

- **Source Control**: Git-based version control
- **Build Process**: Automated testing and packaging
- **Deployment Stages**: Dev → Test → Production progression
- **Quality Gates**: Automated testing and approval processes

### 3. Environment Management

- **Development**: Isolated environment for feature development
- **Testing**: Staging environment for integration testing
- **Production**: Live environment with full monitoring
- **Disaster Recovery**: Cross-region backup and recovery procedures