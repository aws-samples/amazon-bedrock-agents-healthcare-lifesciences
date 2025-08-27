"""
Lambda handler with full FastAPI + Strands Agent functionality
"""
import sys
import os
import json

# Add parent directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

def lambda_handler(event, context):
    """AWS Lambda handler with full FastAPI functionality"""
    try:
        from mangum import Mangum
        from backend_api import app
        
        # Create the Lambda handler using Mangum
        handler = Mangum(app, lifespan="off")
        return handler(event, context)
        
    except ImportError as import_error:
        # Fallback when dependencies not available
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({"error": f"Missing dependencies: {str(import_error)}"})
        }
    except Exception as general_error:
        # General error handling
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({"error": f"Lambda error: {str(general_error)}"})
        }