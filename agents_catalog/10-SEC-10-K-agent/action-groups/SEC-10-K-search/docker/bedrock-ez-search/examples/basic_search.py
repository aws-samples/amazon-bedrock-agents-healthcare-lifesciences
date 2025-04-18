"""
Basic example of using bedrock-ez-search for semantic search
"""

from bedrock_ez_search import SemanticSearch

def main():
    # Initialize the search engine
    search = SemanticSearch(
        model_id="amazon.titan-embed-text-v1",  # Default model
        region_name="us-east-1",  # Optional, change to your region
        profile_name="default"    # Optional, change to your profile
    )

    # Index your documents
    documents = [
        "Amazon Bedrock is a fully managed service that offers a choice of high-performing foundation models.",
        "Amazon S3 is an object storage service offering industry-leading scalability.",
        "Amazon EC2 provides secure and resizable compute capacity in the cloud.",
        "AWS Lambda lets you run code without provisioning or managing servers."
    ]
    search.index(documents)

    # Search for semantically similar documents
    query = "serverless computing options"
    results = search.search(query, top_k=2)

    # Print results
    print(f"Query: {query}\n")
    for result in results:
        print(f"Score: {result['score']:.4f} | {result['document']}")


if __name__ == "__main__":
    main()
