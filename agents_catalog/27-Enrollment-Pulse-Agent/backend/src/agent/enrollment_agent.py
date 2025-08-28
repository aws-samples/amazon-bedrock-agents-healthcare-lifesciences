"""
Enrollment Pulse - Clinical Trial Enrollment Optimization Agent
"""
import sys
from pathlib import Path

# Add root directory to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))

from strands import Agent
from strands_tools import calculator, current_time
from src.agent.tools import (
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
    get_intervention_recommendations
)

# Import new epidemiology and clinical trials tools
from src.agent.epidemiology_tools import (
    get_epidemiology_overview,
    analyze_market_epidemiology,
    compare_market_epidemiology,
    get_biomarker_landscape,
    identify_high_potential_markets,
    get_patient_density_analysis,
    estimate_trial_recruitment_pool
)

from src.agent.clinical_trials_tools import (
    get_clinical_trials_landscape,
    search_clinical_trials,
    get_trial_details,
    analyze_competitive_landscape,
    analyze_trial_enrollment_patterns,
    identify_recruiting_trials,
    analyze_trial_geography,
    analyze_intervention_trends,
    benchmark_trial_characteristics
)

# Import live clinical trials tools
from src.agent.live_clinical_trials_tools import (
    search_live_clinical_trials,
    get_live_trial_details,
    analyze_live_competitive_landscape,
    find_recruiting_trials_by_location,
    track_enrollment_trends
)


# System prompt for the clinical operations advisor
SYSTEM_PROMPT = """
You are an expert clinical operations advisor specializing in clinical trial enrollment optimization. You have deep expertise in analyzing Veeva CTMS data, epidemiological patient populations, and competitive clinical trials landscape to provide actionable insights to study managers.

## Your Role
- **ALWAYS analyze and respond at the individual site level** - never give generic study-wide answers
- Provide detailed, site-specific performance analysis for each location
- Identify patterns distinguishing high-performing from underperforming sites  
- Provide strategic recommendations tailored to each individual site
- Support study managers with granular, actionable, site-specific decision making

## CRITICAL INSTRUCTION
**Every response must be organized by individual sites. Never provide generic or study-wide answers without breaking them down by specific sites. Always use the comprehensive site analysis tool first to get detailed per-site data.**

## Clinical Trial Context
You are analyzing the Phase II ONCO-2025-117 trial studying MK-8791 in combination with Pembrolizumab for metastatic triple-negative breast cancer. The trial has:
- Target enrollment: 120 subjects across 5 US cancer centers
- Enrollment deadline: September 30, 2025
- Current status: Behind schedule with some sites significantly underperforming

## Key Sites
1. Memorial Sloan Cancer Center (NY) - Site 1
2. Dana-Farber Cancer Institute (Boston) - Site 2  
3. MD Anderson Cancer Center (Houston) - Site 3
4. UCLA Jonsson Comprehensive Cancer Center (LA) - Site 4
5. Mayo Clinic Cancer Center - Site 5

## Analysis Approach
- Calculate key metrics (enrollment %, screen failure rates, monthly rates)
- Compare high-performing vs low-performing sites
- Analyze CRA performance correlations
- Project timeline completion based on current trends
- Analyze historical performance trends and patterns
- Recommend alternative sites for underperforming locations
- Recommend specific, actionable interventions
- Analyze epidemiological patient populations and market potential
- Assess competitive clinical trials landscape
- Evaluate biomarker prevalence and trial eligibility rates
- Compare recruitment feasibility across metropolitan areas

## Response Style
- **ALWAYS respond at the granular site level by default** - every answer should be organized by individual sites
- Be concise but comprehensive for each site
- Provide specific, actionable recommendations tailored to each site
- Use a confident, consultative tone
- Present numerical analysis clearly with proper context
- For each site, include: current performance, historical trends, and specific recommendations
- Always frame advice in terms of impact on study timeline and budget
- Support recommendations with data-driven rationale

## MANDATORY Response Format - Site-Level Analysis
**For EVERY question, structure responses as:**

### Site-by-Site Analysis Format:
```
## [Site Name] - [Current Status]
**Performance**: [Enrollment %] ([current]/[target] subjects)
**Trend**: [Recent performance trend]
**Risk Level**: [Low/Medium/High]

**Historical Context**: [Key historical insights]
**Specific Recommendations**: 
- [Site-specific action 1]
- [Site-specific action 2]
**Alternative Options**: [If applicable]

---
```

## Response Rules
1. **NEVER give generic or study-wide answers** - always break down by individual sites
2. **ALWAYS use the comprehensive site analysis tool** to get detailed per-site data
3. **ALWAYS structure responses with clear site sections** using the format above
4. **ALWAYS provide site-specific recommendations** rather than general advice
5. **ALWAYS include historical context** for each site when available
6. **ALWAYS mention specific numbers** (enrollment counts, percentages, trends) for each site

When asked about enrollment status, performance, or optimization, IMMEDIATELY use the comprehensive site analysis tool to get detailed per-site data, then structure your response with individual sections for each relevant site, providing specific insights and recommendations for each location.
"""


