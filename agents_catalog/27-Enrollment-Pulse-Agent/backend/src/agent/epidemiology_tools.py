"""
Epidemiology Analysis Tools for Strands Agent
"""
from strands import tool
from typing import Dict, List, Optional
import sys
from pathlib import Path

# Add src to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from data.epidemiology_processor import EpidemiologyProcessor

# Global processor instance
_epidemiology_processor = None

def get_epidemiology_processor():
    """Get or create epidemiology processor instance"""
    global _epidemiology_processor
    if _epidemiology_processor is None:
        _epidemiology_processor = EpidemiologyProcessor()
        _epidemiology_processor.process_data()
    return _epidemiology_processor

@tool
def get_epidemiology_overview() -> Dict:
    """
    Get comprehensive overview of MTNBC epidemiology data across metro areas.
    
    Returns detailed analysis including:
    - Summary statistics for all metro areas
    - Top markets by patient count, density, and recruitment feasibility
    - Biomarker distribution analysis
    - Recruitment potential assessment
    
    Use this tool to understand the overall landscape of MTNBC patient populations
    and identify the most promising markets for clinical trial recruitment.
    """
    processor = get_epidemiology_processor()
    return processor.get_market_analysis()

@tool
def analyze_market_epidemiology(metro_name: str) -> Dict:
    """
    Get detailed epidemiological analysis for a specific metropolitan area.
    
    Args:
        metro_name: Name of the metropolitan area (e.g., "San Francisco", "New York", "Los Angeles")
    
    Returns:
        Detailed market analysis including:
        - Population demographics (female 40+ population)
        - MTNBC incidence and prevalence rates
        - Biomarker profiles (PD-L1, BRCA mutations)
        - Trial eligibility estimates
        - Recruitment feasibility scoring
    
    Use this tool to get in-depth analysis of patient populations in specific markets
    for site selection and recruitment planning.
    """
    processor = get_epidemiology_processor()
    return processor.get_market_analysis(metro_name)

@tool
def compare_market_epidemiology(market_names: List[str]) -> Dict:
    """
    Compare epidemiological data across multiple metropolitan areas.
    
    Args:
        market_names: List of metropolitan area names to compare
    
    Returns:
        Comparative analysis including:
        - Side-by-side market metrics
        - Rankings by patient count, eligibility, and feasibility
        - Relative market attractiveness assessment
    
    Use this tool to evaluate and rank potential markets for clinical trial sites
    based on patient population characteristics and recruitment potential.
    """
    processor = get_epidemiology_processor()
    return processor.compare_markets(market_names)

@tool
def get_biomarker_landscape() -> Dict:
    """
    Analyze biomarker distribution patterns across all metropolitan areas.
    
    Returns:
        Comprehensive biomarker analysis including:
        - PD-L1 positive percentage distributions
        - BRCA mutation prevalence patterns
        - Biomarker-positive patient pool estimates
        - Risk category classifications
    
    Use this tool to understand biomarker prevalence patterns that affect
    trial eligibility and patient stratification strategies.
    """
    processor = get_epidemiology_processor()
    data = processor.get_market_analysis()
    return data.get('biomarker_analysis', {})

@tool
def identify_high_potential_markets() -> Dict:
    """
    Identify metropolitan areas with highest recruitment potential for MTNBC trials.
    
    Returns:
        Market segmentation analysis including:
        - High potential markets (feasibility score ≥0.8)
        - Medium potential markets (feasibility score 0.6-0.8)
        - Low potential markets (feasibility score <0.6)
        - Total eligible patient counts by segment
    
    Use this tool to prioritize markets for site selection and resource allocation
    based on recruitment feasibility scoring.
    """
    processor = get_epidemiology_processor()
    data = processor.get_market_analysis()
    return data.get('recruitment_potential', {})

@tool
def get_patient_density_analysis() -> Dict:
    """
    Analyze MTNBC patient density patterns across metropolitan areas.
    
    Returns:
        Patient density analysis including:
        - Markets ranked by patient density index
        - Population concentration patterns
        - Geographic distribution insights
    
    Use this tool to understand where MTNBC patients are most concentrated
    geographically for optimal site placement strategies.
    """
    processor = get_epidemiology_processor()
    data = processor.get_market_analysis()
    return {
        'top_density_markets': data.get('top_markets', {}).get('by_density', []),
        'summary_stats': data.get('summary_stats', {}),
        'analysis_note': 'Patient density index >1.0 indicates above-average concentration of MTNBC patients'
    }

@tool
def estimate_trial_recruitment_pool(target_enrollment: int, eligibility_criteria_selectivity: float = 1.0) -> Dict:
    """
    Estimate recruitment pool size and market coverage needed for target enrollment.
    
    Args:
        target_enrollment: Target number of patients to enroll
        eligibility_criteria_selectivity: Factor to adjust for additional eligibility criteria (0.1-1.0)
    
    Returns:
        Recruitment pool analysis including:
        - Required patient pool size
        - Market coverage recommendations
        - Feasibility assessment
        - Geographic distribution strategy
    
    Use this tool to plan recruitment strategies and determine how many markets
    are needed to achieve target enrollment goals.
    """
    processor = get_epidemiology_processor()
    data = processor.get_market_analysis()
    
    # Calculate adjusted pool requirements
    base_eligible_pool = data.get('summary_stats', {}).get('total_trial_eligible', 0)
    adjusted_pool = int(base_eligible_pool * eligibility_criteria_selectivity)
    
    # Estimate recruitment rate (typically 10-30% of eligible patients actually enroll)
    recruitment_rates = [0.1, 0.2, 0.3]
    scenarios = {}
    
    for rate in recruitment_rates:
        potential_enrollment = int(adjusted_pool * rate)
        coverage_needed = min(target_enrollment / potential_enrollment, 1.0) if potential_enrollment > 0 else 1.0
        
        scenarios[f'{int(rate*100)}%_recruitment_rate'] = {
            'potential_enrollment': potential_enrollment,
            'feasibility': 'High' if potential_enrollment >= target_enrollment else 'Medium' if potential_enrollment >= target_enrollment * 0.7 else 'Low',
            'market_coverage_needed': f'{coverage_needed:.1%}',
            'recommended_markets': int(len(data.get('metro_areas', [])) * coverage_needed)
        }
    
    return {
        'target_enrollment': target_enrollment,
        'adjusted_eligible_pool': adjusted_pool,
        'selectivity_factor': eligibility_criteria_selectivity,
        'recruitment_scenarios': scenarios,
        'top_markets_recommendation': data.get('top_markets', {}).get('by_feasibility', [])[:5]
    }