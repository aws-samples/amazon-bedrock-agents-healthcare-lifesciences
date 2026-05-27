import json
import os
import re
import boto3

s3 = boto3.client('s3')
bedrock_agent = boto3.client('bedrock-agent')

KB_BUCKET = os.environ['KB_BUCKET']
KNOWLEDGE_BASE_ID = os.environ.get('KNOWLEDGE_BASE_ID', '')

# Region config: S3 prefix and display name (kb_id and ds_id resolved dynamically)
REGION_CONFIG = {
    'US_FDA': {
        'prefix': 'US_FDA/',
        'name': 'United States — FDA',
        'ds_name': 'US-FDA-Regulatory-Documents',
    },
    'UK_MHRA': {
        'prefix': 'UK_MHRA/',
        'name': 'United Kingdom — MHRA',
        'ds_name': 'UK-MHRA-Regulatory-Documents',
    }
}

# Cache for data source IDs (resolved once per Lambda cold start)
_ds_id_cache = {}

def _get_data_source_id(region_key):
    """Look up the data source ID for a region from the Knowledge Base."""
    if region_key in _ds_id_cache:
        return _ds_id_cache[region_key]
    if not KNOWLEDGE_BASE_ID:
        raise ValueError("KNOWLEDGE_BASE_ID environment variable not set")
    ds_name = REGION_CONFIG[region_key]['ds_name']
    resp = bedrock_agent.list_data_sources(knowledgeBaseId=KNOWLEDGE_BASE_ID)
    for ds in resp.get('dataSourceSummaries', []):
        if ds['name'] == ds_name:
            _ds_id_cache[region_key] = ds['dataSourceId']
            return ds['dataSourceId']
    raise ValueError(f"Data source '{ds_name}' not found in KB {KNOWLEDGE_BASE_ID}")

HEADERS = {
    'Access-Control-Allow-Origin': os.environ.get('FRONTEND_ORIGIN', '*'),
    'Access-Control-Allow-Headers': 'Content-Type',
    'Access-Control-Allow-Methods': 'POST, OPTIONS'
}


def lambda_handler(event, context):
    path = event.get('rawPath') or event.get('path', '')
    http_method = (
        event.get('requestContext', {}).get('http', {}).get('method')
        or event.get('httpMethod', '')
    )

    if http_method == 'OPTIONS':
        return {'statusCode': 200, 'headers': HEADERS, 'body': ''}

    body_str = event.get('body', '{}')
    if isinstance(body_str, str):
        body = json.loads(body_str) if body_str else {}
    else:
        body = body_str

    print(f"Path: {path}, Method: {http_method}, Body keys: {list(body.keys())}")

    try:
        if path == '/documents/list':
            return handle_list(body)
        elif path == '/documents/upload':
            return handle_upload(body)
        elif path == '/documents/delete':
            return handle_delete(body)
        elif path == '/documents/download':
            return handle_download(body)
        elif path == '/documents/sync':
            return handle_sync(body)
        else:
            return response(404, {'error': f'Not found: {path}'})
    except Exception as e:
        print(f"Error: {str(e)}")
        return response(500, {'error': 'Internal server error'})


def response(status_code, body):
    return {
        'statusCode': status_code,
        'headers': HEADERS,
        'body': json.dumps(body)
    }


def handle_list(body):
    """List all documents in S3 for a given region."""
    region = body.get('region')

    if region and region in REGION_CONFIG:
        regions_to_list = {region: REGION_CONFIG[region]}
    else:
        regions_to_list = REGION_CONFIG

    result = {}
    for region_key, config in regions_to_list.items():
        prefix = config['prefix']
        try:
            documents = []
            continuation_token = None
            while True:
                kwargs = {'Bucket': KB_BUCKET, 'Prefix': prefix}
                if continuation_token:
                    kwargs['ContinuationToken'] = continuation_token
                resp = s3.list_objects_v2(**kwargs)
                for obj in resp.get('Contents', []):
                    key = obj['Key']
                    if key.endswith('/'):
                        continue
                    filename = key.split('/')[-1]
                    documents.append({
                        'key': key,
                        'name': filename,
                        'size': obj['Size'],
                        'lastModified': obj['LastModified'].isoformat(),
                        'region': region_key
                    })
                if resp.get('IsTruncated'):
                    continuation_token = resp.get('NextContinuationToken')
                else:
                    break
            result[region_key] = {
                'region': config['name'],
                'documents': documents
            }
        except Exception as e:
            print(f"Error listing {region_key}: {str(e)}")
            result[region_key] = {
                'region': config['name'],
                'documents': [],
                'error': str(e)
            }

    return response(200, result)


