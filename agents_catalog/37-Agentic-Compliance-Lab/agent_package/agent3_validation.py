import boto3
import json
import base64
from typing import Dict, List
from datetime import datetime
import uuid
from strands import Agent, tool
from strands.models import BedrockModel
from steering_hooks import ValidationWorkflowPlugin

region = boto3.Session().region_name
s3 = boto3.client('s3')

@tool
def load_compliance_report(bucket: str, key: str) -> Dict:
    """Load compliance report and structured violations from S3"""
    try:
        response = s3.get_object(Bucket=bucket, Key=key)
        data = json.loads(response['Body'].read().decode('utf-8'))
        return {
            'status': 'success',
            'report': data.get('compliance_report', ''),
            'violations': data.get('violations', []),
            'source_file': data.get('source_file', '')
        }
    except Exception as e:
        return {'status': 'error', 'error': str(e)}


@tool
def analyze_annotated_image(bucket: str, key: str) -> Dict:
    """Use Claude vision (sub-agent) to analyze the annotated image"""
    try:
        bedrock = boto3.client('bedrock-runtime', region_name=region)
        
        response = s3.get_object(Bucket=bucket, Key=key)
        image_bytes = response['Body'].read()
        image_base64 = base64.b64encode(image_bytes).decode('utf-8')
        
        prompt = """Analyze this annotated medicine label image and provide a structured analysis:

IMAGE ANNOTATIONS (colored boxes on the label):
List each annotation with:
- Exact label text
- Box color (red/orange/yellow/green)
- What label content it highlights

SIDEBAR ANNOTATIONS (right side panel):
List each item with:
- Exact text
- Color indicator
- Section title (e.g., "MISSING SECTIONS")

VISUAL QUALITY:
- Total annotation count
- Any overlapping boxes
- Text readability
- Overall clarity (clear/cluttered/acceptable)

Provide your analysis in clear sections matching the above structure."""

        message = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 2000,
            "messages": [{
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/png",
                            "data": image_base64
                        }
                    },
                    {"type": "text", "text": prompt}
                ]
            }]
        }
        
        response = bedrock.invoke_model(
            modelId="us.anthropic.claude-sonnet-4-6",
            body=json.dumps(message)
        )
        
        result = json.loads(response['body'].read())
        analysis = result['content'][0]['text']
        
        return {'status': 'success', 'analysis': analysis, 'prompt_used': prompt}
    except Exception as e:
        return {'status': 'error', 'error': str(e)}
        

@tool
def store_validation_result(bucket: str, report_key: str, image_key: str, 
                           validation_status: str, issues: List[str], 
                           feedback: str) -> str:
    """Store validation results in S3"""
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        session_id = str(uuid.uuid4())[:8]
        key = f"validation-{timestamp}-{session_id}.json"
        
        validation_data = {
            'timestamp': timestamp,
            'session_id': session_id,
            'report_key': report_key,
            'image_key': image_key,
            'validation_status': validation_status,
            'issues_found': issues,
            'feedback_to_agent2': feedback,
            'validation_date': datetime.now().isoformat()
        }
        
        s3.put_object(
            Bucket=bucket,
            Key=key,
            Body=json.dumps(validation_data, indent=2),
            ContentType='application/json'
        )
        
        return f"s3://{bucket}/{key}"
    except Exception as e:
        raise Exception(f"Error storing validation: {str(e)}")

validation_tools = [load_compliance_report, analyze_annotated_image, store_validation_result]

agent_instructions = """You are a Validation Specialist that ensures Agent 2's annotated images accurately reflect Agent 1's structured violations list.

Your workflow: load the compliance report, analyze the annotated image, then store your validation result. Tool ordering and status/issues consistency are enforced automatically.

VALIDATION CRITERIA:

1. COUNT CHECK (strict):
   - The number of annotations on the image (both on-label boxes + sidebar items) MUST visually equal the number of violations in the violations array
   - If the count does not match, REJECT and specify which violations are missing or which annotations are extra

2. COMPLETENESS CHECK (compare annotations against the violations array):
   - Every violation in the array MUST have a corresponding annotation — regardless of severity
   - Each annotation label must reasonably match a violation's "title" from the violations array

3. CLASSIFICATION ACCURACY CHECK:
   - Severity levels in annotations should match the violation's "severity" field
   - Missing/absent items must be placed on the sidebar (right hand side)
   - Existing content issues must be placed on the label with bounding boxes
   - Largely compliant labels (empty violations array) show compliant badge only on the right hand side

4. HALLUCINATION CHECK (Strict):
   - No annotations for violations not present in the violations array
   - ZERO false positives required

POSSIBLE VALIDATION OUTCOMES:

1. APPROVED:
- validation_status: "APPROVED"
- Approve ONLY when annotation count matches violation count AND all violations are covered AND no false positives exist
- Minor wording variations in labels are acceptable (e.g., "Missing Drug Facts" vs "Missing Drug Facts Panel")

2. REJECTED:
- validation_status: "REJECTED"
- Reject when annotation count does not match violation count
- Reject when any violation from the array has no corresponding annotation
- Reject when there are false positive annotations (not in the violations array)
- In the feedback, list EVERY missing violation by title so Agent 2 knows exactly what to add

FEEDBACK FORMAT:
When rejecting, structure your feedback clearly:
- Expected annotation count: N
- Actual annotation count: M
- Missing violations: [list each missing violation title]
- Extra/false annotations: [list any annotations not matching a violation]
- Correctly annotated: [list what was done right so Agent 2 preserves these]

ADDITIONAL RULES:
- Do not reject for minor wording variations or slight coordinate imprecision
- DO reject for any missing violation, any extra annotation, or count mismatch
"""

def get_validation_agent():
    model = BedrockModel(
        model_id="us.anthropic.claude-opus-4-7",
        region_name=region,
        streaming=False
    )
    
    agent = Agent(
        model=model,
        tools=validation_tools,
        system_prompt=agent_instructions,
        plugins=[ValidationWorkflowPlugin()]  # steering hooks
    )
    agent.name = "Validation_Specialist_Agent"
    return agent
