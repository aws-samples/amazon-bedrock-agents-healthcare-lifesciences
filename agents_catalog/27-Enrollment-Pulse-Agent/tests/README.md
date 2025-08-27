# Enrollment Pulse Test Suite

## Setup

### 1. Deploy Backend First
```bash
cd backend
./build.sh
./deploy_only.sh
```
This creates `backend/deployment_info.txt` with API URLs.

### 2. Install Test Dependencies
```bash
# From project root
python3 -m venv venv
source venv/bin/activate
pip install -r tests/requirements.txt
```

## Test Files

- `test_data_processing.py` - Local data processing tests
- `test_api_gateway.py` - **API Gateway endpoints (public)**
- `test_query_endpoint.py` - Lambda Function URL (IAM auth)
- `load_deployment_info.py` - Utility to load URLs from deployment

## Running Tests

### Local Data Processing
```bash
python tests/test_data_processing.py
```

### API Gateway Tests (Recommended)
```bash
python tests/test_api_gateway.py
```
Tests public endpoints:
- `/status/overall`
- `/sites/performance` 
- `/sites/underperforming`
- `/query` (AI agent)

### Lambda Function URL Tests (IAM Auth)
```bash
# Requires AWS credentials
export AWS_ACCESS_KEY_ID=your_key
export AWS_SECRET_ACCESS_KEY=your_secret
export AWS_DEFAULT_REGION=us-west-2
python tests/test_query_endpoint.py
```

## Expected Results

**API Gateway Tests:**
- ✅ Overall status: 75.8% enrollment (91/120)
- ✅ Site performance: 5 sites ranked
- ✅ Underperforming: 2 sites identified
- ✅ AI query: Detailed analysis response

**Local Tests:**
- ✅ Data processing: 5 sites, 112 subjects loaded

## Dynamic URL Loading

Tests automatically load URLs from `backend/deployment_info.txt`:
- No hardcoded URLs in test files
- Works with any AWS region/account
- Updates automatically when backend is redeployed