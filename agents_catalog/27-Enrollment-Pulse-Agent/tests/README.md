# Enrollment Pulse Test Suite

## Local Backend Tests

### Data Processing
```bash
python tests/test_data_processing.py
```

## AWS Deployment Tests

### Prerequisites
Set AWS credentials using **one** of these methods:

**Option 1: Environment Variables**
```bash
export AWS_ACCESS_KEY_ID=your_key
export AWS_SECRET_ACCESS_KEY=your_secret
export AWS_DEFAULT_REGION=us-west-2
```

**Option 2: AWS CLI**
```bash
aws configure
```

**Option 3: AWS Credentials File**
```bash
# ~/.aws/credentials
[default]
aws_access_key_id = your_key
aws_secret_access_key = your_secret
region = us-west-2
```

### Run AWS Tests

**Query Endpoint Test (Recommended)**
```bash
python tests/test_query_endpoint.py
```

## Test Files

- `test_helper.py` - Common test utilities
- `test_data_processing.py` - Backend data processing
- `test_query_endpoint.py` - **Query endpoint with IAM auth**

## Expected Results

**Local Tests:**
- Data processing: ✅ 5 sites, 112 subjects

**AWS Tests:**
- Query endpoint: ✅ Detailed enrollment analysis with site-specific recommendations
- IAM authentication: ✅ Properly secured

## Security

- AWS tests use IAM authentication
- No credentials hardcoded in test files
- Uses standard AWS credential chain