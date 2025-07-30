# Requirements for DMTA Orchestration Agent

## Functional Requirements

### FR1: DMTA Cycle Planning
- Create experimental plans for Cablivi (Caplacizumab) optimization using active learning approach
- Support iterative DMTA cycles with acquisition function-based nanobody variant selection
- Generate structured protocols for expression and SPR binding assays
- Estimate timelines and resource requirements
- Track cycle progress and vWF binding optimization objectives

### FR2: Nanobody Design and Selection
- Generate nanobody variants using active learning acquisition functions
- Implement Expected Improvement (EI) and Upper Confidence Bound (UCB) strategies
- Support Gaussian Process modeling for binding affinity prediction
- Rank variants based on acquisition function scores
- Generate FactorX dummy data for expression/testing phases

### FR3: Automated Sample Preparation
- Generate Opentrons OT-2 protocols for SPR binding assay sample preparation
- Automated liquid handling for serial dilutions and buffer dispensing
- Support 6-point concentration curves for binding kinetics analysis
- Real-time protocol execution monitoring and progress tracking
- Integration with Lambda-based Make-Test workflow for seamless automation

### FR4: Results Analysis and Optimization
- Analyze SPR binding results using Gaussian Process regression
- Update models with new experimental data
- Identify optimal nanobody variants and convergence criteria
- Generate recommendations for next DMTA cycle
- Support vWF binding affinity optimization

## Non-Functional Requirements

### NFR1: Performance
- DMTA cycle planning should complete within 5 minutes
- Molecular design calculations should complete within 10 minutes
- Real-time experiment monitoring with <30 second updates
- Analysis results should be available within 2 minutes of data input

### NFR2: Reliability
- Handle incomplete or missing experimental data gracefully
- Robust error handling for computational failures
- Automatic retry mechanisms for transient failures
- Data integrity validation throughout the workflow

### NFR3: Scalability
- Support for multiple concurrent DMTA cycles
- Handle large datasets from high-throughput experiments
- Efficient resource utilization for computational tasks
- Horizontal scaling for increased workload

## Technical Requirements

### TR1: AWS Infrastructure
- Amazon Bedrock Agent with Claude 3.5 Sonnet v2
- AWS Lambda functions for core DMTA workflow
- S3 storage for experimental data and results
- DynamoDB for workflow state management
- CloudFormation template for deployment
- Opentrons OT-2 integration via dedicated Lambda function

### TR2: Integration Requirements
- Lambda functions for all core operations
- Support for common laboratory data formats
- Integration with computational chemistry platforms
- Database connectivity for historical data access
- Opentrons OT-2 protocol generation and simulation capabilities

## Use Cases

### UC1: Active Learning DMTA Workflow
**Actor**: Drug Discovery Scientist
**Goal**: Optimize FactorX using active learning approach
**Chat Conversation Flow**:

**User**: "Please create a project plan to optimize Cablivi (Caplacizumab) for improved vWF binding affinity"
**Agent**: Creates initial DMTA plan with active learning strategy, defines optimization objectives (KD < 1 nM)

**User**: "Start the first DMTA cycle"
**Agent**: Uses plan_project to generate initial compound set and experimental design

**User**: "Design nanobody variants for testing"
**Agent**: Uses design_variants to apply acquisition functions (EI/UCB) and select promising variants

**User**: "Execute the expression and testing with OT-2 automation"
**Agent**: 
- Step 1: Calls make_test Lambda function
- Step 2: Lambda generates protein expression data
- Step 3: Lambda creates OT-2 protocol for sample preparation (6 concentrations × 8 variants)
- Step 4: Lambda simulates automated liquid handling execution (45 min, ±1.5% accuracy)
- Step 5: Lambda generates SPR binding assay results with improved precision
- Step 6: Lambda stores results in S3 and updates status in DynamoDB

**User**: "Analyze the results and recommend next steps"
**Agent**: Uses analyze_results to update Gaussian Process model, identifies best variants, recommends next cycle

