import boto3
import pandas as pd
import json
from typing import List, Dict
from botocore.exceptions import ClientError

def connect_to_neptune_analytics(graph_id, region_name):
    try:
        client = boto3.client('neptune-graph', region_name=region_name)
        response = client.get_graph(graphIdentifier=graph_id)

        print(f"Graph response: {response}")
        
        query_response = client.execute_query(
            graphIdentifier=graph_id,
            language='OPENCYPHER',
            queryString='MATCH (n) RETURN count(n) as count LIMIT 1'
        )

        print("Connection successful!")
        print(f"Query result: {json.loads(query_response['payload'].read().decode('utf-8'))}")
        return client
    except Exception as e:
        print(f"Error connecting to Neptune Analytics: {e}")
        raise e

def get_embedding(text: str, bedrock_client) -> List[float]:
    """
    Get embeddings using Amazon Bedrock (Claude/Titan)
    """
    try:
        # Using Claude/Titan for embeddings
        body = json.dumps({
            "inputText": text
        })
        
        response = bedrock_client.invoke_model(
            modelId="amazon.titan-embed-text-v2:0",
            body=body
        )
        
        response_body = json.loads(response['body'].read())
        embedding = response_body['embedding']
        
        return embedding
        
    except Exception as e:
        print(f"Error getting embedding for text: {e}")
        raise e

def enrich_omop_field_text(field_name, table_name, field_desc, table_desc, etl_conventions, data_type):
    return f"""
    Field: {field_name}
    Table: {table_name}
    Field Description: {field_desc or 'N/A'}
    Table Description: {table_desc or 'N/A'}
    ETL Conventions: {etl_conventions or 'N/A'}
    Data Type: {data_type or 'N/A'}
    """.strip()


def add_omop_field_embeddings(neptune_client, bedrock_client, graph_id):
    print("Fetching field + table info from Neptune...")

    query = """
    MATCH (t:Table)-[:HAS_FIELD]->(f:Field)
    RETURN f.`~id` AS fieldId, f.name AS fieldName, f.cdmDatatype AS dataType,
           f.userGuidance AS fieldDesc, f.etlConventions AS etlConventions,
           t.name AS tableName, t.tableDescription AS tableDesc
    """

    response = neptune_client.execute_query(
        graphIdentifier=graph_id,
        language='OPENCYPHER',
        queryString=query
    )

    records = json.loads(response['payload'].read().decode('utf-8'))

    print(f"Total fields found: {len(records)}")

    for i, node in enumerate(records['results']):
        if i % 50 == 0:
            print(f"Embedding node {i}/{len(records)}")
        print(node)
        # Prepare enriched text for embedding
        enriched_text = enrich_omop_field_text(
            field_name=node['fieldName'],
            table_name=node['tableName'],
            field_desc=node.get('fieldDesc', ''),
            table_desc=node.get('tableDesc', ''),
            etl_conventions=node.get('etlConventions', ''),
            data_type=node.get('dataType', '')
        )

        # Call embedding function (you already have this)
        embedding = get_embedding(enriched_text, bedrock_client)

        # Save embedding into vector index
        update_embedding_query = f"""
        CALL neptune.algo.vectors.upsert(
            '{node['fieldId']}',
            {embedding}
        )
        YIELD node, embedding, success
        RETURN node, embedding, success
        """

        neptune_client.execute_query(
            graphIdentifier=graph_id,
            language='OPENCYPHER',
            queryString=update_embedding_query
        )

        # Save enriched text back to node
        set_text_query = """
        MATCH (f:Field {`~id`: $node_id})
        SET f.enriched_text = $enriched_text
        RETURN f.`~id` AS node_id
        """

        neptune_client.execute_query(
            graphIdentifier=graph_id,
            language='OPENCYPHER',
            queryString=set_text_query,
            parameters={'node_id': node['fieldId'], 'enriched_text': enriched_text}
        )

    print("✅ All embeddings and enriched text saved to Neptune.")


def ingest_table_metadata(client, graph_id, table_df):
    for _, row in table_df.iterrows():
        table = row['cdmTableName']
        props = {
            'schema': row.get('schema', 'NA'),
            'isRequired': row.get('isRequired', 'NA'),
            'conceptPrefix': row.get('conceptPrefix', 'NA'),
            'measurePersonCompleteness': row.get('measurePersonCompleteness', 'NA'),
            'measurePersonCompletenessThreshold': row.get('measurePersonCompletenessThreshold', 'NA'),
            'validation': row.get('validation', 'NA'),
            'tableDescription': row.get('tableDescription', '').replace('"', '\\"'),
            'userGuidance': str(row.get('userGuidance', '') or '').replace('"', '\\"'),
            'etlConventions': str(row.get('etlConventions', '') or '').replace('"', '\\"')
        }

        query = f"""
        MERGE (t:Table {{
            name: "{table}",
            schema: "{props['schema']}",
            isRequired: "{props['isRequired']}",
            conceptPrefix: "{props['conceptPrefix']}",
            measurePersonCompleteness: "{props['measurePersonCompleteness']}",
            measurePersonCompletenessThreshold: "{props['measurePersonCompletenessThreshold']}",
            validation: "{props['validation']}",
            tableDescription: "{props['tableDescription']}",
            userGuidance: "{props['userGuidance']}",
            etlConventions: "{props['etlConventions']}"
        }})
        """
        client.execute_query(
            graphIdentifier=graph_id,
            language='OPENCYPHER',
            queryString=query
        )
    print("✅ Table metadata ingested.")


