import os
import boto3
import json
import re
import time
import logging
from datetime import datetime
from bedrock_agentcore.runtime import BedrockAgentCoreApp
from agent1_compliance import get_compliance_agent
from agent2_annotation import get_annotation_agent
from agent3_validation import get_validation_agent

logging.getLogger("strands").setLevel(logging.DEBUG)
logging.basicConfig(format="%(levelname)s | %(name)s | %(message)s", handlers=[logging.StreamHandler()])
logger = logging.getLogger(__name__)

s3 = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')
results_bucket = os.environ['RESULTS_BUCKET']
projects_table_name = os.environ.get('PROJECTS_TABLE', '')
cloudfront_url = os.environ.get('CLOUDFRONT_URL', '')

def _update_project(project_id, updates):
    """Update project record in DynamoDB."""
    if not project_id or not projects_table_name:
        return
    try:
        table = dynamodb.Table(projects_table_name)
        expr_parts = []
        values = {}
        names = {}
        for i, (k, v) in enumerate(updates.items()):
            attr = f"#a{i}"
            val = f":v{i}"
            expr_parts.append(f"{attr} = {val}")
            names[attr] = k
            values[val] = v
        table.update_item(
            Key={'projectId': project_id},
            UpdateExpression="SET " + ", ".join(expr_parts),
            ExpressionAttributeNames=names,
            ExpressionAttributeValues=values,
        )
        logger.info(f"📝 DynamoDB updated: {list(updates.keys())}")
    except Exception as e:
        logger.warning(f"DynamoDB update failed: {e}")

def _finalize_project(project_id, image_key, report_key, annotated_key, validation_key, attempts):
    """Write final pipeline results to DynamoDB and S3 completion marker."""
    annotated_url = f"{cloudfront_url}/{annotated_key}" if cloudfront_url else f"s3://{results_bucket}/{annotated_key}"

    # Read compliance report to get violations and narrative
    compliance_report = ''
    violations = []
    try:
        report_obj = s3.get_object(Bucket=results_bucket, Key=report_key)
        report_data = json.loads(report_obj['Body'].read().decode('utf-8'))
        compliance_report = report_data.get('compliance_report', '')
        violations = report_data.get('violations', [])
    except Exception as e:
        logger.warning(f"Could not read report for DynamoDB: {e}")

    # Write to DynamoDB
    _update_project(project_id, {
        'status': 'complete',
        'annotatedImageUrl': annotated_url,
        'complianceReport': compliance_report,
        'formattedViolations': violations,
        'imageKey': image_key,
        'reportKey': report_key,
        'annotatedKey': annotated_key,
        'validationKey': validation_key,
        'pipelineAttempts': attempts,
        'completedAt': datetime.now().isoformat(),
        'progress': {'step1': True, 'step2': True, 'step3': True},
    })

    # S3 completion marker (backwards compatibility)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    marker_key = f"completion-{timestamp}-{image_key.replace('labels/', '').replace('/', '-')}.json"
    s3.put_object(
        Bucket=results_bucket,
        Key=marker_key,
        Body=json.dumps({
            'status': 'completed',
            'annotated_key': annotated_key,
            'report_key': report_key,
            'validation_key': validation_key,
            'timestamp': datetime.now().isoformat(),
            'attempts': attempts,
            'project_id': project_id,
        }, indent=2),
        ContentType='application/json'
    )
    logger.info(f"📍 Marker: s3://{results_bucket}/{marker_key}")
    logger.info("="*80)


def extract_key(text):
    match = re.search(r's3://[^/]+/([^\s`]+)', str(text))
    return match.group(1) if match else None

