import boto3
import json
from typing import List, Dict

class OMOPOntology():

    def __init__(self, graph_id, region_name):
        self.graph_id = graph_id
        self.neptune_client = self.connect_to_neptune_analytics(graph_id, region_name)
        self.bedrock_client = boto3.client('bedrock-runtime', region_name=region_name)

    def connect_to_neptune_analytics(self, graph_id, region_name):
        try:
            client = boto3.client('neptune-graph', region_name=region_name)
            response = client.get_graph(graphIdentifier=graph_id)

            print(f"Connected to Neptune graph: {graph_id}")
            query_response = client.execute_query(
                graphIdentifier=graph_id,
                language='OPENCYPHER',
                queryString='MATCH (n) RETURN count(n) as count LIMIT 1'
            )

            print(f"Query test successful: {json.loads(query_response['payload'].read().decode('utf-8'))}")
            return client

        except Exception as e:
            print(f"Error connecting to Neptune Analytics: {e}")
            raise e


    def find_similar_fields(self, input_text: str, top_k: int = 5):
        """
        Find similar OMOP fields using vector similarity
        """
        print(f"Finding top {top_k} similar OMOP fields for: {input_text}")
        try:
            body = json.dumps({"inputText": input_text})

            response = self.bedrock_client.invoke_model(
                modelId="amazon.titan-embed-text-v2:0",
                body=body,
                accept='application/json',
                contentType='application/json'
            )

            response_body = json.loads(response['body'].read())
            query_embedding = response_body['embedding']

            similarity_query = f"""
            CALL neptune.algo.vectors.topKByEmbedding(
                {query_embedding},
                {{
                    topK: {top_k},
                    concurrency: 1
                }}
            )
            YIELD embedding, node, score
            WHERE node:Field
            RETURN node.`~id` AS id,
                   node.name AS fieldName,
                   node.table AS tableName,
                   node.enriched_text AS enrichedText,
                   score
            ORDER BY score DESC
            """

            result = self.neptune_client.execute_query(
                graphIdentifier=self.graph_id,
                language='OPENCYPHER',
                queryString=similarity_query
            )

            results = json.loads(result['payload'].read())
            return results.get('results', [])

        except Exception as e:
            print(f"Error in find_similar_fields: {e}")
            raise e


    def get_table_fields(self, table_name: str) -> List[Dict]:
        """
        Get all fields for a given OMOP table
        """
        try:
            query = f"""
            MATCH (t:Table {{name: "{table_name}"}})-[:HAS_FIELD]->(f:Field)
            RETURN f.name AS fieldName, 
                   f.cdmDatatype AS dataType,
                   f.userGuidance AS userGuidance,
                   f.enriched_text AS enrichedText
            ORDER BY fieldName
            """
            result = self.neptune_client.execute_query(
                graphIdentifier=self.graph_id,
                language='OPENCYPHER',
                queryString=query
            )
            return json.loads(result['payload'].read()).get('results', [])

        except Exception as e:
            print(f"Error fetching fields for table {table_name}: {e}")
            raise e

    def connect(self):
        ontology_summary = self.neptune_client.get_graph_summary(
            graphIdentifier=self.graph_id
        )
        return ontology_summary

    def get_foreign_keys(self, field_name: str, table_name: str) -> List[Dict]:
        """
        Follow foreign key links from a specific field
        """
        try:
            query = f"""
            MATCH (f:Field {{name: "{field_name}", table: "{table_name}"}})
                  -[:IS_FOREIGN_KEY_TO]->(target:Field)
            RETURN f.name AS sourceField,
                   f.table AS sourceTable,
                   target.name AS targetField,
                   target.table AS targetTable
            """
            result = self.neptune_client.execute_query(
                graphIdentifier=self.graph_id,
                language='OPENCYPHER',
                queryString=query
            )
            return json.loads(result['payload'].read()).get('results', [])

        except Exception as e:
            print(f"Error fetching foreign keys: {e}")
            raise e


    def list_all_tables(self) -> List[str]:
        """
        List all OMOP tables
        """
        try:
            query = "MATCH (t:Table) RETURN t.name AS tableName ORDER BY tableName"
            result = self.neptune_client.execute_query(
                graphIdentifier=self.graph_id,
                language='OPENCYPHER',
                queryString=query
            )
            records = json.loads(result['payload'].read()).get('results', [])
            return [r['tableName'] for r in records]
        except Exception as e:
            print(f"Error listing tables: {e}")
            raise e
