import json
import os
import re
import boto3
from datetime import datetime
from decimal import Decimal

s3 = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')

INCOMING_BUCKET = os.environ['INCOMING_BUCKET']
RESULTS_BUCKET = os.environ['RESULTS_BUCKET']
CLOUDFRONT_URL = os.environ['CLOUDFRONT_URL']
PROJECTS_TABLE = os.environ['PROJECTS_TABLE']

projects_table = dynamodb.Table(PROJECTS_TABLE)


class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, Decimal):
            return int(o) if o == int(o) else float(o)
        return super().default(o)

def lambda_handler(event, context):
    # Handle both API Gateway v1 and v2 formats
    path = event.get('rawPath') or event.get('path', '')
    
    # Parse body
    body_str = event.get('body', '{}')
    if isinstance(body_str, str):
        body = json.loads(body_str) if body_str else {}
    else:
        body = body_str
    
    headers = {
        'Access-Control-Allow-Origin': os.environ.get('FRONTEND_ORIGIN', '*'),
        'Access-Control-Allow-Headers': 'Content-Type',
        'Access-Control-Allow-Methods': 'POST, OPTIONS'
    }
    
    # Handle OPTIONS for CORS
    http_method = event.get('requestContext', {}).get('http', {}).get('method') or event.get('httpMethod', '')
    if http_method == 'OPTIONS':
        return {'statusCode': 200, 'headers': headers, 'body': ''}
    
    print(f"Path: {path}, Method: {http_method}, Body: {body}")
    
    try:
        if path == '/upload':
            return handle_upload(body, headers)
        elif path == '/check':
            return handle_check(body, headers)
        elif path == '/projects/list':
            return handle_projects_list(headers)
        elif path == '/projects/save':
            return handle_projects_save(body, headers)
        elif path == '/projects/delete':
            return handle_projects_delete(body, headers)
        else:
            return {
                'statusCode': 404,
                'headers': headers,
                'body': json.dumps({'error': f'Not found: {path}'})
            }
    except Exception as e:
        print(f"Error: {str(e)}")
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({'error': 'Internal server error'})
        }

def _sanitize_filename(name):
    """Strip path components and unsafe characters from a filename."""
    name = name.split('/')[-1].split('\\')[-1]  # strip path separators
    name = re.sub(r'[^a-zA-Z0-9._-]', '_', name)  # keep only safe chars
    return name[:255] or 'upload'

def handle_upload(body, headers):
    filename = _sanitize_filename(body.get('filename', ''))
    content_type = body.get('contentType', '')
    region = body.get('region', 'US_FDA')
    project_id = body.get('projectId', '')

    if not filename or not content_type:
        return {'statusCode': 400, 'headers': headers, 'body': json.dumps({'error': 'filename and contentType are required'})}

    # Validate content type
    allowed_types = ['image/jpeg', 'image/png', 'image/jpg']
    if content_type not in allowed_types:
        return {'statusCode': 400, 'headers': headers, 'body': json.dumps({'error': 'Only JPEG and PNG images are allowed'})}

    # Validate region
    valid_regions = ['US_FDA', 'UK_MHRA']
    if region not in valid_regions:
        print(f"⚠ Invalid region '{region}', defaulting to US_FDA")
        region = 'US_FDA'
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    key = f"labels/{region}/{timestamp}_{filename}"
    
    print(f"📤 Generating upload URL for: {key}")
    print(f"📍 Regulatory Region: {region}, Project: {project_id}")
    
    # Generate presigned URL with tagging (region + projectId)
    tagging = f'regulatory_region={region}&project_id={project_id}'
    upload_url = s3.generate_presigned_url(
        'put_object',
        Params={
            'Bucket': INCOMING_BUCKET,
            'Key': key,
            'ContentType': content_type,
            'Tagging': tagging
        },
        ExpiresIn=300
    )
    
    return {
        'statusCode': 200,
        'headers': headers,
        'body': json.dumps({
            'uploadUrl': upload_url,
            'key': key,
            'region': region
        })
    }

