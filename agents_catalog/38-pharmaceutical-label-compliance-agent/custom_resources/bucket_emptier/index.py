import json
import os
import time
import boto3
import urllib.request
from botocore.exceptions import ClientError


def _send(event, status, reason, physical_id):
    """Send the response document back to the CloudFormation pre-signed URL."""
    body = json.dumps({
        'Status': status,
        'Reason': reason or 'OK',
        'PhysicalResourceId': physical_id,
        'StackId': event['StackId'],
        'RequestId': event['RequestId'],
        'LogicalResourceId': event['LogicalResourceId'],
    }).encode()

    response_url = event['ResponseURL']
    if not response_url.startswith('https://'):
        raise ValueError(f"ResponseURL must use HTTPS scheme, got: {response_url[:20]}")
    req = urllib.request.Request(response_url, data=body, method='PUT')
    req.add_header('Content-Type', '')
    req.add_header('Content-Length', str(len(body)))
    urllib.request.urlopen(req)


def _empty_bucket(s3_client, bucket):
    """Delete every object, version, and delete-marker in the bucket.

    Returns the number of items deleted so callers can tell whether new
    objects (e.g. late-arriving CloudFront logs) showed up between passes.
    """
    deleted = 0
    paginator = s3_client.get_paginator('list_object_versions')
    for page in paginator.paginate(Bucket=bucket):
        batch = []
        for item in page.get('Versions', []) + page.get('DeleteMarkers', []):
            batch.append({'Key': item['Key'], 'VersionId': item['VersionId']})
            if len(batch) == 1000:  # S3 delete_objects hard limit
                s3_client.delete_objects(Bucket=bucket, Delete={'Objects': batch, 'Quiet': True})
                deleted += len(batch)
                batch = []
        if batch:
            s3_client.delete_objects(Bucket=bucket, Delete={'Objects': batch, 'Quiet': True})
            deleted += len(batch)
    return deleted


def _bucket_exists(s3_client, bucket):
    try:
        s3_client.head_bucket(Bucket=bucket)
        return True
    except ClientError as e:
        if e.response['Error']['Code'] in ('404', 'NoSuchBucket'):
            return False
        # 403 or other: assume it still exists but we can't confirm.
        raise


def _teardown(s3_client, bucket, deadline_ts):
    """Empty + delete the bucket, tolerating CloudFront's asynchronous log flush.

    CloudFront can keep delivering buffered access logs for a while after its
    distribution is gone, so a single empty->delete can still hit
    "bucket not empty". We repeatedly empty until the bucket stays empty across
    consecutive passes, then delete and verify, all within the time budget.

    Returns True if the bucket was confirmed deleted, False if we ran out of
    time (caller decides how to degrade).
    """
    stable_empty_passes = 0
    while time.time() < deadline_ts:
        deleted = _empty_bucket(s3_client, bucket)
        if deleted == 0:
            stable_empty_passes += 1
        else:
            stable_empty_passes = 0
            print(f"Removed {deleted} object(s); waiting for late writes to settle.")

        # Require two consecutive empty passes so we don't race a log flush
        # that lands between the last list and the DeleteBucket call.
        if stable_empty_passes >= 2:
            try:
                s3_client.delete_bucket(Bucket=bucket)
            except ClientError as e:
                code = e.response['Error']['Code']
                if code == 'NoSuchBucket':
                    return True
                if code == 'BucketNotEmpty':
                    # A log file slipped in; reset and keep draining.
                    print("DeleteBucket hit BucketNotEmpty; retrying empty loop.")
                    stable_empty_passes = 0
                    continue
                raise
            if not _bucket_exists(s3_client, bucket):
                print(f"Bucket {bucket} confirmed deleted.")
                return True
            # Delete reported success but bucket still visible: loop again.
            stable_empty_passes = 0

        # Pause between passes to let any in-flight log delivery arrive.
        time.sleep(15)

    return False


def handler(event, context):
    request_type = event['RequestType']
    props = event.get('ResourceProperties', {})
    bucket = props.get('BucketName')
    physical_id = event.get('PhysicalResourceId', bucket or 'BucketEmptier')

    status = 'SUCCESS'
    reason = 'OK'

    try:
        # Only Delete needs to do work. Create/Update are no-ops so the custom
        # resource simply tracks the bucket it is responsible for.
        if request_type == 'Delete' and bucket:
            s3_client = boto3.client('s3', region_name=os.environ.get('AWS_REGION', 'us-east-1'))

            if not _bucket_exists(s3_client, bucket):
                print(f"Bucket {bucket} already gone; nothing to do.")
            else:
                # Reserve ~45s of the remaining Lambda time to send the CFN
                # response so we never time out mid-request.
                deadline_ts = time.time() + max(
                    0, context.get_remaining_time_in_millis() / 1000.0 - 45
                )
                if not _teardown(s3_client, bucket, deadline_ts):
                    # Graceful degradation: the bucket is RemovalPolicy.RETAIN,
                    # so returning SUCCESS leaves an orphan rather than blocking
                    # the whole stack teardown. CloudFront logs on it expire via
                    # the bucket lifecycle rule and it can be removed manually.
                    reason = (
                        f"Timed out draining {bucket} (likely ongoing CloudFront "
                        f"log delivery); leaving retained bucket to avoid blocking "
                        f"stack deletion."
                    )
                    print(reason)

    except Exception as e:  # never let an error block teardown
        # Even on unexpected errors we report SUCCESS on Delete so a retained
        # bucket cannot wedge the stack in DELETE_FAILED. The failure is logged.
        print(f"Error during {request_type}: {e}")
        if request_type == 'Delete':
            reason = f"Ignored error during delete: {e}"
        else:
            status = 'FAILED'
            reason = str(e)

    _send(event, status, reason, physical_id)
