# bedrock-ez-search

A lightweight Python library for semantic search over a list of strings using Amazon Bedrock embedding models.

## Features

- Simple API for semantic search
- Uses Amazon Bedrock for high-quality text embeddings
- Minimal dependencies (only boto3, numpy, and scikit-learn)
- Fast cosine similarity search

## Installation

```bash
pip install bedrock-ez-search
```

## Usage

```python
from bedrock_ez_search import SemanticSearch

# Initialize the search engine
search = SemanticSearch(
    model_id="amazon.titan-embed-text-v1",  # Default model
    region_name="us-east-1",  # Optional
    profile_name="default"    # Optional
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
results = search.search("serverless computing options", top_k=2)

# Print results
for result in results:
    print(f"Score: {result['score']:.4f} | {result['document']}")
```

## Requirements

- Python 3.12+
- AWS account with access to Amazon Bedrock
- Proper AWS credentials configured

## License

This library is licensed under the MIT License.
