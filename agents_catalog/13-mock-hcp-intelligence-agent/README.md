# HCP Intelligence DynamoDB Table

This directory contains resources for creating and interacting with a DynamoDB table designed to store healthcare provider (HCP) intelligence data.

## CloudFormation Template

The `dynamodb.yaml` CloudFormation template creates:

- A DynamoDB table with PAY_PER_REQUEST (on-demand) billing mode
- Primary key: HcpId (string)
- Global Secondary Index on FullName for efficient name-based queries
- Time-to-Live configuration using the ExpirationTime attribute
- IAM role with appropriate permissions for accessing the table

## Deployment

To deploy the CloudFormation stack:

```bash
aws cloudformation deploy \
  --template-file dynamodb.yaml \
  --stack-name hcp-intelligence-dynamodb \
  --region us-west-2 \
  --capabilities CAPABILITY_IAM
```

## Python Scripts

### 1. Populate DynamoDB Table (`populate_dynamodb.py`)

This script demonstrates how to:
- Add sample healthcare provider records to the table
- Query records by full name using the Global Secondary Index
- Retrieve a record directly by its HcpId (primary key)

```bash
python populate_dynamodb.py
```

### 2. Query Examples (`query_examples.py`)

This script provides additional examples of:
- Querying HCPs by specialty using scan with filter
- Finding HCPs with minimum years of experience
- Updating HCP information
- Using batch operations for efficient writes

```bash
python query_examples.py
```

## Data Structure

Each HCP record contains:

- **HcpId**: Unique identifier (primary key)
- **FullName**: Provider's full name (indexed for efficient queries)
- **Specialty**: Medical specialty
- **Hospital**: Affiliated institution
- **YearsExperience**: Years of professional experience
- **Certifications**: List of professional certifications
- **ContactInfo**: Nested attribute with contact details
- **ExpirationTime**: TTL attribute for automatic record expiration

## Best Practices

- Use the Global Secondary Index (GSI) on FullName for name-based queries
- For queries on non-indexed attributes, use scan with filters
- Consider adding additional GSIs if you frequently query by other attributes
- Use batch operations when adding or updating multiple items
- Set appropriate TTL values to automatically remove outdated records