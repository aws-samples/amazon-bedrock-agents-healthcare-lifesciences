# DMTA Orchestration Agent

## 1. Summary

This agent orchestrates Design-Make-Test-Analyze (DMTA) cycles for Cablivi (Caplacizumab) optimization. It coordinates experimental planning, nanobody engineering, expression/testing, and results analysis to improve vWF binding affinity through iterative active learning cycles.

## 2. Agent Details

### 2.1. Instructions

You are an expert nanobody engineer specializing in DMTA cycle orchestration for Cablivi (Caplacizumab) optimization. Help users plan, execute, and analyze iterative experimental cycles to improve vWF A1 domain binding affinity through active learning approaches.
>
> You have access to the following tools:
>
> - plan_project: Create initial project setup and active learning strategy
> - design_variants: Generate nanobody variants using acquisition functions (EI/UCB)
> - make_test: Execute expression and SPR binding assays with FactorX simulation
> - analyze_results: Analyze results using Gaussian Process modeling and recommend next steps
>
> DMTA Workflow Process
>
> 1. Begin by understanding the optimization objectives (improve vWF binding affinity for Cablivi)
> 2. Use plan_project to create initial project setup and active learning strategy
> 3. For each cycle, execute phases sequentially with user confirmation:
>    - Use design_variants to select nanobody variants using acquisition functions
>    - Use make_test to simulate expression and SPR binding assays with FactorX data
>    - Use analyze_results to update Gaussian Process model and assess progress
> 4. Ask user permission before starting each phase: "Design phase completed. Would you like to start the Make phase?"
> 5. Continue cycles until convergence criteria met or optimal nanobody variants found
> 6. Provide final optimization summary with best candidates
>
> Response Guidelines
>
> - Execute phases sequentially with user confirmation between each phase
> - Provide clear phase completion messages: "[Phase] completed. Would you like to start the [Next Phase]?"
> - Generate realistic FactorX dummy data for Make and Test phases
> - Update Gaussian Process models with new experimental data
> - Track optimization progress and convergence criteria
- Highlight best nanobody variants and binding improvements achieved
> - Recommend next cycle strategies based on active learning principles

### 2.2. Tools

```json
{
  name: "plan_project",
  description: "Create initial Cablivi optimization project plan with active learning strategy",
  inputSchema: {
    type: "object",
    properties: {
      target_nanobody: { type: "string", description: "Starting nanobody (Cablivi/Caplacizumab)"},
      optimization_objective: { type: "string", description: "vWF binding affinity improvement objective"},
      target_kd: { type: "number", description: "Target KD value in nM (default: 1.0)"},
      timeline_weeks: { type: "integer", description: "Project timeline in weeks (default: 8)"},
      knowledge_base_query: { type: "string", description: "Query for similar nanobody optimization experiments"}
    },
    required: ["target_nanobody", "optimization_objective"]
  }
},
{
  name: "design_variants",
  description: "Generate nanobody variants using active learning acquisition functions",
  inputSchema: {
    type: "object",
    properties: {
      parent_nanobody: { type: "string", description: "Base nanobody sequence"},
      cycle_number: { type: "integer", description: "Current DMTA cycle number"},
      acquisition_function: { type: "string", enum: ["EI", "UCB", "hybrid"], description: "Active learning strategy"},
      num_variants: { type: "integer", description: "Number of variants to generate (default: 8)"},
      previous_results: { type: "string", description: "Historical binding data for GP model"}
    },
    required: ["parent_nanobody", "cycle_number"]
  }
},
{
  name: "make_test",
  description: "Execute nanobody expression and SPR binding assays with FactorX simulation",
  inputSchema: {
    type: "object",
    properties: {
      variant_list: { type: "array", items: { type: "string" }, description: "Nanobody variants to express and test"},
      assay_type: { type: "string", description: "SPR binding assay configuration"},
      target_protein: { type: "string", description: "Target protein (vWF A1 domain)"},
      quality_controls: { type: "object", description: "Expression and binding QC parameters"}
    },
    required: ["variant_list"]
  }
},
{
  name: "analyze_results",
  description: "Analyze SPR binding results using Gaussian Process modeling and recommend next cycle strategy",
  inputSchema: {
    type: "object",
    properties: {
      binding_data: { type: "string", description: "SPR binding results from make-test phase"},
      cycle_number: { type: "integer", description: "Current cycle number"},
      previous_cycles: { type: "string", description: "Historical optimization data"},
      convergence_criteria: { type: "object", description: "Optimization targets and thresholds"},
      target_kd: { type: "number", description: "Target binding affinity KD value in nM"}
    },
    required: ["binding_data", "cycle_number"]
  }
}
```

## 3. Installation

1. Verify your AWS credentials are available in your current session:

```bash
aws sts get-caller-identity
```

2. Navigate to the `DMTA-orchestration-agent` folder:

```bash
cd agents_catalog/23-DMTA-orchestration-agent
```

3. Deploy the agent using the provided script:

```bash
# Set required environment variables
export BUCKET_NAME="<YOUR_S3_BUCKET_NAME>"        # S3 bucket for Lambda function code
export REGION="<YOUR_REGION>"                     # AWS region for deployment
export BEDROCK_AGENT_SERVICE_ROLE_ARN="<YOUR_BEDROCK_AGENT_ROLE_ARN>"  # IAM role for Bedrock Agent

# Run the deployment script
./deploy.sh
```

The script will:
- Package Lambda function code and upload to S3
- Deploy the CloudFormation stack with all required resources
- Create the Bedrock Agent with configured action groups

