import json
import os
import re
import boto3
import logging
from datetime import datetime
from decimal import Decimal
from urllib.parse import urlencode, urlparse

from boto3.dynamodb.conditions import Attr
from botocore.config import Config
from botocore.exceptions import ClientError

# Amazon S3 client for presigned URLs and object access
amazon_s3 = boto3.client('s3')
# Signs the annotated-image download URLs with Signature Version 4.
amazon_s3_signer = boto3.client('s3', config=Config(signature_version='s3v4'))
# Amazon DynamoDB resource for project persistence
amazon_dynamodb = boto3.resource('dynamodb')

LOG_LEVEL = os.environ.get("LOG_LEVEL", "WARNING").upper()
logging.basicConfig(level=LOG_LEVEL)
logger = logging.getLogger(__name__)
logger.setLevel(LOG_LEVEL)

INCOMING_BUCKET = os.environ['INCOMING_BUCKET']
RESULTS_BUCKET = os.environ['RESULTS_BUCKET']
PROJECTS_TABLE = os.environ['PROJECTS_TABLE']

projects_table = amazon_dynamodb.Table(PROJECTS_TABLE)

OWNER_ATTR = 'ownerSub'
VALID_REGIONS = ('US_FDA', 'UK_MHRA')

# Project IDs become part of S3 keys (labels/<region>/<projectId>/...), so they
# are limited to letters, digits, and hyphens (UUIDs and legacy numeric IDs).
PROJECT_ID_RE = re.compile(r'^[A-Za-z0-9-]{1,64}$')

SERVER_OWNED_FIELDS = (
    'projectId', OWNER_ATTR, 'evaluations', 'imageKey', 'reportKey',
    'annotatedKey', 'validationKey', 'annotatedImageUrl',
)

# Annotated images are private. The API returns short-lived presigned GET URLs
# for them, and only after the ownership check.
ANNOTATED_KEY_RE = re.compile(r'^annotated-[A-Za-z0-9_.-]+\.png$')
RESULT_KEY_RE = re.compile(r'^(annotated|validation|compliance-report|completion)-[A-Za-z0-9_.-]+$')
IMAGE_URL_TTL_SECONDS = 3600


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


def _denied(headers, caller_sub, action, project_id):
    # Logged with the caller's sub so cross-user attempts can be attributed.
    logger.warning("Denied %s: project %s not found or not owned by sub=%s", action, project_id, caller_sub)
    return _not_found(headers)


def _valid_project_id(project_id):
    return isinstance(project_id, str) and bool(PROJECT_ID_RE.match(project_id))


def _annotated_image_url(key):
    """Presigned GET URL for an annotated image key, or '' if the key is not one."""
    if not isinstance(key, str) or not ANNOTATED_KEY_RE.match(key):
        return ''
    return amazon_s3_signer.generate_presigned_url(
        'get_object',
        Params={'Bucket': RESULTS_BUCKET, 'Key': key},
        ExpiresIn=IMAGE_URL_TTL_SECONDS,
    )


def _legacy_annotated_key(url):
    """Annotated image key from a stored URL (evaluations written before keys were stored)."""
    if not isinstance(url, str):
        return None
    path = urlparse(url).path.lstrip('/')
    return path if ANNOTATED_KEY_RE.match(path) else None


def _evaluation_annotated_key(evaluation):
    return evaluation.get('annotatedKey') or _legacy_annotated_key(evaluation.get('annotatedImageUrl'))


