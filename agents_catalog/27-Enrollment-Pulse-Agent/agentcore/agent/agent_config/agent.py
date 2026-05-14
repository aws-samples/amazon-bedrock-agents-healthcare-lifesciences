"""Enrollment Pulse agent task logic."""

from strands import Agent
from strands.models import BedrockModel
from strands_tools import calculator, current_time

from agent.agent_config.tools import (
    get_overall_enrollment_status,
    get_site_performance_ranking,
    identify_underperforming_sites,
    get_underperforming_sites_detailed,
    get_comprehensive_site_analysis,
    analyze_cra_performance,
    get_monthly_enrollment_trends,
    calculate_screening_efficiency,
    project_enrollment_timeline,
    get_historical_performance,
    get_alternative_site_recommendations,
    get_intervention_recommendations,
)
from agent.agent_config.epidemiology_tools import (
    get_epidemiology_overview,
    analyze_market_epidemiology,
    compare_market_epidemiology,
    get_biomarker_landscape,
    identify_high_potential_markets,
    get_patient_density_analysis,
    estimate_trial_recruitment_pool,
)
from agent.agent_config.clinical_trials_tools import (
    get_clinical_trials_landscape,
    search_clinical_trials,
    get_trial_details,
    analyze_competitive_landscape,
    analyze_trial_enrollment_patterns,
    identify_recruiting_trials,
    analyze_trial_geography,
    analyze_intervention_trends,
    benchmark_trial_characteristics,
)
from agent.agent_config.live_clinical_trials_tools import (
    search_live_clinical_trials,
    get_live_trial_details,
    analyze_live_competitive_landscape,
    find_recruiting_trials_by_location,
    track_enrollment_trends,
)

MODEL_ID = "us.anthropic.claude-sonnet-4-5-20250929-v1:0"

SYSTEM_PROMPT = """
You are an expert clinical operations advisor specializing in clinical trial enrollment optimization.
You analyze Veeva CTMS data, epidemiological patient populations, and competitive clinical trials
landscape to provide actionable, site-level insights to study managers.

ALWAYS analyze at the individual site level. Use the comprehensive site analysis tool first.
Include specific numbers, historical context, and actionable recommendations for each site.
"""

ALL_TOOLS = [
    get_comprehensive_site_analysis,
    get_underperforming_sites_detailed,
    get_historical_performance,
    get_alternative_site_recommendations,
    get_overall_enrollment_status,
    get_site_performance_ranking,
    identify_underperforming_sites,
    analyze_cra_performance,
    get_monthly_enrollment_trends,
    calculate_screening_efficiency,
    project_enrollment_timeline,
    get_intervention_recommendations,
    get_epidemiology_overview,
    analyze_market_epidemiology,
    compare_market_epidemiology,
    get_biomarker_landscape,
    identify_high_potential_markets,
    get_patient_density_analysis,
    estimate_trial_recruitment_pool,
    get_clinical_trials_landscape,
    search_clinical_trials,
    get_trial_details,
    analyze_competitive_landscape,
    analyze_trial_enrollment_patterns,
    identify_recruiting_trials,
    analyze_trial_geography,
    analyze_intervention_trends,
    benchmark_trial_characteristics,
    search_live_clinical_trials,
    get_live_trial_details,
    analyze_live_competitive_landscape,
    find_recruiting_trials_by_location,
    track_enrollment_trends,
    calculator,
    current_time,
]


async def agent_task(user_message: str, session_id: str):
    """Create and run the enrollment pulse agent."""
    agent = Agent(
        model=BedrockModel(model_id=MODEL_ID),
        system_prompt=SYSTEM_PROMPT,
        tools=ALL_TOOLS,
    )

    import json as _json
    async for event in agent.stream_async(user_message):
        yield _json.loads(_json.dumps(dict(event), default=str))
