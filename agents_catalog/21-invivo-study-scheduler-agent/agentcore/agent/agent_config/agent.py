import json
import logging
from typing import Dict, Any, List, Optional

import numpy as np
from strands import Agent, tool
from strands.models import BedrockModel

logger = logging.getLogger(__name__)

MODEL_ID = "us.anthropic.claude-sonnet-4-5-20250929-v1:0"

SYSTEM_PROMPT = """You are an expert laboratory resource scheduler specializing in optimizing in vivo study schedules. Your goal is to help laboratory managers efficiently allocate resources by creating balanced schedules that distribute studies evenly across a 30-day period.

You have access to the following tools:

- optimize_schedule: Creates an optimized schedule for in vivo studies over a 30-day period, balancing resource utilization and respecting capacity constraints.

Scheduling Process:

1. Begin by asking which studies need to be scheduled, if not provided.
2. For each study, collect the following information:
   - Study ID or name
   - Number of animals required
   - Preferred start date (optional)
   - Duration of the study in days (default is 1)
   - Priority level (optional)
3. Use the optimize_schedule function to generate an optimized schedule.
4. Present the schedule in a clear, structured format.
5. Provide insights on resource utilization and any potential bottlenecks.

Response Guidelines:

- Explain the optimization approach and constraints considered
- Highlight how the schedule balances resource utilization
- Compare the optimized schedule to any preferred dates that were specified
- Suggest improvements or alternatives if applicable
- Acknowledge any limitations in the optimization process
"""


def _find_best_day(
    daily_animals: List[int],
    daily_studies: List[int],
    animals_required: int,
    duration: int,
    max_animals_per_day: int,
    preferred_day: Optional[int],
    optimization_objective: str,
) -> int:
    """Find the best day to schedule a study using greedy optimization."""
    days_in_period = len(daily_animals)
    preferred_day_0indexed = preferred_day - 1 if preferred_day is not None else None

    # Try preferred day first
    if preferred_day_0indexed is not None and 0 <= preferred_day_0indexed <= days_in_period - duration:
        can_schedule = all(
            daily_animals[preferred_day_0indexed + d] + animals_required <= max_animals_per_day
            for d in range(duration)
            if preferred_day_0indexed + d < days_in_period
        )
        if can_schedule:
            return preferred_day_0indexed

    best_day = 0
    best_score = float("inf")

    for start_day in range(days_in_period - duration + 1):
        can_schedule = all(
            daily_animals[start_day + d] + animals_required <= max_animals_per_day
            for d in range(duration)
            if start_day + d < days_in_period
        )
        if not can_schedule:
            continue

        if optimization_objective == "balance_animals":
            new_daily = daily_animals.copy()
            for d in range(duration):
                if start_day + d < days_in_period:
                    new_daily[start_day + d] += animals_required
            score = float(np.std(new_daily))
        else:
            new_daily = daily_studies.copy()
            for d in range(duration):
                if start_day + d < days_in_period:
                    new_daily[start_day + d] += 1
            score = float(np.std(new_daily))

        if preferred_day_0indexed is not None:
            score += abs(start_day - preferred_day_0indexed) * 0.1

        if score < best_score:
            best_score = score
            best_day = start_day

    return best_day


@tool
def optimize_schedule(
    studies: str,
    max_animals_per_day: int = 1000,
    optimization_objective: str = "balance_animals",
) -> str:
    """Optimize the schedule of in vivo studies over a 30-day period to balance resource utilization.

    Args:
        studies: JSON string representing a list of studies to schedule, each with study_id, animals_required, preferred_start_day (optional), duration_days (optional), and priority (optional).
        max_animals_per_day: Maximum number of animals available per day, default is 1000.
        optimization_objective: Primary optimization objective: 'balance_animals' (default) or 'balance_studies'.
    """
    days_in_period = 30

    try:
        studies_list = json.loads(studies)
    except json.JSONDecodeError as e:
        return json.dumps({"status": "error", "message": f"Invalid JSON for studies: {e}"})

    sorted_studies = sorted(
        studies_list, key=lambda s: (-s.get("priority", 3), -s.get("animals_required", 0))
    )

    daily_animals = [0] * days_in_period
    daily_studies = [0] * days_in_period
    daily_active_studies: List[List[str]] = [[] for _ in range(days_in_period)]
    schedule = []

    for i, study in enumerate(sorted_studies):
        study_id = study.get("study_id", f"Study_{i+1}")
        animals_required = study.get("animals_required", 0)
        duration = study.get("duration_days", 1)
        preferred_day = study.get("preferred_start_day")

        best_day = _find_best_day(
            daily_animals, daily_studies, animals_required, duration,
            max_animals_per_day, preferred_day, optimization_objective,
        )

        schedule.append({
            "study_id": study_id,
            "animals_required": animals_required,
            "assigned_start_day": best_day + 1,
            "duration_days": duration,
            "preferred_start_day": preferred_day,
            "priority": study.get("priority", 3),
        })

        for d in range(duration):
            if best_day + d < days_in_period:
                daily_animals[best_day + d] += animals_required
                daily_studies[best_day + d] += 1
                daily_active_studies[best_day + d].append(study_id)

    daily_usage = [
        {"day": d + 1, "animal_count": daily_animals[d], "study_count": daily_studies[d], "active_studies": daily_active_studies[d]}
        for d in range(days_in_period)
    ]

    result = {
        "status": "success",
        "schedule": schedule,
        "daily_usage": daily_usage,
        "total_animals": sum(s.get("animals_required", 0) for s in studies_list),
        "max_animals_per_day": max(daily_animals),
        "avg_animals_per_day": round(sum(daily_animals) / days_in_period, 2),
        "std_dev_animals": round(float(np.std(daily_animals)), 2),
        "max_studies_per_day": max(daily_studies),
        "avg_studies_per_day": round(sum(daily_studies) / days_in_period, 2),
        "std_dev_studies": round(float(np.std(daily_studies)), 2),
        "summary": f"Successfully optimized schedule for {len(studies_list)} studies with {optimization_objective} objective.",
    }

    return json.dumps(result)


def create_agent() -> Agent:
    """Create and return the In Vivo Study Scheduler agent."""
    model = BedrockModel(model_id=MODEL_ID, streaming=True)
    return Agent(
        model=model,
        system_prompt=SYSTEM_PROMPT,
        tools=[optimize_schedule],
    )
