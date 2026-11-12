import json
import os
import re
import boto3
import logging
from datetime import datetime
from decimal import Decimal
from urllib.parse import urlencode

from boto3.dynamodb.conditions import Attr
from botocore.exceptions import ClientError

# Amazon S3 client for presigned URLs and object access
amazon_s3 = boto3.client('s3')
# Amazon DynamoDB resource for project persistence
amazon_dynamodb = boto3.resource('dynamodb')

LOG_LEVEL = os.environ.get("LOG_LEVEL", "WARNING").upper()
logging.basicConfig(level=LOG_LEVEL)
logger = logging.getLogger(__name__)
logger.setLevel(LOG_LEVEL)

INCOMING_BUCKET = os.environ['INCOMING_BUCKET']
RESULTS_BUCKET = os.environ['RESULTS_BUCKET']
CLOUDFRONT_URL = os.environ['CLOUDFRONT_URL']
PROJECTS_TABLE = os.environ['PROJECTS_TABLE']

projects_table = amazon_dynamodb.Table(PROJECTS_TABLE)

OWNER_ATTR = 'ownerSub'


class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, Decimal):
            return int(o) if o == int(o) else float(o)
        return super().default(o)


def _json_response(status_code, headers, payload):
    return {
        'statusCode': status_code,
        'headers': headers,
        'body': json.dumps(payload, cls=DecimalEncoder),
    }


def _not_found(headers):
    # Used for both "does not exist" and "belongs to another user", so callers
    # cannot discover which project IDs exist.
    return _json_response(404, headers, {'error': 'Project not found'})


def _get_caller_sub(event):
    """Return the Cognito `sub` of the caller, or None.

    API Gateway's JWT authorizer validates the token (signature, issuer,
    audience, expiry) before invoking this function and passes the verified
    claims in `requestContext.authorizer.jwt.claims`.
    """
    claims = (
        (event.get('requestContext') or {})
        .get('authorizer', {})
        .get('jwt', {})
        .get('claims')
    ) or {}
    sub = claims.get('sub')
    return sub if isinstance(sub, str) and sub else None


def _get_owned_project(project_id, caller_sub):
    """Return the project record if it exists and belongs to the caller, else None."""
    resp = projects_table.get_item(Key={'projectId': project_id}, ConsistentRead=True)
    item = resp.get('Item')
    if item and item.get(OWNER_ATTR) == caller_sub:
        return item
    return None


def _is_conditional_check_failure(error):
    return error.response.get('Error', {}).get('Code') == 'ConditionalCheckFailedException'


def lambda_handler(event, context):
    # Handle both API Gateway v1 and v2 formats
    path = event.get('rawPath') or event.get('path', '')

    headers = {
        'Access-Control-Allow-Origin': os.environ.get('FRONTEND_ORIGIN', '*'),
        'Access-Control-Allow-Headers': 'Content-Type',
        'Access-Control-Allow-Methods': 'POST, OPTIONS'
    }

    # Handle OPTIONS for CORS
    http_method = event.get('requestContext', {}).get('http', {}).get('method') or event.get('httpMethod', '')
    if http_method == 'OPTIONS':
        return {'statusCode': 200, 'headers': headers, 'body': ''}

    # Every data route is scoped to the authenticated caller. Fail closed if the
    # verified identity is missing (e.g. a route deployed without the authorizer).
    caller_sub = _get_caller_sub(event)
    if not caller_sub:
        logger.warning("Rejected request without caller identity: %s %s", http_method, path)
        return _json_response(401, headers, {'error': 'Unauthorized'})

    logger.info("Request: %s %s", http_method, path)

    try:
        # Parse body
        body_str = event.get('body', '{}')
        if isinstance(body_str, str):
            body = json.loads(body_str) if body_str else {}
        else:
            body = body_str
        if not isinstance(body, dict):
            return _json_response(400, headers, {'error': 'Request body must be a JSON object'})

        if path == '/upload':
            return handle_upload(body, headers, caller_sub)
        elif path == '/check':
            return handle_check(body, headers, caller_sub)
        elif path == '/projects/list':
            return handle_projects_list(headers, caller_sub)
        elif path == '/projects/save':
            return handle_projects_save(body, headers, caller_sub)
        elif path == '/projects/delete':
            return handle_projects_delete(body, headers, caller_sub)
        else:
            return _json_response(404, headers, {'error': f'Not found: {path}'})
    except json.JSONDecodeError:
        return _json_response(400, headers, {'error': 'Invalid JSON body'})
    except Exception as e:
        logger.error("Error handling request: %s", e)
        return _json_response(500, headers, {'error': 'Internal server error'})

def _sanitize_filename(name):
    """Strip path components and unsafe characters from a filename."""
    name = name.split('/')[-1].split('\\')[-1]  # strip path separators
    name = re.sub(r'[^a-zA-Z0-9._-]', '_', name)  # keep only safe chars
    return name[:255] or 'upload'

