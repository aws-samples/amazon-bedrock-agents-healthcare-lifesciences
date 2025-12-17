import boto3
import os

dynamodb = boto3.resource("dynamodb")


def create_evidence_table(table_name: str = "deep-research-evidence"):
    # Check if table exists
    try:
        ddb_table = dynamodb.Table(table_name)
        ddb_table.load()
        print(f"Table '{table_name}' already exists")
    except:
        # Create table if it doesn't exist
        ddb_table = dynamodb.create_table(
            TableName=table_name,
            KeySchema=[{"AttributeName": "evidence_id", "KeyType": "HASH"}],
            AttributeDefinitions=[
                {"AttributeName": "evidence_id", "AttributeType": "S"},
                {"AttributeName": "source", "AttributeType": "S"},
            ],
            GlobalSecondaryIndexes=[
                {
                    "IndexName": "source_index",
                    "KeySchema": [{"AttributeName": "source", "KeyType": "HASH"}],
                    "Projection": {"ProjectionType": "ALL"},
                }
            ],
            BillingMode="PAY_PER_REQUEST",
        )

        ddb_table.wait_until_exists()
    return ddb_table


def format_evidence(records):
    for record in records:
        print("-" * 50)
        print(f"Evidence ID: {record.get('evidence_id')}")
        print(f"Question: {record.get('question')}")
        print(f"Answer: {record.get('answer')}")
        print(f"Source: {record.get('source')}")
        print("Context:")
        for i, item in enumerate(record.get("context"), start=1):
            print(f"  {i}: {item}")

def print_cited_response(response_content: dict) -> None:
    citations = []
    for content_item in response_content:
        print(content_item.get("text"), end="")
        for citation in content_item.get("citations", []):
            title = citation.get("document_title")
            if title not in citations:
                citations.append(title)
            print(f" ({citations.index(title)+1})", end="")

    print("\n")
    print("## References")
    for i, title in enumerate(citations, start=1):
        print(f"{i}. https://www.ncbi.nlm.nih.gov/pmc/articles/{title}")
    return None
