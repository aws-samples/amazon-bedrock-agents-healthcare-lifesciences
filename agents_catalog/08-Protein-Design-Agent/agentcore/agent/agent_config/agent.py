"""Protein Design Agent — Strands + AgentCore.

Runs protein design optimization on AWS HealthOmics. The agent triggers a
pre-existing HealthOmics Nextflow workflow (EvoProtGrad / ESM-2 directed
evolution on GPU) and monitors run status / results.

Migrated from the notebook-driven Bedrock Agent + two Lambda action groups in
the parent directory. The tools here are thin wrappers over the same boto3
`omics` and `s3` calls the Lambdas made. The HealthOmics workflow, the GPU
container image (ECR), the ESM-2 model weights (S3), and the workflow execution
role are pre-existing infrastructure provisioned by `protein_design_stack.yaml`;
this agent only calls into them.
"""

import logging
import os
import uuid
from urllib.parse import urlparse

import boto3
from strands import Agent, tool
from strands.models import BedrockModel

logger = logging.getLogger(__name__)

MODEL_ID = os.environ.get("MODEL_ID", "global.anthropic.claude-sonnet-5")

# Pre-existing infrastructure, injected as runtime configuration (previously the
# Lambda environment variables set by protein_design_stack.yaml).
WORKFLOW_ID = os.environ.get("WORKFLOW_ID") or os.environ.get("DEFAULT_WORKFLOW_ID")
ROLE_ARN = os.environ.get("ROLE_ARN") or os.environ.get("DEFAULT_ROLE_ARN")
ECR_URI = os.environ.get("ECR_URI") or os.environ.get("DEFAULT_ECR_URI")
S3_BUCKET = os.environ.get("S3_BUCKET") or os.environ.get("DEFAULT_S3_BUCKET")
ESM_MODEL_FILES = os.environ.get("ESM_MODEL_FILES") or os.environ.get("DEFAULT_ESM_MODEL_FILES")
DEFAULT_OUTPUT_TYPE = os.environ.get("DEFAULT_OUTPUT_TYPE", "all")
DEFAULT_PARALLEL_CHAINS = int(os.environ.get("DEFAULT_PARALLEL_CHAINS", "10"))
DEFAULT_N_STEPS = int(os.environ.get("DEFAULT_N_STEPS", "100"))
DEFAULT_MAX_MUTATIONS = int(os.environ.get("DEFAULT_MAX_MUTATIONS", "15"))

SYSTEM_PROMPT = """You are an expert in protein design and optimization using AWS HealthOmics workflows. \
Your primary task is to help users run protein design optimization workflows and provide relevant insights.

When providing your response:
a. Start with a brief summary of your understanding of the user's query.
b. Explain briefly the workflows you support and how each one does or does not meet the user's request.
c. Explain the steps you're taking to address the query. Ask for clarifications from the user if required.
d. Present the results of the workflow execution.

The optimization is asynchronous: trigger_aho_workflow starts a run and returns a run ID immediately, \
then monitor_aho_workflow reports status and results for that run ID. A run can take many minutes to \
hours, so after triggering, tell the user to check back and use the run ID to monitor progress. \
You perform workflow orchestration, not clinical or wet-lab advice."""


def _get_client(service: str):
    return boto3.client(service)


