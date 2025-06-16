"""
Advanced example of using bedrock-ez-search for semantic search
"""

from bedrock_ez_search import SemanticSearch

def main():
    # Initialize the search engine with a different model
    search = SemanticSearch(
        model_id="amazon.titan-embed-text-v2:0",  # Using v2 model
        region_name="us-east-1",  # Optional, change to your region
        profile_name="default"    # Optional, change to your profile
    )

    # Index a larger set of documents
    documents = [
        "Amazon Bedrock is a fully managed service that offers a choice of high-performing foundation models.",
        "Amazon S3 is an object storage service offering industry-leading scalability.",
        "Amazon EC2 provides secure and resizable compute capacity in the cloud.",
        "AWS Lambda lets you run code without provisioning or managing servers.",
        "Amazon DynamoDB is a key-value and document database that delivers single-digit millisecond performance at any scale.",
        "Amazon RDS makes it easy to set up, operate, and scale a relational database in the cloud.",
        "Amazon SageMaker is a fully managed machine learning service.",
        "AWS Step Functions is a serverless orchestration service.",
        "Amazon API Gateway is a fully managed service for creating, publishing, and securing APIs.",
        "AWS CloudFormation provides a common language to model and provision AWS resources in your cloud environment."
    ]
    search.index(documents)

    # Perform multiple searches
    queries = [
        "serverless computing options",
        "database services for web applications",
        "machine learning on AWS",
        "infrastructure as code"
    ]
    
    for query in queries:
        print(f"\nQuery: {query}")
        print("-" * 50)
        
        results = search.search(query, top_k=3)
        
        for i, result in enumerate(results, 1):
            print(f"{i}. Score: {result['score']:.4f} | {result['document']}")


if __name__ == "__main__":
    main()