**Iterative Process**: Continues until convergence criteria met or optimal nanobody variant found

### UC2: Multi-Cycle Optimization with Automation
**Actor**: Medicinal Chemist
**Goal**: Achieve target properties through iterative cycles with lab automation
**Steps**:
1. Review Gaussian Process model predictions
2. Apply acquisition functions for next compound selection
3. Generate OT-2 protocols for automated sample preparation
4. Execute liquid handling automation with real-time monitoring
5. Generate FactorX SPR binding data with enhanced precision
6. Update model with new results
7. Assess convergence and binding optimization progress

### UC3: Automated Sample Preparation Workflow
**Actor**: Laboratory Technician
**Goal**: Prepare SPR binding assay samples with OT-2 automation
**Chat Conversation Flow**:

**User**: "Prepare samples for Cycle 1 variants using OT-2"
**Agent**: "Generating OT-2 protocol for 8 variants × 6 concentrations = 48 samples. Estimated time: 45 minutes."

**User**: "Execute the protocol"
**Agent**: "🤖 OT-2 execution in progress... Buffer dispensing complete. Serial dilutions: 5/8 variants done. ETA: 12 minutes."

**User**: "Check preparation quality"
**Agent**: "✅ Sample preparation complete. Accuracy: 98.5% (±1.5%). Ready for SPR assay."

## Constraints

### C1: Simulation Limitations
- FactorX dummy data generation for make/test phases
- Opentrons protocol simulation using official Opentrons Python API (no physical hardware required)
- Gaussian Process modeling with synthetic data
- Realistic liquid handling parameters and timing simulation through Opentrons' validated simulation tools

### C2: Active Learning Scope
- Focus on Expected Improvement and UCB acquisition functions
- Single-objective optimization (vWF binding affinity)
- Simplified nanobody sequence representation

### C3: Implementation Scope
- Five Lambda functions: plan_project, design_variants, make_test (with OT-2 integration), analyze_results, project_status
- Chat-based interaction workflow with phase-by-phase confirmation
- DynamoDB state persistence with 3-table architecture
- S3 data storage for experimental data
- Multi-project support with project status management
- Opentrons protocol generation and execution simulation

## Implementation Status ✅

### Core Features
- ✅ Complete DMTA workflow (Plan → Design → Make-Test → Analyze)
- ✅ Multi-project support (tested with 3+ concurrent projects)
- ✅ Project status management and progress tracking
- ✅ 26+ variants generated across 4+ cycles
- ✅ Gaussian Process modeling with acquisition functions
- ✅ DynamoDB data persistence and S3 storage

### Opentrons OT-2 Integration
- 🚀 Automated sample preparation for SPR binding assays
- 🚀 OT-2 protocol generation with realistic liquid handling parameters
- 🚀 Serial dilution automation (6-point concentration curves)
- 🚀 Real-time execution monitoring and progress tracking
- 🚀 Enhanced precision: Manual ±5% → OT-2 ±1.5%
- 🚀 Time efficiency: 3 hours manual → 45 minutes automated

### Project Status Management
- ✅ Query project count: "How many projects are registered?"
- ✅ Check project progress: "What is the progress of the first project?"
- ✅ View all projects: "Show all project statuses"
- ✅ Phase tracking: "Cycle X Design completed - ready for Make-Test"
- ✅ Multi-project data isolation with unique project IDs

### Validated Capabilities
- ✅ End-to-end DMTA cycles with realistic data generation
- ✅ Active learning with EI/UCB acquisition functions
- ✅ Project isolation and concurrent execution
- ✅ Progress tracking across multiple cycles
- ✅ Natural language interface for all operations
- 🚀 Opentrons OT-2 protocol simulation and execution tracking
- 🚀 Automated liquid handling with enhanced precision and efficiency
- 🚀 Seamless integration of lab automation into DMTA workflow
