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

### Caching Embeddings

You can save the generated embeddings to a local file to avoid recomputing them:

```python
# Index documents and save embeddings to a file
search.index(documents, cache_path="embeddings.npy")
```

This saves the embeddings as a NumPy binary file, which can be useful for:
- Preserving embeddings between application restarts
- Sharing embeddings between different applications
- Reducing API calls to Amazon Bedrock

### Loading Pre-computed Embeddings

You can also load pre-computed embeddings from a file instead of generating them:

```python
# Load embeddings from a file instead of computing them
search.index(documents, embeddings_file="embeddings.npy")
```

You can combine both options to load from one file and save to another:

```python
# Load embeddings from one file and save to another
search.index(documents, embeddings_file="source_embeddings.npy", cache_path="destination_embeddings.npy")
```

The library validates that the number of embeddings in the file matches the number of documents being indexed. If there's a mismatch, a `ValueError` will be raised.

## Requirements

- Python 3.12+
- AWS account with access to Amazon Bedrock
- Proper AWS credentials configured

## License

This library is licensed under the MIT License.