def create_enrollment_agent() -> Agent:
    """Create and configure the Enrollment Pulse agent"""
    
    # Custom tools for clinical trial analysis - prioritized for site-level responses
    clinical_tools = [
        get_comprehensive_site_analysis,        # PRIMARY TOOL - always use for detailed site analysis
        get_underperforming_sites_detailed,     # Site-specific underperforming analysis
        get_historical_performance,             # Historical trends by site
        get_alternative_site_recommendations,   # Site-specific alternatives
        get_overall_enrollment_status,          # Overall context (use sparingly)
        get_site_performance_ranking,           # Site rankings
        identify_underperforming_sites,         # Basic underperforming list
        analyze_cra_performance,                # CRA correlation analysis
        get_monthly_enrollment_trends,          # Regional trends
        calculate_screening_efficiency,         # Site screening metrics
        project_enrollment_timeline,            # Site projections
        get_intervention_recommendations        # Generic recommendations (use sparingly)
    ]
    
    # Epidemiology and market analysis tools
    epidemiology_tools = [
        get_epidemiology_overview,             # Overall epidemiology landscape
        analyze_market_epidemiology,           # Specific market analysis
        compare_market_epidemiology,           # Market comparison
        get_biomarker_landscape,               # Biomarker distribution analysis
        identify_high_potential_markets,       # High-potential market identification
        get_patient_density_analysis,          # Patient density patterns
        estimate_trial_recruitment_pool        # Recruitment pool estimation
    ]
    
    # Clinical trials competitive intelligence tools
    clinical_trials_tools = [
        get_clinical_trials_landscape,         # Overall trials landscape
        search_clinical_trials,                # Search specific trials
        get_trial_details,                     # Detailed trial information
        analyze_competitive_landscape,         # Competitive analysis
        analyze_trial_enrollment_patterns,     # Enrollment pattern analysis
        identify_recruiting_trials,            # Currently recruiting trials
        analyze_trial_geography,               # Geographic trial distribution
        analyze_intervention_trends,           # Treatment trend analysis
        benchmark_trial_characteristics        # Trial benchmarking
    ]
    
    # Live clinical trials API tools
    live_clinical_trials_tools = [
        search_live_clinical_trials,           # Live API search
        get_live_trial_details,                # Live trial details
        analyze_live_competitive_landscape,    # Live competitive analysis
        find_recruiting_trials_by_location,    # Geographic recruitment analysis
        track_enrollment_trends                # Enrollment trend tracking
    ]
    
    # Utility tools
    utility_tools = [
        calculator,
        current_time
    ]
    
    # Combine all tools
    all_tools = clinical_tools + epidemiology_tools + clinical_trials_tools + live_clinical_trials_tools + utility_tools
    
    # Create the agent
    agent = Agent(
        model="us.anthropic.claude-3-7-sonnet-20250219-v1:0",
        tools=all_tools,
        system_prompt=SYSTEM_PROMPT
    )
    
    return agent


# Create the global agent instance
enrollment_agent = create_enrollment_agent()


class EnrollmentAgent:
    """Enrollment Pulse Agent wrapper class"""
    
    def __init__(self):
        self.agent = enrollment_agent
    
    def query(self, message: str) -> str:
        """Query the agent with a message"""
        return query_agent(message)


def query_agent(message: str) -> str:
    """
    Query the enrollment agent with a message
    
    Args:
        message: User query about enrollment status or optimization
        
    Returns:
        Agent response with analysis and recommendations
    """
    try:
        response = enrollment_agent(message)
        
        # Extract text content from the Strands Agent response
        if hasattr(response, 'message') and isinstance(response.message, dict):
            # Handle Strands Agent response structure: {'role': 'assistant', 'content': [{'text': '...'}]}
            if 'content' in response.message and isinstance(response.message['content'], list):
                text_parts = []
                for item in response.message['content']:
                    if isinstance(item, dict) and 'text' in item:
                        text_parts.append(item['text'])
                return '\n'.join(text_parts) if text_parts else "No response content"
            else:
                return str(response.message)
        else:
            return str(response)
            
    except Exception as e:
        return f"Error processing query: {str(e)}"


if __name__ == "__main__":
    # Test the agent with sample queries
    test_queries = [
        "What is the current enrollment status by site?",
        "Which sites are underperforming and need intervention?",
        "How does CRA assignment correlate with site performance?",
        "What are your recommendations for improving enrollment at Mayo Clinic?"
    ]
    
    print("🔬 Testing Enrollment Pulse Agent...")
    print("=" * 60)
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n📋 Query {i}: {query}")
        print("-" * 40)
        response = query_agent(query)
        print(response)
        print("\n" + "=" * 60)