def handle_upload(body, headers, caller_sub):
    filename = _sanitize_filename(body.get('filename', ''))
    content_type = body.get('contentType', '')
    region = body.get('region', 'US_FDA')
    project_id = body.get('projectId', '')

    if not filename or not content_type:
        return _json_response(400, headers, {'error': 'filename and contentType are required'})

    # Validate content type
    allowed_types = ['image/jpeg', 'image/png', 'image/jpg']
    if content_type not in allowed_types:
        return _json_response(400, headers, {'error': 'Only JPEG and PNG images are allowed'})

    # The pipeline writes its results into the project named here, so the caller
    # must own it. Otherwise one user could overwrite another user's results.
    if not project_id or not isinstance(project_id, str):
        return _json_response(400, headers, {'error': 'projectId is required'})
    if not _get_owned_project(project_id, caller_sub):
        return _not_found(headers)

    # Validate region
    valid_regions = ['US_FDA', 'UK_MHRA']
    if region not in valid_regions:
        logger.warning("Invalid region '%s', defaulting to US_FDA", region)
        region = 'US_FDA'

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    key = f"labels/{region}/{timestamp}_{filename}"

    logger.info("Generating upload URL for: %s", key)
    logger.info("Region: %s, Project: %s", region, project_id)

    # Generate presigned URL with tagging (region + projectId).
    tagging = urlencode({'regulatory_region': region, 'project_id': project_id})
    upload_url = amazon_s3.generate_presigned_url(
        'put_object',
        Params={
            'Bucket': INCOMING_BUCKET,
            'Key': key,
            'ContentType': content_type,
            'Tagging': tagging
        },
        ExpiresIn=300
    )

    return _json_response(200, headers, {
        'uploadUrl': upload_url,
        'key': key,
        'region': region
    })

def handle_check(body, headers, caller_sub):
    project_id = body.get('projectId')
    if not project_id or not isinstance(project_id, str):
        return _json_response(400, headers, {'error': 'projectId is required'})

    item = _get_owned_project(project_id, caller_sub)
    if not item:
        return _not_found(headers)

    if item.get('status') == 'complete':
        return _json_response(200, headers, {
            'status': 'completed',
            'annotatedImageUrl': item.get('annotatedImageUrl', ''),
            'complianceReport': item.get('complianceReport', ''),
            'violations': item.get('formattedViolations', []),
            'progress': item.get('progress', {
                'step1': True, 'step2': True, 'step3': True
            })
        })

    return _json_response(200, headers, {
        'status': 'processing',
        'progress': item.get('progress', {
            'step1': False, 'step2': False, 'step3': False
        })
    })


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


def handle_projects_list(headers, caller_sub):
    """Return the caller's projects from DynamoDB."""
    # Strongly consistent read so a list immediately after a write (e.g. saving a
    # new evaluation, then re-fetching) never returns a stale projects record.
    # Filtered to the caller's own records; records without an owner are never returned.
    scan_kwargs = {
        'FilterExpression': Attr(OWNER_ATTR).eq(caller_sub),
        'ConsistentRead': True,
    }
    response = projects_table.scan(**scan_kwargs)
    items = response.get('Items', [])
    # Handle pagination
    while 'LastEvaluatedKey' in response:
        response = projects_table.scan(
            ExclusiveStartKey=response['LastEvaluatedKey'],
            **scan_kwargs,
        )
        items.extend(response.get('Items', []))
    return _json_response(200, headers, items)


def handle_projects_save(body, headers, caller_sub):
    """Create a project owned by the caller, or merge into one the caller owns."""
    project = body.get('project')
    if not isinstance(project, dict) or not project.get('id') or not isinstance(project.get('id'), str):
        return _json_response(400, headers, {'error': 'project with id is required'})
    item = _convert_floats(project)
    project_id = item.pop('id')
    item.pop('evaluations', None)
    # Never let the client set the key or the owner.
    item.pop('projectId', None)
    item.pop(OWNER_ATTR, None)

    if not item:
        # Nothing to write. The response is the same whoever owns the ID, so it
        # reveals nothing about other users' projects.
        return _json_response(200, headers, {'saved': project_id})

    # Use update_item to merge fields instead of put_item which replaces the whole record.
    # This prevents race conditions where the frontend overwrites fields set by the orchestrator
    # (e.g. evaluations array getting wiped on re-upload).
    expr_parts = ["#owner = :owner"]
    names = {'#owner': OWNER_ATTR}
    values = {':owner': caller_sub}
    for i, (k, v) in enumerate(item.items()):
        attr = f"#a{i}"
        val = f":v{i}"
        expr_parts.append(f"{attr} = {val}")
        names[attr] = k
        values[val] = v

    try:
        projects_table.update_item(
            Key={'projectId': project_id},
            UpdateExpression="SET " + ", ".join(expr_parts),
            # New project, or an existing one owned by the caller.
            ConditionExpression="attribute_not_exists(projectId) OR #owner = :owner",
            ExpressionAttributeNames=names,
            ExpressionAttributeValues=values,
        )
    except ClientError as e:
        if _is_conditional_check_failure(e):
            return _not_found(headers)
        raise
    return _json_response(200, headers, {'saved': project_id})


def handle_projects_delete(body, headers, caller_sub):
    """Delete a project the caller owns."""
    project_id = body.get('id')
    if not project_id or not isinstance(project_id, str):
        return _json_response(400, headers, {'error': 'id is required'})
    try:
        projects_table.delete_item(
            Key={'projectId': project_id},
            ConditionExpression="#owner = :owner",
            ExpressionAttributeNames={'#owner': OWNER_ATTR},
            ExpressionAttributeValues={':owner': caller_sub},
        )
    except ClientError as e:
        if _is_conditional_check_failure(e):
            return _not_found(headers)
        raise
    return _json_response(200, headers, {'deleted': project_id})
