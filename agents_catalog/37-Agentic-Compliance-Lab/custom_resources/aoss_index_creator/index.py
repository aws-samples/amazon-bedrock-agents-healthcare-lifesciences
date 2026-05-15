"""Custom resource Lambda to create a vector index in an OpenSearch Serverless collection."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "deps"))

import json
import urllib.request
import time
import traceback
import boto3
from opensearchpy import OpenSearch, RequestsHttpConnection, AWSV4SignerAuth


def handler(event, context):
    try:
        if event["RequestType"] == "Delete":
            _send(event, context, "SUCCESS")
            return

        props = event["ResourceProperties"]
        endpoint = props["CollectionEndpoint"].replace("https://", "")
        region = props["Region"]
        index_name = props["IndexName"]
        dimension = int(props.get("Dimension", "1024"))

        print(f"Creating index '{index_name}' on endpoint '{endpoint}' in region '{region}' with dimension {dimension}")

        session = boto3.Session()
        credentials = session.get_credentials()
        auth = AWSV4SignerAuth(credentials, region, "aoss")

        client = OpenSearch(
            hosts=[{"host": endpoint, "port": 443}],
            http_auth=auth,
            use_ssl=True,
            verify_certs=True,
            connection_class=RequestsHttpConnection,
            timeout=30,
        )

        if client.indices.exists(index=index_name):
            print(f"Index '{index_name}' already exists, skipping creation")
        else:
            print(f"Creating index '{index_name}'...")
            client.indices.create(
                index=index_name,
                body={
                    "settings": {
                        "index": {"knn": True},
                    },
                    "mappings": {
                        "properties": {
                            "bedrock-knowledge-base-default-vector": {
                                "type": "knn_vector",
                                "dimension": dimension,
                                "method": {
                                    "engine": "faiss",
                                    "name": "hnsw",
                                },
                            },
                            "AMAZON_BEDROCK_TEXT_CHUNK": {"type": "text"},
                            "AMAZON_BEDROCK_METADATA": {"type": "text"},
                        }
                    },
                },
            )
            print(f"Index '{index_name}' created successfully")

        # Verify the index exists with stabilization delay
        # AOSS indexes need time to become visible to other AWS services (e.g., Bedrock)
        for verify_attempt in range(10):
            if client.indices.exists(index=index_name):
                print(f"Verified: index '{index_name}' exists (attempt {verify_attempt + 1})")
                if verify_attempt == 0:
                    print("Waiting 30s for index to stabilize across AWS services...")
                    time.sleep(30)
                _send(event, context, "SUCCESS")
                return
            print(f"Verify attempt {verify_attempt + 1}: index not found yet, waiting...")
            time.sleep(10)

        raise Exception(f"Index '{index_name}' was created but could not be verified after 30 seconds")

    except Exception as e:
        print(f"Error: {e}")
        traceback.print_exc()
        _send(event, context, "FAILED", str(e))


def _send(event, context, status, reason=""):
    body = json.dumps({
        "Status": status,
        "Reason": reason or "See CloudWatch logs",
        "PhysicalResourceId": context.log_stream_name,
        "StackId": event["StackId"],
        "RequestId": event["RequestId"],
        "LogicalResourceId": event["LogicalResourceId"],
    })
    req = urllib.request.Request(event["ResponseURL"], data=body.encode(), method="PUT")
    req.add_header("Content-Type", "")
    urllib.request.urlopen(req)