def _sanitize_filename(name):
    """Strip path components and unsafe characters from a filename."""
    name = name.split('/')[-1].split('\\')[-1]
    name = re.sub(r'[^a-zA-Z0-9._-]', '_', name)
    return name[:255] or 'upload'

def handle_upload(body):
    """Generate a presigned URL for uploading a document to S3."""
    region = body.get('region')
    filename = _sanitize_filename(body.get('filename', ''))
    content_type = body.get('contentType', 'application/pdf')

    if not region or region not in REGION_CONFIG:
        return response(400, {'error': f'Invalid region: {region}'})
    if not filename:
        return response(400, {'error': 'filename is required'})

    # Validate content type
    allowed_types = ['application/pdf', 'application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'text/plain']
    if content_type not in allowed_types:
        return response(400, {'error': 'Only PDF, DOC, DOCX, and TXT files are allowed'})

    config = REGION_CONFIG[region]
    key = f"{config['prefix']}{filename}"

    # Check if file already exists
    try:
        s3.head_object(Bucket=KB_BUCKET, Key=key)
        return response(409, {'error': f'Document already exists: {filename}'})
    except s3.exceptions.ClientError as e:
        if e.response['Error']['Code'] != '404':
            raise

    upload_url = s3.generate_presigned_url(
        'put_object',
        Params={
            'Bucket': KB_BUCKET,
            'Key': key,
            'ContentType': content_type
        },
        ExpiresIn=300
    )

    print(f"Generated upload URL for: {key}")
    return response(200, {
        'uploadUrl': upload_url,
        'key': key,
        'region': region,
        'filename': filename
    })


def handle_delete(body):
    """Delete a document from S3."""
    key = body.get('key')
    region = body.get('region')

    if not key:
        return response(400, {'error': 'key is required'})
    if not region or region not in REGION_CONFIG:
        return response(400, {'error': f'Invalid region: {region}'})

    # Verify the key belongs to the claimed region
    config = REGION_CONFIG[region]
    if not key.startswith(config['prefix']):
        return response(403, {'error': 'Key does not belong to this region'})

    try:
        s3.head_object(Bucket=KB_BUCKET, Key=key)
    except s3.exceptions.ClientError:
        return response(404, {'error': f'Document not found: {key}'})

    s3.delete_object(Bucket=KB_BUCKET, Key=key)
    print(f"Deleted: {key}")

    return response(200, {
        'deleted': key,
        'region': region
    })


def handle_download(body):
    """Generate a presigned GET URL for downloading a document."""
    key = body.get('key')
    region = body.get('region')

    if not key:
        return response(400, {'error': 'key is required'})
    if not region or region not in REGION_CONFIG:
        return response(400, {'error': f'Invalid region: {region}'})

    config = REGION_CONFIG[region]
    if not key.startswith(config['prefix']):
        return response(403, {'error': 'Key does not belong to this region'})

    try:
        s3.head_object(Bucket=KB_BUCKET, Key=key)
    except s3.exceptions.ClientError:
        return response(404, {'error': f'Document not found: {key}'})

    download_url = s3.generate_presigned_url(
        'get_object',
        Params={'Bucket': KB_BUCKET, 'Key': key},
        ExpiresIn=3600
    )

    return response(200, {
        'downloadUrl': download_url,
        'key': key
    })


def handle_sync(body):
    """Trigger a Bedrock Knowledge Base ingestion job to sync after changes."""
    region = body.get('region')

    if not region or region not in REGION_CONFIG:
        return response(400, {'error': f'Invalid region: {region}'})

    try:
        ds_id = _get_data_source_id(region)
        resp = bedrock_agent.start_ingestion_job(
            knowledgeBaseId=KNOWLEDGE_BASE_ID,
            dataSourceId=ds_id
        )
        job = resp.get('ingestionJob', {})
        print(f"Started ingestion job for {region}: {job.get('ingestionJobId')}")

        return response(200, {
            'region': region,
            'ingestionJobId': job.get('ingestionJobId'),
            'status': job.get('status', 'STARTING')
        })
    except Exception as e:
        print(f"Sync error for {region}: {str(e)}")
        return response(500, {'error': f'Failed to sync: {str(e)}'})