def handle_check(body, headers):
    project_id = body.get('projectId')
    image_key = body.get('key')

    # If we have a projectId, check DynamoDB directly
    if project_id:
        try:
            resp = projects_table.get_item(Key={'projectId': project_id})
            item = resp.get('Item')
            if item and item.get('status') == 'complete':
                return {
                    'statusCode': 200,
                    'headers': headers,
                    'body': json.dumps({
                        'status': 'completed',
                        'annotatedImageUrl': item.get('annotatedImageUrl', ''),
                        'complianceReport': item.get('complianceReport', ''),
                        'violations': item.get('formattedViolations', []),
                        'progress': item.get('progress', {
                            'step1': True, 'step2': True, 'step3': True
                        })
                    }, cls=DecimalEncoder)
                }
            elif item:
                return {
                    'statusCode': 200,
                    'headers': headers,
                    'body': json.dumps({
                        'status': 'processing',
                        'progress': item.get('progress', {
                            'step1': False, 'step2': False, 'step3': False
                        })
                    }, cls=DecimalEncoder)
                }
        except Exception as e:
            print(f"DynamoDB check error: {e}")

    # Fallback: S3-based check for backwards compatibility
    if not image_key:
        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps({'status': 'processing', 'progress': {'step1': False, 'step2': False, 'step3': False}})
        }

    upload_timestamp = body.get('uploadTimestamp')
    search_pattern = "completion-"
    search_suffix = f"-{image_key.replace('labels/', '').replace('/', '-')}.json"
    
    print(f"Searching for completion files with pattern: {search_pattern}*{search_suffix}")
    print(f"Upload timestamp: {upload_timestamp}")
    
    try:
        image_obj = s3.head_object(Bucket=INCOMING_BUCKET, Key=image_key)
        image_upload_time = image_obj['LastModified']
        
        progress = check_pipeline_progress(image_key, image_upload_time)
        
        response = s3.list_objects_v2(Bucket=RESULTS_BUCKET, Prefix=search_pattern)
        
        if 'Contents' not in response:
            return {
                'statusCode': 200,
                'headers': headers,
                'body': json.dumps({'status': 'processing', 'progress': progress})
            }
        
        matching_files = [
            obj for obj in response['Contents']
            if obj['Key'].endswith(search_suffix) and obj['LastModified'] > image_upload_time
        ]
        
        if not matching_files:
            return {
                'statusCode': 200,
                'headers': headers,
                'body': json.dumps({'status': 'processing', 'progress': progress})
            }
        
        marker_key = sorted(matching_files, key=lambda x: x['LastModified'], reverse=True)[0]['Key']
        marker_obj = s3.get_object(Bucket=RESULTS_BUCKET, Key=marker_key)
        marker_data = json.loads(marker_obj['Body'].read().decode('utf-8'))
        
        annotated_key = marker_data['annotated_key']
        report_key = marker_data['report_key']
        
        try:
            s3.head_object(Bucket=RESULTS_BUCKET, Key=annotated_key)
            s3.head_object(Bucket=RESULTS_BUCKET, Key=report_key)
        except Exception:
            return {
                'statusCode': 200,
                'headers': headers,
                'body': json.dumps({'status': 'processing', 'progress': progress})
            }
        
        annotated_url = f"{CLOUDFRONT_URL}/{annotated_key}"
        report_obj = s3.get_object(Bucket=RESULTS_BUCKET, Key=report_key)
        report_data = json.loads(report_obj['Body'].read().decode('utf-8'))
        
        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps({
                'status': 'completed',
                'annotatedImageUrl': annotated_url,
                'complianceReport': report_data.get('compliance_report', ''),
                'violations': report_data.get('violations', []),
                'progress': {'step1': True, 'step2': True, 'step3': True}
            })
        }
    except Exception as e:
        print(f"Error checking status: {e}")
        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps({'status': 'processing', 'progress': {'step1': False, 'step2': False, 'step3': False}})
        }

