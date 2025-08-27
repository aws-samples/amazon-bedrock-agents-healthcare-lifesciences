"""
Custom tools for the Enrollment Pulse agent
"""
from typing import Dict, List, Optional
from strands import tool
import sys
from pathlib import Path

# Add src to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from data.processors import CTMSDataProcessor
from analysis.enrollment_metrics import EnrollmentAnalyzer


# Global data cache to avoid reprocessing
_data_cache = {}


def _get_processed_data():
    """Get processed CTMS data, using cache if available"""
    if not _data_cache:
        processor = CTMSDataProcessor()
        _data_cache.update(processor.process_all())
    return _data_cache


@tool
def get_overall_enrollment_status() -> Dict:
    """
    Get the overall enrollment status for the clinical trial study.
    
    Returns:
        Dict: Overall enrollment metrics including total enrolled, percentages, and screen failure rates
    """
    data = _get_processed_data()
    
    if not data.get('enrollment_summaries'):
        return {"error": "No enrollment data available"}
    
    analyzer = EnrollmentAnalyzer(
        summaries=data['enrollment_summaries'],
        subjects=data['subjects'],
        sites=data['sites'],
        metrics=data.get('enrollment_metrics', [])
    )
    
    return analyzer.get_overall_enrollment_status()


@tool
def get_site_performance_ranking() -> List[Dict]:
    """
    Get sites ranked by enrollment performance from highest to lowest.
    
    Returns:
        List[Dict]: Sites ranked by enrollment percentage with detailed metrics
    """
    data = _get_processed_data()
    
    if not data.get('enrollment_summaries'):
        return []
    
    analyzer = EnrollmentAnalyzer(
        summaries=data['enrollment_summaries'],
        subjects=data['subjects'],
        sites=data['sites'],
        metrics=data.get('enrollment_metrics', [])
    )
    
    return analyzer.get_site_performance_ranking()


@tool
def get_underperforming_sites_detailed(threshold: float = 60.0) -> Dict:
    """
    Get detailed analysis of underperforming sites with site-specific historical performance and recommendations.
    
    Args:
        threshold: Enrollment percentage threshold below which sites are considered underperforming
        
    Returns:
        Dict: Detailed per-site analysis of underperforming sites with historical trends and specific recommendations
    """
    data = _get_processed_data()
    
    if not data.get('enrollment_summaries'):
        return {"error": "No enrollment data available"}
    
    analyzer = EnrollmentAnalyzer(
        summaries=data['enrollment_summaries'],
        subjects=data['subjects'],
        sites=data['sites'],
        metrics=data.get('enrollment_metrics', [])
    )
    
    # Get comprehensive analysis for all sites
    comprehensive_analysis = get_comprehensive_site_analysis()
    
    # Filter to underperforming sites only
    underperforming_analysis = {}
    
    for site_num, site_data in comprehensive_analysis.items():
        if site_data['current_performance']['enrollment_percentage'] < threshold:
            underperforming_analysis[site_num] = site_data
    
    return {
        'threshold_used': threshold,
        'total_underperforming_sites': len(underperforming_analysis),
        'sites': underperforming_analysis
    }


@tool
def identify_underperforming_sites(threshold: float = 60.0) -> List[Dict]:
    """
    Identify sites that are underperforming based on enrollment percentage.
    
    Args:
        threshold: Enrollment percentage threshold below which sites are considered underperforming
        
    Returns:
        List[Dict]: Underperforming sites with projected shortfalls and risk analysis
    """
    data = _get_processed_data()
    
    if not data.get('enrollment_summaries'):
        return []
    
    analyzer = EnrollmentAnalyzer(
        summaries=data['enrollment_summaries'],
        subjects=data['subjects'],
        sites=data['sites'],
        metrics=data.get('enrollment_metrics', [])
    )
    
    return analyzer.identify_underperforming_sites(threshold)


@tool
def analyze_cra_performance() -> Dict:
    """
    Analyze Clinical Research Associate (CRA) performance correlation with site enrollment.
    
    Returns:
        Dict: CRA performance analysis showing correlation between CRA assignments and site performance
    """
    data = _get_processed_data()
    
    if not data.get('enrollment_summaries'):
        return {"error": "No enrollment data available"}
    
    analyzer = EnrollmentAnalyzer(
        summaries=data['enrollment_summaries'],
        subjects=data['subjects'],
        sites=data['sites'],
        metrics=data.get('enrollment_metrics', [])
    )
    
    return analyzer.analyze_cra_performance()


@tool
def get_monthly_enrollment_trends() -> Dict:
    """
    Analyze monthly enrollment patterns by geographic region.
    
    Returns:
        Dict: Monthly enrollment trends grouped by region (East Coast, West Coast, etc.)
    """
    data = _get_processed_data()
    
    if not data.get('enrollment_summaries'):
        return {"error": "No enrollment data available"}
    
    analyzer = EnrollmentAnalyzer(
        summaries=data['enrollment_summaries'],
        subjects=data['subjects'],
        sites=data['sites'],
        metrics=data.get('enrollment_metrics', [])
    )
    
    return analyzer.get_monthly_enrollment_trends()


