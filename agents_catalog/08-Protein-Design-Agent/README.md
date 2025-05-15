# Protein Design Agent with AWS HealthOmics Workflow

This agent helps users design and optimize protein sequences using AWS HealthOmics workflows. It leverages pretrained machine 
learning models (such as protein language models and property prediction models) to evolve protein sequences for improved properties, making it valuable for researchers in biotechnology, pharmaceuticals, and synthetic biology.

## Features

• **Protein Sequence Optimization**: Submit protein sequences for optimization using directed evolution algorithms
• **Workflow Monitoring**: Track the progress of running optimization workflows
• **Results Analysis**: Retrieve and analyze the results of completed optimization runs
• **Custom Parameters**: Configure optimization parameters like mutation rates and chain counts

## Architecture

The agent consists of two main Lambda functions:

1. WorkflowTriggerFunction: Initiates protein design optimization workflows in AWS HealthOmics
2. WorkflowMonitorFunction: Monitors the status of running workflows and retrieves results

The workflow uses the EvoProtGrad library for protein directed evolution, running on AWS HealthOmics with GPU acceleration.

## Deployment

The agent is deployed using AWS CloudFormation. The template `protein_design_stack.yaml` creates all necessary resources including:

• Amazon Bedrock Agent with action groups
• Lambda functions for workflow triggering and monitoring
• ECR repository for the container image
• HealthOmics workflow definition
• IAM roles and permissions
• S3 bucket for storing workflow inputs and outputs

## Prerequisites

• AWS CLI configured with appropriate permissions
• Amazon Bedrock access
• IAM role for the Bedrock agent
• AWS HealthOmics service access

## Deployment Steps

See `agent_creation_protein_design_aho_workflow.ipynb`


## Usage Examples

### Start a Protein Design Optimization

"Can you optimize this protein sequence: 
EVQLVETGGGLVQPGGSLRLSCAASGFTLNSYGISWVRQAPGKGPEWVSVIYSDGRRTFYGDSVKGRFTISRDTSTNTVYLQMNSLRVEDTAVYYCAKGRAAGTFDSWGQGTLVTVSS"

### Monitor a Running Workflow

"Check the status of workflow run 6762860"

### Retrieve Optimization Results

"Show me the results of the protein optimization run 6762860"

### Configure Advanced Parameters

"Run a protein optimization for sequence ACDEFGHIKLMNPQRSTVWY with 20 parallel chains and 200 steps"

## Technical Details

The protein design workflow uses:

• **EvoProtGrad**: A library for directed evolution of proteins using gradient-based discrete MCMC
• **ESM-2**: A state-of-the-art protein language model for sequence optimization
• **AWS HealthOmics**: For running the computationally intensive workflow with GPU acceleration
• **Docker Container**: Custom container with all required dependencies for the workflow

The workflow performs directed evolution by:
1. Starting with a seed protein sequence
2. Running multiple parallel MCMC chains
3. Proposing mutations based on the ESM-2 model
4. Evaluating mutations using ESM-2 model `mutant_marginal` score
5. Returning optimized sequences with improved properties