def ingest_field_metadata(client, graph_id, field_df):
    for _, row in field_df.iterrows():
        table = row['cdmTableName']
        field = row['cdmFieldName']
        props = {
            'isRequired': row.get('isRequired', 'NA'),
            'cdmDatatype': row.get('cdmDatatype', 'NA'),
            'userGuidance': str(row.get('userGuidance', '') or '').replace('"', '\\"'),
            'etlConventions': str(row.get('etlConventions', '') or '').replace('"', '\\"'),
            'isPrimaryKey': row.get('isPrimaryKey', 'NA'),
            'isForeignKey': row.get('isForeignKey', 'NA'),
            'fkTableName': row.get('fkTableName', 'NA'),
            'fkFieldName': row.get('fkFieldName', 'NA'),
            'fkDomain': row.get('fkDomain', 'NA'),
            'fkClass': row.get('fkClass', 'NA')
        }

        # Create Field node and HAS_FIELD relationship
        query = f"""
        MERGE (f:Field {{
            name: "{field}",
            table: "{table}",
            isRequired: "{props['isRequired']}",
            cdmDatatype: "{props['cdmDatatype']}",
            userGuidance: "{props['userGuidance']}",
            etlConventions: "{props['etlConventions']}",
            isPrimaryKey: "{props['isPrimaryKey']}",
            isForeignKey: "{props['isForeignKey']}",
            fkTableName: "{props['fkTableName']}",
            fkFieldName: "{props['fkFieldName']}",
            fkDomain: "{props['fkDomain']}",
            fkClass: "{props['fkClass']}"
        }})
        WITH f
        MATCH (t:Table {{name: "{table}"}})
        MERGE (t)-[:HAS_FIELD]->(f)
        """
        client.execute_query(
            graphIdentifier=graph_id,
            language='OPENCYPHER',
            queryString=query
        )

        # Create IS_FOREIGN_KEY_TO relationship if foreign key info is present
        if str(props['isForeignKey']).lower() == 'yes' and props['fkTableName'] != 'NA' and props['fkFieldName'] != 'NA':
            fk_query = f"""
            MATCH (f1:Field {{name: "{field}", table: "{table}"}})
            MATCH (f2:Field {{name: "{props['fkFieldName']}", table: "{props['fkTableName']}"}})
            MERGE (f1)-[:IS_FOREIGN_KEY_TO]->(f2)
            """
            client.execute_query(
                graphIdentifier=graph_id,
                language='OPENCYPHER',
                queryString=fk_query
            )

    print("✅ Field metadata and relationships (HAS_FIELD, IS_FOREIGN_KEY_TO) ingested.")

def main(graph_id: str, omop_table_file: str, omop_field_file: str = None, region_name: str = 'us-west-2'):
    """
    Main function to load OMOP data into Neptune Analytics
    
    Args:
        graph_id: Neptune Analytics Graph ID
        omop_table_file: Path to OMOP table level CSV file
        omop_field_file: Path to OMOP field level CSV file (optional)
        region_name: AWS region name (default: us-west-2)
    """
    print(f"Connecting to Neptune Analytics Graph: {graph_id}")
    neptune_client = connect_to_neptune_analytics(graph_id, region_name)
    bedrock_client = boto3.client('bedrock-runtime', region_name=region_name)

    print(f"Loading table metadata from: {omop_table_file}")
    table_df = pd.read_csv(omop_table_file)
    ingest_table_metadata(neptune_client, graph_id, table_df)

    print(f"Loading field metadata from: {omop_field_file}")
    field_df = pd.read_csv(omop_field_file)
    ingest_field_metadata(neptune_client, graph_id, field_df)

    print("Adding embeddings to OMOP fields...")
    add_omop_field_embeddings(neptune_client, bedrock_client, graph_id)
    print("✅ OMOP data loading completed successfully!")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Load OMOP data into Neptune Analytics')
    parser.add_argument('--graph-id', required=True, help='Neptune Analytics Graph ID')
    parser.add_argument('--table-file', required=True, help='Path to OMOP table level CSV file')
    parser.add_argument('--field-file', required=True, help='Path to OMOP field level CSV file')
    parser.add_argument('--region', default='us-east-1', help='AWS region (default: us-east-1)')
    
    args = parser.parse_args()
    
    main(
        graph_id=args.graph_id,
        omop_table_file=args.table_file,
        omop_field_file=args.field_file,
        region_name=args.region
    )

