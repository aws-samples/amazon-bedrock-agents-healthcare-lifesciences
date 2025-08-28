"""
Clinical Trials Analysis Tools for Strands Agent
"""
from strands import tool
from typing import Dict, List, Optional
import sys
from pathlib import Path

# Add src to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from data.clinical_trials_processor import ClinicalTrialsProcessor

# Global processor instance
_clinical_trials_processor = None

def get_clinical_trials_processor():
    """Get or create clinical trials processor instance"""
    global _clinical_trials_processor
    if _clinical_trials_processor is None:
        _clinical_trials_processor = ClinicalTrialsProcessor()
        _clinical_trials_processor.process_data()
    return _clinical_trials_processor

@tool
def get_clinical_trials_landscape() -> Dict:
    """
    Get comprehensive overview of the clinical trials landscape for TNBC/MTNBC.
    
    Returns detailed analysis including:
    - Summary statistics (total trials, enrollment, duration)
    - Trial status distribution (recruiting, completed, etc.)
    - Phase distribution analysis
    - Geographic spread and international presence
    - Competitive landscape by sponsors
    
    Use this tool to understand the overall clinical trials environment
    and competitive dynamics in the TNBC space.
    """
    processor = get_clinical_trials_processor()
    return processor.processed_data

@tool
def search_clinical_trials(
    condition: Optional[str] = None,
    intervention: Optional[str] = None, 
    status: Optional[str] = None,
    phase: Optional[str] = None,
    sponsor: Optional[str] = None
) -> Dict:
    """
    Search clinical trials based on specific criteria.
    
    Args:
        condition: Condition/disease to search for (e.g., "Triple Negative Breast Cancer")
        intervention: Intervention type to search for (e.g., "Pembrolizumab", "Immunotherapy")
        status: Trial status (e.g., "RECRUITING", "COMPLETED")
        phase: Trial phase (e.g., "PHASE2", "PHASE1")
        sponsor: Sponsor name or type (e.g., "Pfizer", "University")
    
    Returns:
        Search results including:
        - Number of matching trials
        - Detailed trial information
        - Key characteristics of matching studies
    
    Use this tool to find specific trials or analyze subsets of the clinical trials database
    based on your criteria of interest.
    """
    processor = get_clinical_trials_processor()
    return processor.search_trials(condition, intervention, status, phase, sponsor)

@tool
def get_trial_details(nct_number: str) -> Dict:
    """
    Get detailed information for a specific clinical trial.
    
    Args:
        nct_number: NCT number of the trial (e.g., "NCT05035745")
    
    Returns:
        Comprehensive trial details including:
        - Study title and summary
        - Current status and timeline
        - Enrollment targets and locations
        - Interventions and conditions
        - Sponsor and collaborator information
    
    Use this tool to get in-depth information about specific trials
    for competitive analysis or collaboration opportunities.
    """
    processor = get_clinical_trials_processor()
    return processor.get_trial_details(nct_number)

@tool
def analyze_competitive_landscape() -> Dict:
    """
    Analyze the competitive landscape in TNBC clinical trials.
    
    Returns:
        Competitive analysis including:
        - Top sponsors by number of trials
        - Industry vs academic sponsor distribution
        - Market concentration analysis
        - Key players identification
    
    Use this tool to understand who the major players are in TNBC research
    and identify potential competitors or collaboration partners.
    """
    processor = get_clinical_trials_processor()
    data = processor.processed_data
    return {
        'competitive_landscape': data.get('competitive_landscape', {}),
        'sponsor_analysis': data.get('competitive_landscape', {}),
        'market_insights': {
            'total_unique_sponsors': data.get('competitive_landscape', {}).get('unique_sponsors', 0),
            'industry_dominance': data.get('competitive_landscape', {}).get('sponsor_type_distribution', {}),
            'top_players': data.get('competitive_landscape', {}).get('top_sponsors', {})
        }
    }

@tool
def analyze_trial_enrollment_patterns() -> Dict:
    """
    Analyze enrollment patterns across TNBC clinical trials.
    
    Returns:
        Enrollment analysis including:
        - Enrollment size distributions
        - Average and median enrollment targets
        - Enrollment patterns by phase and sponsor type
        - Geographic enrollment distribution
    
    Use this tool to understand typical enrollment targets and patterns
    in TNBC trials for benchmarking and planning purposes.
    """
    processor = get_clinical_trials_processor()
    data = processor.processed_data
    return {
        'enrollment_analysis': data.get('enrollment_analysis', {}),
        'summary_stats': data.get('summary_stats', {}),
        'geographic_patterns': data.get('geographic_analysis', {}),
        'insights': {
            'typical_enrollment_range': 'Based on median and quartile analysis',
            'international_vs_domestic': data.get('geographic_analysis', {}).get('international_percentage', 0),
            'multi_site_prevalence': data.get('summary_stats', {}).get('avg_locations_per_trial', 0)
        }
    }

