"""Clinical Prior Authorization Agent — AgentCore runtime."""

import json

from bedrock_agentcore.runtime import BedrockAgentCoreApp
from strands import Agent
from strands_tools import use_llm

from model.load import load_model
from tools.prior_auth_tools import (
    calculate_claim_approval,
    download_appropriate_document,
    get_guidance_document_list,
    load_billing_data,
    parse_fee_schedule,
    parse_pdf,
)

app = BedrockAgentCoreApp()
log = app.logger

SYSTEM_PROMPT_TEMPLATE = """
From the following patient data, choose which specialty closely aligns with the patient data.
Please choose the one that is the latest document for the given input of the patient data.
1. Return them as a dictionary with the keys 'pdf_urls' and 'fee_schedule_url'.
2. Download the latest document
3. Parse the fee schedule document.
4. Only rely on the fee schedule document to calculate the claim approval cost
5. Only rely on the claim approval document to determine if the claim is approved or not.
Give a clear "SUCCESS" flag if the document is downloaded successfully.
Do not use model's internal knowledge to answer the questions.
Give me the total cost along with the line items in the fee schedule document.
Only use the fee schedule document and the costs mentioned in the columns to calculate the cost.
Also do include a breakdown or explanation of the cost for each line item.
Here is the list of specialties:
{}
"""


@app.entrypoint
async def invoke(payload, context):
    """Process a prior authorization request.

    Payload:
        patient_data: dict or str — FHIR patient encounter bundle
    """
    patient_data = payload.get("patient_data")
    if isinstance(patient_data, dict):
        patient_data = json.dumps(patient_data, indent=2)

    billing_data = load_billing_data()
    specialties = list(billing_data["categories"].keys())
    system_prompt = SYSTEM_PROMPT_TEMPLATE.format("\n".join(specialties))

    agent = Agent(
        model=load_model(),
        system_prompt=system_prompt,
        tools=[
            use_llm,
            get_guidance_document_list,
            download_appropriate_document,
            parse_pdf,
            parse_fee_schedule,
            calculate_claim_approval,
        ],
    )

    stream = agent.stream_async(patient_data)
    async for event in stream:
        if "data" in event and isinstance(event["data"], str):
            yield event["data"]


if __name__ == "__main__":
    app.run()
