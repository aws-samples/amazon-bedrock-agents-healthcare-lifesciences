#!/usr/bin/env python3
"""
Test script for the In Vivo Study Scheduler lambda function.
"""

import sys
import os
import json

# Add the container directory to the path so we can import the modules
sys.path.append(os.path.join(os.path.dirname(__file__), "container"))

# Import the lambda function
from lambda_function import optimize_study_schedule

# Sample test data
TEST_STUDIES = [
    {
        "study_id": "Study_A",
        "animals_required": 150,
        "preferred_start_day": 5,
        "duration_days": 3,
        "priority": 4
    },
    {
        "study_id": "Study_B",
        "animals_required": 200,
        "preferred_start_day": 10,
        "duration_days": 2,
        "priority": 3
    },
    {
        "study_id": "Study_C",
        "animals_required": 100,
        "preferred_start_day": 8,
        "duration_days": 1,
        "priority": 5
    },
    {
        "study_id": "Study_D",
        "animals_required": 300,
        "preferred_start_day": 15,
        "duration_days": 4,
        "priority": 2
    },
    {
        "study_id": "Study_E",
        "animals_required": 175,
        "preferred_start_day": 20,
        "duration_days": 2,
        "priority": 3
    }
]

def main():
    """Test the lambda function."""
    print("=== Testing In Vivo Study Scheduler Lambda Function ===")
    
    try:
        # Convert studies to JSON string
        studies_json = json.dumps(TEST_STUDIES)
        
        # Set environment variable for testing
        os.environ["VISUALIZATION_BUCKET"] = "test-bucket"
        
        # Run the lambda function
        result = optimize_study_schedule(
            studies=studies_json,
            max_animals_per_day=1000,
            optimization_objective="balance_animals",
            visualization_type="bar_chart"
        )
        
        print("Lambda function executed successfully!")
        print("\nResponse:")
        print(result["TEXT"]["body"])
        
        return 0
    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
