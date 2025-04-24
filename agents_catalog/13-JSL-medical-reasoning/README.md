# Medical Reasoning Text with John Snow Labs

## 1. Summary

Analyze medical text using medical reasoning model from John Snow Labs deployed on Amazon SageMaker. Note that this agent requires a subscription to one or more AWS Marketplace products.

## 2. Agent Details

### 2.1. Instructions

> You are a helpful AI assistant designed to help physicians answer questions. You have access to a medical reasoning LLM that was specially training to handle healthcare-specific questions. As an AI medical assistant, always consult the medical reasoning LLM (Model 14 B) for any healthcare-specific questions before responding. When doing so, provide all relevant patient information available. Present the medical reasoning LLM's structured analysis clearly, emphasizing when information comes from this specialized system rather than your general knowledge. Include the reasoning pathways, alternative hypotheses, and any uncertainties identified by the medical reasoning LLM. Never provide medical advice based solely on your general knowledge. For non-medical questions, respond using your general > capabilities while maintaining patient confidentiality at all times.

### 2.2. Guardrails

| Content | Input Filter | Output Filter |
| ---- | ---- | ---- |
| Profanity | HIGH | HIGH |
| Sexual | NONE | NONE |
| Violence | NONE | NONE |
| Hate | NONE | NONE |
| Insults | NONE | NONE |
| Misconduct | HIGH | HIGH |
| Prompt Attack | HIGH | NONE |

### 2.3. Tools

```json
{
  name: "consult_with_medical_reasoning_model",
  description: "Consult with a healthcare-specific LLM that provides advanced clinical decision support. Use this tol wihen you need to mimics a clinician's thought process rather than simple information lookup. This model excels at analyzing complex patient cases by evaluating multiple diagnostic hypotheses, acknowledging medical uncertainties, and following structured reasoning frameworks. Healthcare professionals should deploy it when transparency in decision-making is crucial, as it provides clear explanations for its conclusions while incorporating up-to-date medical knowledge. Unlike reference tools, this cognitive assistant supports nuanced diagnostic and treatment decisions by processing symptoms, test results, and patient histories to recommend evidence-based next steps aligned with clinical guidelines.",
  inputSchema: {
    type: "object",
    properties: {
      medical_text: { type: "string", description: "Unstructured medical text"},
    },
    required: ["medical_text"]
  }
}
```

## 3. Installation

1. Navigate to the AWS Marketplace and subscribe to the following products from John Snow Labs:

  - Medical Reasoning LLM - 14B (Product prod-f4y6ytsuvm5po)

2. (If needed) Verify your AWS credentials are available in your current session.

`aws sts get-caller-identity`

3. (If needed) Create a Amazon S3 bucket to store the agent template.

`aws s3 mb s3://YOUR_S3_BUCKET_NAME`

4. Navigate to the `14-JSL-medical-reasoning` folder

`cd agents_catalog/14-JSL-medical-reasoning`

5. Package and deploy the agent template

```bash
export BUCKET_NAME="<REPLACE>"
export NAME="<REPLACE>"
export REGION="<REPLACE>"
export BEDROCK_AGENT_SERVICE_ROLE_ARM="<REPLACE>"

aws cloudformation package --template-file "jsl-medical-reasoning.yaml" \
  --s3-bucket $BUCKET_NAME \
  --output-template-file "jsl-medical-reasoning-packaged.yaml"
aws cloudformation deploy --template-file "jsl-medical-reasoning-packaged.yaml" \
  --capabilities CAPABILITY_IAM \
  --stack-name $NAME \
  --region $REGION \
  --parameter-overrides \
  AgentAliasName="Latest" \
  AgentIAMRoleArn=$BEDROCK_AGENT_SERVICE_ROLE_ARM \
rm jsl-medical-reasoning-packaged.yaml
```