def run_pipeline(image_bucket, image_key, max_retries=3, regulatory_region='US_FDA', project_id=''):
    
    logger.info("="*80)
    logger.info("🚀 STARTING PIPELINE")
    logger.info(f"📍 Region: {regulatory_region}, Project: {project_id}")
    logger.info("="*80)

    # Mark project as processing
    _update_project(project_id, {
        'status': 'processing',
        'progress': {'step1': False, 'step2': False, 'step3': False}
    })
    
    logger.info("\n📋 STEP 1: Compliance Analysis...")

    # Fetch the label image so Agent 1 can read it directly with its own vision
    image_obj = s3.get_object(Bucket=image_bucket, Key=image_key)
    image_bytes = image_obj['Body'].read()
    ext = image_key.rsplit('.', 1)[-1].lower() if '.' in image_key else 'png'
    image_format = {'jpg': 'jpeg', 'jpeg': 'jpeg', 'png': 'png', 'gif': 'gif', 'webp': 'webp'}.get(ext, 'png')

    agent1_prompt = [
        {"text": (
            f"Analyze {regulatory_region.replace('_', ' ')} compliance for the attached medicine label image. "
            f"The image is stored at s3://{image_bucket}/{image_key} — use that S3 key as the source_file when "
            f"you call store_compliance_report."
        )},
        {"image": {"format": image_format, "source": {"bytes": image_bytes}}},
    ]
    agent1 = get_compliance_agent(regulatory_region)
    agent1_response = agent1(agent1_prompt)

    report_key = extract_key(agent1_response)
    
    if not report_key:
        response = s3.list_objects_v2(Bucket=results_bucket, Prefix='compliance-report-')
        contents = response.get('Contents', [])
        if not contents:
            raise Exception(f"No compliance reports found in {results_bucket}")
        report_key = sorted([obj['Key'] for obj in contents], reverse=True)[0]
    
    logger.info(f"✅ Report: s3://{results_bucket}/{report_key}")

    _update_project(project_id, {
        'progress': {'step1': True, 'step2': False, 'step3': False}
    })

    validation_key = None
    attempts_history = []  # Track all attempts with their issue counts
    
    for attempt in range(1, max_retries + 1):
        logger.info(f"\n🎨 STEP 2: Image Annotation (Attempt {attempt}/{max_retries})...")
        
        agent2_query = f"""Create annotated image using:
                        - Original image: bucket={image_bucket}, key={image_key}
                        - Compliance analysis: bucket={results_bucket}, key={report_key}
                        
                        Analyze the image visually, map the compliance issues to specific regions, and generate precise annotations."""
        
        if attempt > 1 and validation_key:
            validation_obj = s3.get_object(Bucket=results_bucket, Key=validation_key)
            validation_data = json.loads(validation_obj['Body'].read().decode('utf-8'))
            feedback = validation_data.get('feedback_to_agent2', '')
            agent2_query += f"\n\nPREVIOUS FEEDBACK:\n{feedback}"
        
        agent2 = get_annotation_agent()
        agent2_response = agent2(agent2_query)
        
        annotated_key = extract_key(agent2_response)
        if not annotated_key:
            response = s3.list_objects_v2(Bucket=results_bucket, Prefix='annotated-')
            annotated_key = sorted([obj['Key'] for obj in response.get('Contents', [])], reverse=True)[0]
        logger.info(f"✅ Annotated: s3://{results_bucket}/{annotated_key}")

        _update_project(project_id, {
            'progress': {'step1': True, 'step2': True, 'step3': False}
        })
        
        logger.info(f"\n🔍 STEP 3: Validation (Attempt {attempt}/{max_retries})...")
        
        agent3_query = f"""Validate the annotated image against the compliance report:
                        - Compliance report: bucket={results_bucket}, key={report_key}
                        - Annotated image: bucket={results_bucket}, key={annotated_key}
                        
                        Store validation results in bucket: {results_bucket}"""
        agent3 = get_validation_agent()
        agent3_response = agent3(agent3_query)
        
        validation_key = extract_key(agent3_response)
        if not validation_key:
            time.sleep(2)  # Wait for S3 consistency
            response = s3.list_objects_v2(Bucket=results_bucket, Prefix='validation-')
            validation_key = sorted([obj['Key'] for obj in response.get('Contents', [])], reverse=True)[0]
        
        logger.info(f"📄 Validation: s3://{results_bucket}/{validation_key}")
        
        validation_obj = s3.get_object(Bucket=results_bucket, Key=validation_key)
        validation_data = json.loads(validation_obj['Body'].read().decode('utf-8'))
        
        # Track this attempt
        issue_count = len(validation_data.get('issues_found', []))
        attempts_history.append({
            'attempt': attempt,
            'annotated_key': annotated_key,
            'validation_key': validation_key,
            'status': validation_data['validation_status'],
            'issue_count': issue_count
        })
        
        if validation_data['validation_status'] == 'APPROVED':
            logger.info(f"\n✅ APPROVED on attempt {attempt}!")
            _finalize_project(project_id, image_key, report_key, annotated_key, validation_key, attempt)
            
            return {
                'status': 'success',
                'compliance_report': f"s3://{results_bucket}/{report_key}",
                'annotated_image': f"s3://{results_bucket}/{annotated_key}",
                'validation_report': f"s3://{results_bucket}/{validation_key}",
                'attempts': attempt
            }
        else:
            logger.info(f"\n❌ REJECTED -> Issues: {issue_count}")
            if attempt == max_retries:
                logger.info("\n⚠️ Max retries reached -> selecting best attempt")
                best_attempt = min(attempts_history, key=lambda x: x['issue_count'])
                logger.info(f"🏆 Best attempt: #{best_attempt['attempt']} with {best_attempt['issue_count']} issues")
                _finalize_project(project_id, image_key, report_key, best_attempt['annotated_key'], best_attempt['validation_key'], max_retries)
                
                return {
                    'status': 'partial_success',
                    'compliance_report': f"s3://{results_bucket}/{report_key}",
                    'annotated_image': f"s3://{results_bucket}/{best_attempt['annotated_key']}",
                    'validation_report': f"s3://{results_bucket}/{best_attempt['validation_key']}",
                    'attempts': max_retries,
                    'best_of_attempts': True,
                    'issue_count': best_attempt['issue_count']
                }
    
    return {'status': 'failed'}

app = BedrockAgentCoreApp()

@app.entrypoint
def compliance_pipeline_handler(payload):
    """Invoke compliance pipeline"""
    image_bucket = payload.get("image_bucket")
    image_key = payload.get("image_key")
    max_retries = payload.get("max_retries", 3)
    regulatory_region = payload.get("region", "US_FDA")
    project_id = payload.get("project_id", "")
    
    logger.info(f"Processing: {image_bucket}/{image_key} for {regulatory_region} (project: {project_id})")
    
    try:
        result = run_pipeline(image_bucket, image_key, max_retries, regulatory_region, project_id)
        logger.info(f"Pipeline completed: {result.get('status')}")
        return result
    except Exception as e:
        error_response = {"error": str(e), "type": "pipeline_error", "status": "failed"}
        logger.error(f"Pipeline error: {error_response}")
        return error_response

if __name__ == "__main__":
    app.run()