@tool
def identify_recruiting_trials() -> Dict:
    """
    Identify currently recruiting TNBC trials and analyze recruitment opportunities.
    
    Returns:
        Recruiting trials analysis including:
        - List of actively recruiting studies
        - Geographic distribution of recruiting sites
        - Enrollment targets and timelines
        - Competitive recruitment landscape
    
    Use this tool to understand the current recruitment environment
    and identify potential competition or collaboration opportunities.
    """
    processor = get_clinical_trials_processor()
    recruiting_trials = processor.search_trials(status="RECRUITING")
    
    return {
        'recruiting_trials_count': recruiting_trials.get('matching_trials', 0),
        'recruiting_trials': recruiting_trials.get('trials', []),
        'recruitment_competition': {
            'total_recruiting_enrollment': sum(
                trial.get('Enrollment', 0) for trial in recruiting_trials.get('trials', [])
                if trial.get('Enrollment') is not None
            ),
            'avg_enrollment_per_recruiting_trial': round(
                sum(trial.get('Enrollment', 0) for trial in recruiting_trials.get('trials', [])
                    if trial.get('Enrollment') is not None) / 
                max(recruiting_trials.get('matching_trials', 1), 1)
            )
        }
    }

@tool
def analyze_trial_geography() -> Dict:
    """
    Analyze geographic distribution of TNBC clinical trials.
    
    Returns:
        Geographic analysis including:
        - Country distribution of trials
        - International vs domestic trial patterns
        - Multi-country trial prevalence
        - Regional concentration analysis
    
    Use this tool to understand where TNBC trials are being conducted
    and identify geographic opportunities or gaps.
    """
    processor = get_clinical_trials_processor()
    data = processor.processed_data
    return {
        'geographic_analysis': data.get('geographic_analysis', {}),
        'international_insights': {
            'global_reach': data.get('geographic_analysis', {}).get('unique_countries', 0),
            'international_prevalence': data.get('geographic_analysis', {}).get('international_percentage', 0),
            'top_countries': data.get('geographic_analysis', {}).get('top_countries', {}),
            'multi_national_trials': data.get('geographic_analysis', {}).get('international_trials', 0)
        }
    }

@tool
def analyze_intervention_trends() -> Dict:
    """
    Analyze intervention and treatment trends in TNBC clinical trials.
    
    Returns:
        Intervention analysis including:
        - Most common intervention types
        - Drug vs non-drug intervention distribution
        - Emerging treatment modalities
        - Innovation patterns
    
    Use this tool to understand current treatment approaches being studied
    and identify trends in TNBC therapeutic development.
    """
    processor = get_clinical_trials_processor()
    data = processor.processed_data
    return {
        'intervention_analysis': data.get('intervention_analysis', {}),
        'treatment_trends': {
            'drug_dominance': data.get('intervention_analysis', {}).get('drug_intervention_percentage', 0),
            'intervention_diversity': len(data.get('intervention_analysis', {}).get('intervention_type_distribution', {})),
            'top_intervention_types': data.get('intervention_analysis', {}).get('intervention_type_distribution', {})
        }
    }

@tool
def benchmark_trial_characteristics(target_enrollment: int, planned_duration_months: int) -> Dict:
    """
    Benchmark proposed trial characteristics against existing TNBC trials.
    
    Args:
        target_enrollment: Proposed enrollment target
        planned_duration_months: Planned study duration in months
    
    Returns:
        Benchmarking analysis including:
        - How proposed trial compares to existing trials
        - Percentile rankings for enrollment and duration
        - Similar trials identification
        - Feasibility assessment
    
    Use this tool to validate trial design parameters against industry standards
    and identify comparable studies for benchmarking purposes.
    """
    processor = get_clinical_trials_processor()
    data = processor.processed_data
    
    # Get enrollment statistics
    enrollment_stats = data.get('enrollment_analysis', {}).get('enrollment_statistics', {})
    duration_stats = data.get('timeline_analysis', {}).get('duration_statistics', {})
    
    # Calculate percentiles (simplified)
    enrollment_percentile = "Not available"
    duration_percentile = "Not available"
    
    if enrollment_stats:
        median_enrollment = enrollment_stats.get('median', 0)
        if target_enrollment <= median_enrollment:
            enrollment_percentile = "Below median (smaller than typical)"
        else:
            enrollment_percentile = "Above median (larger than typical)"
    
    if duration_stats:
        median_duration = duration_stats.get('median_months', 0)
        if planned_duration_months <= median_duration:
            duration_percentile = "Below median (shorter than typical)"
        else:
            duration_percentile = "Above median (longer than typical)"
    
    return {
        'proposed_trial': {
            'enrollment': target_enrollment,
            'duration_months': planned_duration_months
        },
        'benchmark_comparison': {
            'enrollment_benchmark': enrollment_percentile,
            'duration_benchmark': duration_percentile,
            'enrollment_stats': enrollment_stats,
            'duration_stats': duration_stats
        },
        'feasibility_assessment': {
            'enrollment_feasibility': 'Reasonable' if target_enrollment <= enrollment_stats.get('q75', 1000) else 'Ambitious',
            'duration_feasibility': 'Reasonable' if planned_duration_months <= duration_stats.get('mean_months', 60) else 'Extended'
        }
    }