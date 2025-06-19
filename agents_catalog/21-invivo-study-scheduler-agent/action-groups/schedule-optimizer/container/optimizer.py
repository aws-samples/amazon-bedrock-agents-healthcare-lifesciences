"""
Optimizer module for in vivo study scheduling.
Uses a greedy approach to distribute studies across the month.
"""

import logging
from typing import Dict, Any, List, Optional
import numpy as np

# Configure logging
logger = logging.getLogger(__name__)


def optimize_schedule(
    studies: List[Dict[str, Any]],
    max_animals_per_day: int = 1000,
    optimization_objective: str = "balance_animals",
    days_in_period: int = 30
) -> Dict[str, Any]:
    """
    Optimize the schedule of in vivo studies using a greedy approach.
    
    Args:
        studies: List of studies to schedule
        max_animals_per_day: Maximum number of animals available per day
        optimization_objective: Primary objective ('balance_animals' or 'balance_studies')
        days_in_period: Number of days in the scheduling period
        
    Returns:
        Dictionary containing the optimized schedule and metrics
    """
    # Sort studies by priority (higher priority first), then by animals required (larger first)
    sorted_studies = sorted(studies, 
                           key=lambda s: (-s.get("priority", 3), -s.get("animals_required", 0)))
    
    # Initialize daily usage arrays
    daily_animals = [0] * days_in_period
    daily_studies = [0] * days_in_period
    daily_active_studies = [[] for _ in range(days_in_period)]
    
    # Schedule each study
    schedule = []
    for i, study in enumerate(sorted_studies):
        study_id = study.get("study_id", f"Study_{i+1}")
        animals_required = study.get("animals_required", 0)
        duration = study.get("duration_days", 1)
        preferred_day = study.get("preferred_start_day")
        
        # Find the best day to schedule this study
        best_day = find_best_day(
            daily_animals=daily_animals,
            daily_studies=daily_studies,
            animals_required=animals_required,
            duration=duration,
            max_animals_per_day=max_animals_per_day,
            preferred_day=preferred_day,
            optimization_objective=optimization_objective
        )
        
        # Update the schedule and daily usage
        schedule.append({
            "study_id": study_id,
            "animals_required": animals_required,
            "assigned_start_day": best_day + 1,  # Convert to 1-indexed
            "duration_days": duration,
            "preferred_start_day": preferred_day,
            "priority": study.get("priority", 3)
        })
        
        # Update daily usage for each day of the study
        for d in range(duration):
            if best_day + d < days_in_period:
                daily_animals[best_day + d] += animals_required
                daily_studies[best_day + d] += 1
                daily_active_studies[best_day + d].append(study_id)
    
    # Create daily usage data structure
    daily_usage = []
    for d in range(days_in_period):
        daily_usage.append({
            "day": d + 1,  # Convert to 1-indexed
            "animal_count": daily_animals[d],
            "study_count": daily_studies[d],
            "active_studies": daily_active_studies[d]
        })
    
    # Calculate metrics
    total_animals = sum(study.get("animals_required", 0) for study in studies)
    max_animals = max(daily_animals) if daily_animals else 0
    avg_animals = sum(daily_animals) / days_in_period
    std_dev_animals = float(np.std(daily_animals))
    
    max_studies = max(daily_studies) if daily_studies else 0
    avg_studies = sum(daily_studies) / days_in_period
    std_dev_studies = float(np.std(daily_studies))
    
    # Calculate median for non-zero values
    non_zero_animal_counts = [count for count in daily_animals if count > 0]
    non_zero_study_counts = [count for count in daily_studies if count > 0]
    
    median_animals = float(np.median(non_zero_animal_counts)) if non_zero_animal_counts else 0
    median_studies = float(np.median(non_zero_study_counts)) if non_zero_study_counts else 0
    
    result = {
        "schedule": schedule,
        "daily_usage": daily_usage,
        "total_animals": total_animals,
        "max_animals_per_day": max_animals,
        "avg_animals_per_day": avg_animals,
        "median_animals_per_active_day": median_animals,
        "std_dev_animals": std_dev_animals,
        "max_studies_per_day": max_studies,
        "avg_studies_per_day": avg_studies,
        "median_studies_per_active_day": median_studies,
        "std_dev_studies": std_dev_studies
    }
    
    return result

def find_best_day(
    daily_animals: List[int],
    daily_studies: List[int],
    animals_required: int,
    duration: int,
    max_animals_per_day: int,
    preferred_day: Optional[int] = None,
    optimization_objective: str = "balance_animals"
) -> int:
    """
    Find the best day to schedule a study.
    
    Args:
        daily_animals: Current animal usage per day
        daily_studies: Current study count per day
        animals_required: Number of animals required for the study
        duration: Duration of the study in days
        max_animals_per_day: Maximum number of animals available per day
        preferred_day: Preferred start day (1-indexed)
        optimization_objective: Primary objective ('balance_animals' or 'balance_studies')
        
    Returns:
        Best day to start the study (0-indexed)
    """
    days_in_period = len(daily_animals)
    
    # Convert preferred day to 0-indexed
    preferred_day_0indexed = preferred_day - 1 if preferred_day is not None else None
    
    # Check if preferred day is valid
    if (preferred_day_0indexed is not None and 
        0 <= preferred_day_0indexed <= days_in_period - duration):
        # Check if scheduling on the preferred day would exceed capacity
        can_schedule_on_preferred = True
        for d in range(duration):
            if (preferred_day_0indexed + d < days_in_period and 
                daily_animals[preferred_day_0indexed + d] + animals_required > max_animals_per_day):
                can_schedule_on_preferred = False
                break
        
        if can_schedule_on_preferred:
            return preferred_day_0indexed
    
    # If we can't schedule on the preferred day, find the best alternative
    best_day = 0
    best_score = float('inf')
    
    for start_day in range(days_in_period - duration + 1):
        # Check if scheduling on this day would exceed capacity
        can_schedule = True
        for d in range(duration):
            if (start_day + d < days_in_period and 
                daily_animals[start_day + d] + animals_required > max_animals_per_day):
                can_schedule = False
                break
        
        if not can_schedule:
            continue
        
        # Calculate score based on optimization objective
        if optimization_objective == "balance_animals":
            # Calculate what the new daily animal counts would be
            new_daily_animals = daily_animals.copy()
            for d in range(duration):
                if start_day + d < days_in_period:
                    new_daily_animals[start_day + d] += animals_required
            
            # Score is the standard deviation of the new daily animal counts
            score = float(np.std(new_daily_animals))
        else:  # balance_studies
            # Calculate what the new daily study counts would be
            new_daily_studies = daily_studies.copy()
            for d in range(duration):
                if start_day + d < days_in_period:
                    new_daily_studies[start_day + d] += 1
            
            # Score is the standard deviation of the new daily study counts
            score = float(np.std(new_daily_studies))
        
        # If preferred day was specified, add penalty for distance from preferred day
        if preferred_day_0indexed is not None:
            distance_penalty = abs(start_day - preferred_day_0indexed) * 0.1
            score += distance_penalty
        
        # Update best day if this day has a better score
        if score < best_score:
            best_score = score
            best_day = start_day
    
    return best_day