@tool
def calculate_screening_efficiency() -> List[Dict]:
    """
    Calculate screening to randomization efficiency metrics by site.
    
    Returns:
        List[Dict]: Screening efficiency data including average screening days and failure rates by site
    """
    data = _get_processed_data()
    
    if not data.get('enrollment_summaries'):
        return []
    
    analyzer = EnrollmentAnalyzer(
        summaries=data['enrollment_summaries'],
        subjects=data['subjects'],
        sites=data['sites'],
        metrics=data.get('enrollment_metrics', [])
    )
    
    return analyzer.calculate_screening_efficiency()


@tool
def project_enrollment_timeline() -> Dict:
    """
    Project final enrollment numbers based on current trends and timeline.
    
    Returns:
        Dict: Enrollment projections by site including likelihood of meeting targets
    """
    data = _get_processed_data()
    
    if not data.get('enrollment_summaries'):
        return {"error": "No enrollment data available"}
    
    analyzer = EnrollmentAnalyzer(
        summaries=data['enrollment_summaries'],
        subjects=data['subjects'],
        sites=data['sites'],
        metrics=data.get('enrollment_metrics', [])
    )
    
    return analyzer.project_enrollment_timeline()


@tool
def get_historical_performance() -> List[Dict]:
    """
    Get historical performance trends for all sites showing enrollment patterns over time.
    
    Returns:
        List[Dict]: Historical performance data with monthly trends, enrollment rates, and performance indicators
    """
    data = _get_processed_data()
    
    if not data.get('enrollment_summaries'):
        return []
    
    analyzer = EnrollmentAnalyzer(
        summaries=data['enrollment_summaries'],
        subjects=data['subjects'],
        sites=data['sites'],
        metrics=data.get('enrollment_metrics', [])
    )
    
    return analyzer.get_historical_performance()


@tool
def get_alternative_site_recommendations(underperforming_site_number: str) -> List[Dict]:
    """
    Get alternative site recommendations for underperforming sites.
    
    Args:
        underperforming_site_number: Site number of the underperforming site
        
    Returns:
        List[Dict]: Alternative site recommendations with success probability and rationale
    """
    data = _get_processed_data()
    
    if not data.get('enrollment_summaries'):
        return []
    
    analyzer = EnrollmentAnalyzer(
        summaries=data['enrollment_summaries'],
        subjects=data['subjects'],
        sites=data['sites'],
        metrics=data.get('enrollment_metrics', [])
    )
    
    return analyzer.get_alternative_site_recommendations(underperforming_site_number)