def _with_image_urls(item):
    """Copy of a project record with fresh presigned URLs for its annotated images."""
    out = dict(item)
    url = _annotated_image_url(item.get('annotatedKey'))
    if url:
        out['annotatedImageUrl'] = url
    else:
        out.pop('annotatedImageUrl', None)
    if isinstance(item.get('evaluations'), list):
        evaluations = []
        for evaluation in item['evaluations']:
            if isinstance(evaluation, dict):
                evaluation = dict(evaluation)
                evaluation['annotatedImageUrl'] = _annotated_image_url(_evaluation_annotated_key(evaluation))
            evaluations.append(evaluation)
        out['evaluations'] = evaluations
    return out


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

    # The pipeline writes its results into the project named here, so the caller must own it.
    if not _valid_project_id(project_id):
        return _json_response(400, headers, {'error': 'projectId is required'})
    if not _get_owned_project(project_id, caller_sub):
        return _denied(headers, caller_sub, 'upload', project_id)

    # Validate region
    if region not in VALID_REGIONS:
        logger.warning("Invalid region '%s', defaulting to US_FDA", region)
        region = 'US_FDA'

    # Uploads are grouped under the project ID so they can be deleted with the project.
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    key = f"labels/{region}/{project_id}/{timestamp}_{filename}"

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
    if not _valid_project_id(project_id):
        return _json_response(400, headers, {'error': 'projectId is required'})

    item = _get_owned_project(project_id, caller_sub)
    if not item:
        return _denied(headers, caller_sub, 'check', project_id)

    if item.get('status') == 'complete':
        return _json_response(200, headers, {
            'status': 'completed',
            'annotatedImageUrl': _annotated_image_url(item.get('annotatedKey')),
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
    return _json_response(200, headers, [_with_image_urls(item) for item in items])


def handle_projects_save(body, headers, caller_sub):
    """Create a project owned by the caller, or merge into one the caller owns."""
    project = body.get('project')
    if not isinstance(project, dict) or not _valid_project_id(project.get('id')):
        return _json_response(400, headers, {'error': 'project with id is required'})
    item = _convert_floats(project)
    project_id = item.pop('id')
    # Never let the client set the key, the owner, or any S3 key the API acts on.
    for field in SERVER_OWNED_FIELDS:
        item.pop(field, None)

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
            return _denied(headers, caller_sub, 'save', project_id)
        raise
    return _json_response(200, headers, {'saved': project_id})


def handle_projects_delete(body, headers, caller_sub):
    """Delete a project the caller owns, then its label uploads and pipeline results."""
    project_id = body.get('id')
    if not _valid_project_id(project_id):
        return _json_response(400, headers, {'error': 'id is required'})
    try:
        resp = projects_table.delete_item(
            Key={'projectId': project_id},
            ConditionExpression="#owner = :owner",
            ExpressionAttributeNames={'#owner': OWNER_ATTR},
            ExpressionAttributeValues={':owner': caller_sub},
            ReturnValues='ALL_OLD',
        )
    except ClientError as e:
        if _is_conditional_check_failure(e):
            return _denied(headers, caller_sub, 'delete', project_id)
        raise

    # The record is already gone, so a cleanup failure must not fail the request.
    # Leftover objects are unreachable: the API no longer references them.
    try:
        _delete_project_objects(project_id, resp.get('Attributes') or {})
    except Exception as e:
        logger.error("Could not delete S3 objects for project %s: %s", project_id, e)
    return _json_response(200, headers, {'deleted': project_id})


def _delete_keys(bucket, keys):
    keys = sorted(set(keys))
    for start in range(0, len(keys), 1000):
        amazon_s3.delete_objects(
            Bucket=bucket,
            Delete={'Objects': [{'Key': k} for k in keys[start:start + 1000]], 'Quiet': True},
        )


def _delete_project_objects(project_id, item):
    """Delete a project's label uploads and pipeline results.

    Only keys from server-written fields are used, and every key is checked
    against the expected naming pattern before deletion.
    """
    evaluations = [e for e in (item.get('evaluations') or []) if isinstance(e, dict)]

    # Pipeline results (results bucket).
    result_keys = {item.get('annotatedKey'), item.get('reportKey'), item.get('validationKey')}
    for evaluation in evaluations:
        result_keys.add(_evaluation_annotated_key(evaluation))
        result_keys.update(evaluation.get('artifactKeys') or [])
    _delete_keys(RESULTS_BUCKET, [k for k in result_keys if isinstance(k, str) and RESULT_KEY_RE.match(k)])

    # Label uploads (incoming bucket): everything under the project's prefix.
    incoming_keys = set()
    paginator = amazon_s3.get_paginator('list_objects_v2')
    for region in VALID_REGIONS:
        for page in paginator.paginate(Bucket=INCOMING_BUCKET, Prefix=f"labels/{region}/{project_id}/"):
            incoming_keys.update(obj['Key'] for obj in page.get('Contents', []))

    # Uploads made before keys included the project ID. Delete only those whose
    # signed project_id tag matches this project.
    legacy_keys = {item.get('imageKey')} | {e.get('imageKey') for e in evaluations}
    for key in legacy_keys:
        if not isinstance(key, str) or not key.startswith('labels/') or key in incoming_keys:
            continue
        try:
            tags = amazon_s3.get_object_tagging(Bucket=INCOMING_BUCKET, Key=key).get('TagSet', [])
        except ClientError:
            continue
        if any(t.get('Key') == 'project_id' and t.get('Value') == project_id for t in tags):
            incoming_keys.add(key)
    _delete_keys(INCOMING_BUCKET, incoming_keys)