@tool
def trigger_aho_workflow(
    seed_sequence: str,
    run_name: str = "",
    output_uri: str = "",
    esm_model_files: str = "",
    onehotcnn_model_files: str = "",
    output_type: str = "",
    parallel_chains: int = 0,
    n_steps: int = 0,
    max_mutations: int = 0,
) -> str:
    """Start an AWS HealthOmics protein-design optimization run.

    Launches the pre-existing HealthOmics directed-evolution workflow for a seed
    protein sequence and returns the run ID immediately (the run is asynchronous).

    Args:
        seed_sequence: Wild-type / seed amino-acid sequence to optimize.
        run_name: Optional run name; a unique one is generated if omitted.
        output_uri: Optional S3 output URI; defaults to the configured bucket.
        esm_model_files: Optional S3 path to ESM model weights; defaults to configured.
        onehotcnn_model_files: Optional S3 path to a one-hot CNN scorer model.
        output_type: Output type ("all" by default).
        parallel_chains: Number of parallel MCMC chains (default 10).
        n_steps: Steps per chain (default 100).
        max_mutations: Maximum mutations (default 15).

    Returns:
        A human-readable summary including the run ID and status, or an error.
    """
    if not seed_sequence or not seed_sequence.strip():
        return "Error: seed_sequence parameter is required."
    if not WORKFLOW_ID:
        return "Error: WORKFLOW_ID is not configured. Set the WORKFLOW_ID environment variable."
    if not ROLE_ARN:
        return "Error: ROLE_ARN is not configured. Set the ROLE_ARN environment variable."
    if not ECR_URI:
        return "Error: ECR_URI is not configured. Set the ECR_URI environment variable."

    run_name = run_name or f"workflow-run-{uuid.uuid4().hex[:8]}"
    if not output_uri:
        if not S3_BUCKET:
            return "Error: output_uri not given and S3_BUCKET is not configured."
        output_uri = f"s3://{S3_BUCKET}/outputs/{run_name}/"

    workflow_parameters = {
        "container_image": ECR_URI,
        "seed_sequence": seed_sequence,
    }
    esm = esm_model_files or ESM_MODEL_FILES
    if esm:
        workflow_parameters["esm_model_files"] = esm
    if onehotcnn_model_files:
        workflow_parameters["onehotcnn_model_files"] = onehotcnn_model_files
    workflow_parameters["output_type"] = output_type or DEFAULT_OUTPUT_TYPE
    workflow_parameters["parallel_chains"] = parallel_chains or DEFAULT_PARALLEL_CHAINS
    workflow_parameters["n_steps"] = n_steps or DEFAULT_N_STEPS
    workflow_parameters["max_mutations"] = max_mutations or DEFAULT_MAX_MUTATIONS

    try:
        response = _get_client("omics").start_run(
            workflowId=WORKFLOW_ID,
            name=run_name,
            parameters=workflow_parameters,
            outputUri=output_uri,
            roleArn=ROLE_ARN,
        )
    except Exception as e:
        logger.error(f"Error starting workflow run: {e}")
        return f"Error starting workflow run: {e}"

    return (
        "Successfully started protein optimization workflow.\n\n"
        f"Run ID: {response['id']}\n"
        f"Status: {response['status']}\n"
        f"Output URI: {output_uri}\n\n"
        "Optimization parameters:\n"
        f"- Seed sequence: {seed_sequence[:20]}... ({len(seed_sequence)} amino acids)\n"
        f"- Parallel chains: {workflow_parameters['parallel_chains']}\n"
        f"- Steps per chain: {workflow_parameters['n_steps']}\n"
        f"- Max mutations: {workflow_parameters['max_mutations']}\n"
        f"- Output type: {workflow_parameters['output_type']}\n\n"
        f"The run is asynchronous. Check status later by asking to 'monitor workflow run {response['id']}'."
    )


def _get_run_results(s3_client, output_uri: str) -> str:
    """Summarize output files from a completed run's S3 output URI."""
    if not output_uri:
        return "No output URI provided."

    parsed = urlparse(output_uri)
    bucket = parsed.netloc
    prefix = parsed.path.lstrip("/")

    try:
        listing = s3_client.list_objects_v2(Bucket=bucket, Prefix=prefix)
    except Exception as e:
        return f"Error listing S3 objects: {e}"

    text = ""
    files = []
    for obj in listing.get("Contents", []):
        key = obj["Key"]
        size = obj["Size"]
        if not (key.endswith(".json") or key.endswith(".txt") or key.endswith(".csv")):
            continue
        if size < 10240:
            try:
                body = s3_client.get_object(Bucket=bucket, Key=key)["Body"].read().decode("utf-8")
                files.append({"key": key, "size": size, "content": body})
            except Exception as e:
                files.append({"key": key, "size": size, "error": str(e)})
        else:
            files.append({"key": key, "size": size, "url": f"s3://{bucket}/{key}"})

    if not files:
        return text + "No output files found."

    text += "Output files:\n"
    for f in files:
        text += f"- {f.get('key')} ({f.get('size')} bytes)\n"
        if "content" in f and f["key"].endswith("de_results.csv"):
            text += f"Results summary:\n{f['content'][:1000]}...\n\n"
    return text


@tool
def monitor_aho_workflow(run_id: str) -> str:
    """Check the status (and results, if complete) of a HealthOmics run.

    Args:
        run_id: The HealthOmics run ID returned by trigger_aho_workflow.

    Returns:
        The run status; for a completed run, a summary of the output files.
    """
    if not run_id or not run_id.strip():
        return "Error: run_id parameter is required."

    omics = _get_client("omics")
    try:
        run = omics.get_run(id=run_id)
    except Exception as e:
        logger.error(f"Error monitoring workflow: {e}")
        return f"Error monitoring workflow: {e}"

    status = run.get("status")
    text = f"Run ID: {run_id}\nCurrent Status: {status}\n"
    if run.get("name"):
        text += f"Run Name: {run.get('name')}\n"

    if status == "COMPLETED":
        text += _get_run_results(_get_client("s3"), run.get("outputUri"))
    elif status == "FAILED":
        text += f"Failed with message: {run.get('statusMessage')}\n"
    else:
        text += (
            "\nThe workflow is still running. You can check again later with the same run ID.\n"
            f"To check again, ask me to 'monitor workflow run {run_id}'."
        )
    return text


def create_agent() -> Agent:
    """Create and return the Protein Design Agent."""
    model = BedrockModel(model_id=MODEL_ID, streaming=True)
    return Agent(
        model=model,
        system_prompt=SYSTEM_PROMPT,
        tools=[trigger_aho_workflow, monitor_aho_workflow],
    )