def check_pipeline_progress(image_key, image_upload_time):
    """Check for intermediate pipeline files to determine progress"""
    progress = {
        'step1': False,
        'step2': False,
        'step3': False
    }
    
    try:
        # Check for compliance report (step 1)
        report_response = s3.list_objects_v2(
            Bucket=RESULTS_BUCKET,
            Prefix='compliance-report-'
        )
        if 'Contents' in report_response:
            recent_reports = [
                obj for obj in report_response['Contents']
                if obj['LastModified'] > image_upload_time
            ]
            if recent_reports:
                progress['step1'] = True
                print(f"Step 1 complete: Found {len(recent_reports)} recent compliance reports")
        
        # Check for annotated image (step 2)
        annotated_response = s3.list_objects_v2(
            Bucket=RESULTS_BUCKET,
            Prefix='annotated-'
        )
        if 'Contents' in annotated_response:
            recent_annotated = [
                obj for obj in annotated_response['Contents']
                if obj['LastModified'] > image_upload_time
            ]
            if recent_annotated:
                progress['step2'] = True
                print(f"Step 2 complete: Found {len(recent_annotated)} recent annotated images")
        
        # Check for validation (step 3)
        validation_response = s3.list_objects_v2(
            Bucket=RESULTS_BUCKET,
            Prefix='validation-'
        )
        if 'Contents' in validation_response:
            recent_validation = [
                obj for obj in validation_response['Contents']
                if obj['LastModified'] > image_upload_time
            ]
            if recent_validation:
                progress['step3'] = True
                print(f"Step 3 complete: Found {len(recent_validation)} recent validations")
        
    except Exception as e:
        print(f"Error checking progress: {str(e)}")
    
    return progress


# --- Project CRUD handlers ---

def _convert_floats(obj):
    """Convert floats to Decimal for DynamoDB compatibility."""
    if isinstance(obj, float):
        return Decimal(str(obj))
    if isinstance(obj, dict):
        return {k: _convert_floats(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_convert_floats(i) for i in obj]
    return obj


def handle_projects_list(headers):
    """Return all projects from DynamoDB."""
    response = projects_table.scan()
    items = response.get('Items', [])
    # Handle pagination
    while 'LastEvaluatedKey' in response:
        response = projects_table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
        items.extend(response.get('Items', []))
    return {
        'statusCode': 200,
        'headers': headers,
        'body': json.dumps(items, cls=DecimalEncoder)
    }


def handle_projects_save(body, headers):
    """Create or update a project in DynamoDB (merge, not replace)."""
    project = body.get('project')
    if not project or not project.get('id'):
        return {
            'statusCode': 400,
            'headers': headers,
            'body': json.dumps({'error': 'project with id is required'})
        }
    item = _convert_floats(project)
    project_id = item.pop('id')

    if not item:
        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps({'saved': project_id})
        }

    # Use update_item to merge fields instead of put_item which replaces the whole record.
    # This prevents race conditions where the frontend overwrites fields set by the orchestrator
    # (e.g. evaluations array getting wiped on re-upload).
    expr_parts = []
    values = {}
    names = {}
    for i, (k, v) in enumerate(item.items()):
        attr = f"#a{i}"
        val = f":v{i}"
        expr_parts.append(f"{attr} = {val}")
        names[attr] = k
        values[val] = v

    projects_table.update_item(
        Key={'projectId': project_id},
        UpdateExpression="SET " + ", ".join(expr_parts),
        ExpressionAttributeNames=names,
        ExpressionAttributeValues=values,
    )
    return {
        'statusCode': 200,
        'headers': headers,
        'body': json.dumps({'saved': project_id})
    }


def handle_projects_delete(body, headers):
    """Delete a project from DynamoDB."""
    project_id = body.get('id')
    if not project_id:
        return {
            'statusCode': 400,
            'headers': headers,
            'body': json.dumps({'error': 'id is required'})
        }
    projects_table.delete_item(Key={'projectId': project_id})
    return {
        'statusCode': 200,
        'headers': headers,
        'body': json.dumps({'deleted': project_id})
    }