Required Resources:
- An S3 bucket in the target region
- An IAM role for Bedrock Agent with appropriate permissions
- AWS CLI configured with credentials having necessary permissions

## 4. Usage Examples

### Example 1: Complete DMTA Cycle Planning
```
Input: "Plan a DMTA cycle to optimize Cablivi (Caplacizumab) for improved vWF binding affinity"

Output:
DMTA Cycle Plan for Cablivi Optimization
Cycle: 1
Timeline: 6 weeks
Objectives: Improve vWF A1 binding (target KD < 1 nM vs current 3.2 nM)

Phase 1 - Design (Week 1-2):
- CDR sequence analysis of existing nanobody variants
- Generate 8 nanobody variants using active learning
- Prioritize based on predicted binding affinity

Phase 2 - Make (Week 3-4):
- Express top 8 nanobody variants
- Purification and characterization
- Quality assessment

Phase 3 - Test (Week 5):
- SPR binding assays vs vWF A1 domain
- Kinetic analysis (kon, koff, KD)
- Binding specificity assessment

Phase 4 - Analyze (Week 6):
- Gaussian Process model update
- Next cycle recommendations
- Lead variant selection
```

### Example 2: Nanobody Design
```
Input: "Design nanobody variants of Caplacizumab with improved vWF binding affinity"

Output:
Nanobody Design Results for Cablivi Optimization

Base Structure: Caplacizumab (ALX-0081)
Design Strategy: CDR optimization with binding affinity focus

Top 5 Variants:
1. Variant N1-001: CDR3 S101A mutation
   - Predicted KD: 2.1 nM (vs 3.2 nM parent)
   - Expected Improvement score: 0.89
   - Expression feasibility: High

2. Variant N1-002: CDR1 G26D mutation
   - Predicted KD: 2.8 nM
   - Expected Improvement score: 0.82
   - Expression feasibility: High

[Additional variants...]

Rationale: Mutations target vWF A1 binding interface while preserving nanobody stability and expression.
```

### Example 3: Results Analysis
```
Input: "Analyze the experimental results from DMTA cycle 2 and recommend next steps"

Output:
DMTA Cycle 2 Analysis Results

Experimental Summary:
- 8 nanobody variants expressed and tested
- Binding affinity range: 0.8-2.0 nM
- Best variant: N2-008 (KD: 0.8 nM)
- Lead variant: N2-003 (KD: 0.9 nM, excellent stability)

SAR Insights:
- CDR3 S101A provides foundation for improvement
- Y100H mutation enhances binding further
- Framework mutations maintain stability

Cycle 3 Recommendations:
1. Optimize N2-008 with complementary CDR mutations
2. Explore triple mutations combining best features
3. Include stability profiling for top 3 variants
4. Target: KD < 0.5 nM, maintain expression levels
```

## 5. Troubleshooting

### Common Issues and Solutions

#### Issue: "Experimental Plan Validation Error"
**Possible Causes:**
- Insufficient resource allocation
- Unrealistic timeline constraints
- Missing required parameters

**Solutions:**
- Review resource requirements and adjust allocation
- Extend timeline for complex syntheses
- Provide complete optimization objectives

#### Issue: "Molecular Design Generation Failed"
**Possible Causes:**
- Invalid starting structure format
- Conflicting property requirements
- Limited chemical space

**Solutions:**
- Verify SMILES format or compound name
- Adjust target property ranges
- Consider alternative design strategies

#### Issue: "Experiment Execution Timeout"
**Possible Causes:**
- Complex synthetic routes
- Laboratory resource conflicts
- Automation system issues

**Solutions:**
- Simplify synthetic approaches
- Adjust priority levels and scheduling
- Implement manual backup procedures

### Performance Tips

- Start with focused optimization objectives
- Use historical SAR data when available
- Balance automation with manual oversight
- Plan for iterative refinement cycles
- Monitor resource utilization continuously

## 6. DMTA Best Practices

### Cycle Planning Guidelines

**Objective Setting:**
- Define clear, measurable optimization goals
- Prioritize objectives based on project needs
- Consider trade-offs between properties
- Set realistic timelines and milestones

**Resource Management:**
- Allocate sufficient synthetic chemistry resources
- Plan for analytical characterization time
- Reserve assay capacity for testing
- Include buffer time for unexpected challenges

### Design Strategy Recommendations

**Structure-Activity Relationships:**
- Leverage existing SAR knowledge
- Focus on validated chemical series
- Consider synthetic accessibility
- Balance novelty with risk

**Property Optimization:**
- Use multi-parameter optimization approaches
- Consider ADMET properties early
- Plan for selectivity assessment
- Include physicochemical property analysis

### Experimental Execution

**Quality Control:**
- Implement analytical verification steps
- Use appropriate controls and standards
- Document experimental conditions
- Validate assay performance

**Data Management:**
- Maintain comprehensive experimental records
- Use standardized data formats
- Implement version control for protocols
- Enable data sharing across cycles

## 7. Integration with Laboratory Systems

### Supported Data Formats

- **Chemical Structures**: SMILES, SDF, MOL files
- **Experimental Data**: CSV, Excel, JSON formats
- **Assay Results**: Standardized plate reader formats
- **Analytical Data**: LC-MS, NMR integration

### API Integration Points

- **LIMS Integration**: Laboratory information management systems
- **ELN Connectivity**: Electronic laboratory notebooks
- **Compound Registration**: Chemical inventory systems
- **Assay Platforms**: High-throughput screening systems

### Workflow Automation

- **Protocol Generation**: Automated experimental procedure creation
- **Sample Tracking**: Barcode and RFID integration
- **Result Processing**: Automated data analysis pipelines
- **Report Generation**: Standardized output formats