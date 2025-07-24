#!/usr/bin/env python3
"""
Test script for the In Vivo Study Scheduler optimizer.
"""

import sys
import os
import json

# Add the container directory to the path so we can import the modules
sys.path.append(os.path.join(os.path.dirname(__file__), "container"))

# Import the optimizer module directly
from optimizer import optimize_schedule

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
    """Test the optimizer."""
    print("=== Testing In Vivo Study Scheduler Optimizer ===")
    
    try:
        # Run the optimizer
        result = optimize_schedule(
            studies=TEST_STUDIES,
            max_animals_per_day=1000,
            optimization_objective="balance_animals",
            days_in_period=30
        )
        
        print(f"Optimization successful!")
        print(f"Total animals: {result['total_animals']}")
        print(f"Max animals per day: {result['max_animals_per_day']}")
        print(f"Avg animals per day: {result['avg_animals_per_day']:.2f}")
        print(f"Median animals per active day: {result.get('median_animals_per_active_day', 0):.2f}")
        print(f"Std dev animals: {result['std_dev_animals']:.2f}")
        
        print("\nSchedule:")
        for study in result["schedule"]:
            print(f"  {study['study_id']}: Start day {study['assigned_start_day']}, "
                  f"Duration {study['duration_days']} days, "
                  f"Animals {study['animals_required']}")
        
        print("\nDaily usage:")
        active_days = [day for day in result["daily_usage"] if day["animal_count"] > 0]
        for day in active_days:
            print(f"  Day {day['day']}: {day['animal_count']} animals, "
                  f"{day['study_count']} studies, "
                  f"Active: {', '.join(day['active_studies'])}")
        
        # Save the result to a JSON file for reference
        with open("optimizer_result.json", "w") as f:
            json.dump(result, f, indent=2)
        print("\nResult saved to optimizer_result.json")
        
        return 0
    except Exception as e:
        print(f"Error: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
