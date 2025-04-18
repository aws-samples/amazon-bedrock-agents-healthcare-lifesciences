# Analyze Medical Text with John Snow Labs

## 1. Summary

Analyze medical text using John Snow Labs medical LLMs deployed on Amazon SageMaker. Note that this agent requires a subscription to one or more AWS Marketplace products.

## 2. Agent Details

### 2.1. Instructions

> You are a medical text analysis assistant powered by a large language model.
> You help analyze clinical and medical documentation using specialized NLP tools, but you DO NOT provide clinical guidance, diagnosis, treatment recommendations, or interpret medical implications for individual patients.
> 
> Guidelines for Use:
> 
> - Always clarify that you are performing text analysis, not providing medical advice
> - When analyzing clinical text, suggest de-identification first if text might contain PHI
> - Explain which tool you're using and why it's appropriate for the task
> - Present analysis results clearly with appropriate context and limitations
> - Never interpret clinical implications for individual patients
> - Do not make diagnostic or treatment suggestions
> - Refer users to qualified healthcare professionals for clinical questions

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
  name: "extract_social_determinants_of_health",
  description: "Identify socio-environmental health determinants like access to care, diet, employment, and housing from health records. Tailored for professionals and researchers, this pipeline extracts key factors influencing health in social, economic, and environmental contexts. Process up to 2.8 M chars per hour for real-time and up to 12 M chars per hour for batch mode.",
  inputSchema: {
    type: "object",
    properties: {
      medical_text: { type: "string", description: "Unstructured medical text"},
    },
    required: ["medical_text"]
  }
},
{
  name: "extract_icd_10_cm_sentence_entities",
  description: "This model extracts the following entities and maps them to their ICD-10-CM codes using sbiobert_base_cased_mli sentence embeddings. It predicts ICD-10-CM codes up to 3 characters (according to ICD-10-CM code structure the first three characters represent the general type of injury or disease).",
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

  - Extract Social Determinants of Health (Product 1681a948-a003-4c34-81be-7f633d14890d)
  - ICD-10-CM Sentence entity resolver (Product 23387793-337a-4161-b5d0-e899240438ef)

2. (If needed) Verify your AWS credentials are available in your current session.

`aws sts get-caller-identity`

3. (If needed) Create a Amazon S3 bucket to store the agent template.

`aws s3 mb s3://YOUR_S3_BUCKET_NAME`

4. Navigate to the `12-JSL-analyze-medical-reports` folder

`cd agents_catalog/12-JSL-analyze-medical-reports`

5. Package and deploy the agent template

```bash
export BUCKET_NAME="<REPLACE>"
export NAME="<REPLACE>"
export REGION="<REPLACE>"
export BEDROCK_AGENT_SERVICE_ROLE_ARM="<REPLACE>"

aws cloudformation package --template-file "jsl-analyze-medical-reports.yaml" \
  --s3-bucket $BUCKET_NAME \
  --output-template-file "jsl-analyze-medical-reports-packaged.yaml"
aws cloudformation deploy --template-file "jsl-analyze-medical-reports-packaged.yaml" \
  --capabilities CAPABILITY_IAM \
  --stack-name $NAME \
  --region $REGION \
  --parameter-overrides \
  AgentAliasName="Latest" \
  AgentIAMRoleArn=$BEDROCK_AGENT_SERVICE_ROLE_ARM \
rm jsl-analyze-medical-reports-packaged.yaml
```