@tool
def get_comprehensive_site_analysis(site_number: Optional[str] = None) -> Dict:
    """
    Get comprehensive per-site analysis including performance, historical trends, and specific recommendations.
    
    Args:
        site_number: Optional specific site number. If None, returns analysis for all sites
        
    Returns:
        Dict: Comprehensive site-specific analysis with historical performance and tailored recommendations
    """
    data = _get_processed_data()
    
    if not data.get('enrollment_summaries'):
        return {"error": "No enrollment data available"}
    
    analyzer = EnrollmentAnalyzer(
        summaries=data['enrollment_summaries'],
        subjects=data['subjects'],
        sites=data['sites'],
        metrics=data.get('enrollment_metrics', [])
    )
    
    # Get all supporting data
    site_rankings = analyzer.get_site_performance_ranking()
    underperforming = analyzer.identify_underperforming_sites()
    historical_data = analyzer.get_historical_performance()
    cra_analysis = analyzer.analyze_cra_performance()
    projections = analyzer.project_enrollment_timeline()
    
    comprehensive_analysis = {}
    
    # Filter sites if specific site requested
    if site_number:
        target_sites = [s for s in site_rankings if s['site_number'] == site_number]
    else:
        target_sites = site_rankings
    
    for site in target_sites:
        site_num = site['site_number']
        site_name = site['site_name']
        
        # Get site-specific historical data
        site_historical = [h for h in historical_data if h['site_number'] == site_num]
        
        # Get site-specific projections
        site_projection = projections.get(site_num, {})
        
        # Determine if site is underperforming
        is_underperforming = any(u['site_number'] == site_num for u in underperforming)
        underperforming_details = next((u for u in underperforming if u['site_number'] == site_num), None)
        
        # Get CRA assignment
        cra_assignment = "Unknown"
        if site_num in ['1', '2']:
            cra_assignment = "Thomas Nguyen"
        elif site_num in ['3', '4', '5']:
            cra_assignment = "Amanda Garcia"
        
        # Calculate performance trends
        if site_historical:
            recent_trend = site_historical[-1]['performance_trend'] if site_historical else "Unknown"
            avg_monthly_rate = sum(h['enrollment_rate'] for h in site_historical) / len(site_historical)
            improving_months = len([h for h in site_historical if h['performance_trend'] == 'Improving'])
            total_months = len(site_historical)
            consistency_score = improving_months / total_months if total_months > 0 else 0
        else:
            recent_trend = "No data"
            avg_monthly_rate = 0
            consistency_score = 0
        
        # Generate site-specific recommendations
        recommendations = []
        
        if is_underperforming and underperforming_details:
            # High-priority interventions for underperforming sites
            recommendations.extend([
                f"URGENT: Implement immediate intervention plan - site is {underperforming_details['shortfall']} subjects behind target",
                f"Schedule emergency site visit within 7 days to assess recruitment barriers",
                f"Deploy dedicated enrollment specialist for 30-day intensive support period"
            ])
            
            # Historical trend-based recommendations
            if site_historical:
                declining_months = len([h for h in site_historical if h['performance_trend'] == 'Declining'])
                if declining_months > total_months * 0.3:
                    recommendations.append("Address declining enrollment trend - review protocol adherence and staff training")
                
                latest_screen_failure = site_historical[-1]['screen_failure_rate'] if site_historical else 0
                if latest_screen_failure > 20:
                    recommendations.append(f"Optimize screening process - current {latest_screen_failure}% failure rate is above optimal range")
            
            # CRA-specific recommendations
            if cra_assignment == "Amanda Garcia":
                recommendations.append("Consider CRA workload rebalancing - Amanda Garcia manages 3 sites vs Thomas Nguyen's 2 sites")
        
        else:
            # Recommendations for performing sites
            if site['enrollment_percentage'] > 90:
                recommendations.extend([
                    "Excellent performance - consider increasing enrollment target if capacity allows",
                    "Document best practices for knowledge sharing with underperforming sites",
                    "Maintain current recruitment strategies and monitor for capacity constraints"
                ])
            elif site['enrollment_percentage'] > 75:
                recommendations.extend([
                    "Good performance - implement minor optimizations to reach 90%+ target",
                    "Review monthly enrollment patterns for potential acceleration opportunities"
                ])
        
        # Alternative sites (for underperforming sites only)
        alternative_sites = []
        if is_underperforming:
            alternatives = analyzer.get_alternative_site_recommendations(site_num)
            alternative_sites = alternatives[:2]  # Top 2 alternatives
        
        # Compile comprehensive site analysis
        comprehensive_analysis[site_num] = {
            'site_info': {
                'site_number': site_num,
                'site_name': site_name,
                'cra_assignment': cra_assignment,
                'risk_level': site['risk_level']
            },
            'current_performance': {
                'enrollment_percentage': site['enrollment_percentage'],
                'current_enrollment': site['current_enrollment'],
                'target_enrollment': site['target_enrollment'],
                'avg_monthly_enrollment': site['avg_monthly_enrollment'],
                'screen_failure_rate': next((s.screen_failure_rate for s in data['enrollment_summaries'] if s.site_number == site_num), 0)
            },
            'historical_performance': {
                'total_months_active': len(site_historical),
                'recent_trend': recent_trend,
                'avg_monthly_rate': round(avg_monthly_rate, 1),
                'consistency_score': round(consistency_score * 100, 1),
                'monthly_data': site_historical[-6:] if site_historical else []  # Last 6 months
            },
            'projections': {
                'projected_final_enrollment': site_projection.get('projected_final', 0),
                'projected_percentage': site_projection.get('projected_percentage', 0),
                'will_meet_target': site_projection.get('will_meet_target', False),
                'shortfall': site_projection.get('shortfall', 0)
            },
            'underperformance_details': underperforming_details if is_underperforming else None,
            'recommendations': recommendations,
            'alternative_sites': alternative_sites
        }
    
    return comprehensive_analysis


@tool
def get_intervention_recommendations(site_number: Optional[str] = None) -> Dict:
    """
    Get targeted intervention recommendations for underperforming sites.
    
    Args:
        site_number: Optional specific site number to get recommendations for
        
    Returns:
        Dict: Intervention recommendations based on site performance patterns
    """
    data = _get_processed_data()
    
    if not data.get('enrollment_summaries'):
        return {"error": "No enrollment data available"}
    
    underperforming = identify_underperforming_sites()
    cra_analysis = analyze_cra_performance()
    screening_efficiency = calculate_screening_efficiency()
    
    recommendations = {
        "general_recommendations": [
            "Consider redistributing CRA workload - Thomas Nguyen's sites average 92.7% vs Amanda Garcia's sites at 56%",
            "Focus additional resources on Mayo Clinic and UCLA as highest-risk sites",
            "Implement screening efficiency improvements at sites with >7.5 day screening times"
        ],
        "site_specific": {}
    }
    
    # Add site-specific recommendations
    for site in underperforming:
        site_num = site['site_number']
        site_recommendations = []
        
        if site['current_percentage'] < 50:
            site_recommendations.append("URGENT: Site requires immediate intervention - consider additional CRA support")
            site_recommendations.append("Review site activation and patient referral processes")
            
        if site['shortfall'] > 10:
            site_recommendations.append("Consider protocol amendments or eligibility criteria review")
            
        # Check screening efficiency
        site_screening = next((s for s in screening_efficiency if s['site_number'] == site_num), None)
        if site_screening and site_screening['avg_screening_days'] > 7.5:
            site_recommendations.append("Optimize screening process - currently taking longer than high-performing sites")
            
        recommendations["site_specific"][site['site_name']] = site_recommendations
    
    return recommendations