"""
Live Clinical Trials Analysis Tools using ClinicalTrials.gov API
"""
from strands import tool
from typing import Dict, List, Optional
import sys
from pathlib import Path
import logging
import pandas as pd

# Add src to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from data.clinicaltrials_api_client import ClinicalTrialsAPIClient

logger = logging.getLogger(__name__)

# Global API client instance
_api_client = None

def get_api_client():
    """Get or create API client instance"""
    global _api_client
    if _api_client is None:
        _api_client = ClinicalTrialsAPIClient()
    return _api_client

@tool
def search_live_clinical_trials(
    condition: Optional[str] = None,
    intervention: Optional[str] = None,
    status: Optional[str] = None,
    phase: Optional[str] = None,
    sponsor_type: Optional[str] = None,
    country: Optional[str] = None,
    max_results: int = 100
) -> Dict:
    """
    Search live clinical trials data from ClinicalTrials.gov API.
    
    Args:
        condition: Medical condition (e.g., "breast cancer", "triple negative breast cancer")
        intervention: Intervention name (e.g., "pembrolizumab", "immunotherapy")
        status: Trial status ("RECRUITING", "ACTIVE_NOT_RECRUITING", "COMPLETED")
        phase: Trial phase ("PHASE1", "PHASE2", "PHASE3", "PHASE4")
        sponsor_type: Sponsor type ("INDUSTRY", "NIH", "OTHER_GOV", "OTHER")
        country: Country name (e.g., "United States", "Canada")
        max_results: Maximum number of results to return
    
    Returns:
        Live clinical trials data including current recruitment status,
        enrollment targets, locations, and competitive landscape.
    
    Use this tool to get the most current clinical trials information
    for competitive analysis and market research.
    """
    try:
        client = get_api_client()
        
        # Convert single values to lists for API
        status_list = [status] if status else None
        phase_list = [phase] if phase else None
        
        # Search studies
        response = client.search_studies(
            condition=condition,
            intervention=intervention,
            status=status_list,
            phase=phase_list,
            sponsor_type=sponsor_type,
            location_country=country,
            page_size=min(max_results, 1000)
        )
        
        studies = response.get('studies', [])
        
        # Extract key information
        results = []
        for study in studies[:max_results]:
            protocol_section = study.get('protocolSection', {})
            identification_module = protocol_section.get('identificationModule', {})
            status_module = protocol_section.get('statusModule', {})
            design_module = protocol_section.get('designModule', {})
            
            study_info = {
                'nct_id': identification_module.get('nctId'),
                'title': identification_module.get('briefTitle'),
                'status': status_module.get('overallStatus'),
                'phase': '|'.join(design_module.get('phases', [])),
                'enrollment': design_module.get('enrollmentInfo', {}).get('count', 0),
                'start_date': status_module.get('startDateStruct', {}).get('date'),
                'sponsor': protocol_section.get('sponsorCollaboratorsModule', {}).get('leadSponsor', {}).get('name'),
                'conditions': '|'.join(protocol_section.get('conditionsModule', {}).get('conditions', [])),
                'brief_summary': identification_module.get('briefSummary', '')[:200] + '...' if identification_module.get('briefSummary') else ''
            }
            results.append(study_info)
        
        return {
            'total_found': response.get('totalCount', 0),
            'returned_count': len(results),
            'studies': results,
            'search_criteria': {
                'condition': condition,
                'intervention': intervention,
                'status': status,
                'phase': phase,
                'sponsor_type': sponsor_type,
                'country': country
            }
        }
        
    except Exception as e:
        logger.warning(f"Error searching live clinical trials: {e}")
        return {
            'error': str(e),
            'total_found': 0,
            'returned_count': 0,
            'studies': []
        }

@tool
def get_live_trial_details(nct_id: str) -> Dict:
    """
    Get detailed information for a specific clinical trial from live API.
    
    Args:
        nct_id: NCT number (e.g., "NCT05035745")
    
    Returns:
        Comprehensive trial details including:
        - Complete study protocol information
        - Current enrollment status and targets
        - Detailed location and contact information
        - Eligibility criteria
        - Primary and secondary outcomes
        - Timeline and milestones
    
    Use this tool to get the most current and detailed information
    about specific trials for competitive analysis.
    """
    try:
        client = get_api_client()
        response = client.get_study_details(nct_id)
        
        protocol_section = response.get('protocolSection', {})
        
        # Extract comprehensive details
        identification_module = protocol_section.get('identificationModule', {})
        status_module = protocol_section.get('statusModule', {})
        design_module = protocol_section.get('designModule', {})
        arms_interventions_module = protocol_section.get('armsInterventionsModule', {})
        outcomes_module = protocol_section.get('outcomesModule', {})
        eligibility_module = protocol_section.get('eligibilityModule', {})
        contacts_locations_module = protocol_section.get('contactsLocationsModule', {})
        sponsor_collaborators_module = protocol_section.get('sponsorCollaboratorsModule', {})
        
        return {
            'basic_info': {
                'nct_id': identification_module.get('nctId'),
                'title': identification_module.get('briefTitle'),
                'official_title': identification_module.get('officialTitle'),
                'brief_summary': identification_module.get('briefSummary'),
                'detailed_description': identification_module.get('detailedDescription')
            },
            'status_info': {
                'overall_status': status_module.get('overallStatus'),
                'start_date': status_module.get('startDateStruct', {}).get('date'),
                'completion_date': status_module.get('completionDateStruct', {}).get('date'),
                'primary_completion_date': status_module.get('primaryCompletionDateStruct', {}).get('date'),
                'last_update': status_module.get('lastUpdatePostDateStruct', {}).get('date'),
                'study_first_posted': status_module.get('studyFirstPostDateStruct', {}).get('date')
            },
            'design_info': {
                'study_type': design_module.get('studyType'),
                'phases': design_module.get('phases', []),
                'allocation': design_module.get('designInfo', {}).get('allocation'),
                'intervention_model': design_module.get('designInfo', {}).get('interventionModel'),
                'masking': design_module.get('designInfo', {}).get('maskingInfo', {}).get('masking'),
                'primary_purpose': design_module.get('designInfo', {}).get('primaryPurpose'),
                'enrollment_count': design_module.get('enrollmentInfo', {}).get('count'),
                'enrollment_type': design_module.get('enrollmentInfo', {}).get('type')
            },
            'interventions': [
                {
                    'type': intervention.get('type'),
                    'name': intervention.get('name'),
                    'description': intervention.get('description')
                }
                for intervention in arms_interventions_module.get('interventions', [])
            ],
            'outcomes': {
                'primary': [
                    {
                        'measure': outcome.get('measure'),
                        'description': outcome.get('description'),
                        'time_frame': outcome.get('timeFrame')
                    }
                    for outcome in outcomes_module.get('primaryOutcomes', [])
                ],
                'secondary': [
                    {
                        'measure': outcome.get('measure'),
                        'description': outcome.get('description'),
                        'time_frame': outcome.get('timeFrame')
                    }
                    for outcome in outcomes_module.get('secondaryOutcomes', [])
                ]
            },
            'eligibility': {
                'criteria': eligibility_module.get('eligibilityCriteria'),
                'gender': eligibility_module.get('sex'),
                'minimum_age': eligibility_module.get('minimumAge'),
                'maximum_age': eligibility_module.get('maximumAge'),
                'healthy_volunteers': eligibility_module.get('healthyVolunteers')
            },
            'locations': [
                {
                    'facility': location.get('facility'),
                    'city': location.get('city'),
                    'state': location.get('state'),
                    'country': location.get('country'),
                    'zip_code': location.get('zip'),
                    'status': location.get('status')
                }
                for location in contacts_locations_module.get('locations', [])
            ],
            'sponsor_info': {
                'lead_sponsor': sponsor_collaborators_module.get('leadSponsor', {}),
                'collaborators': sponsor_collaborators_module.get('collaborators', [])
            },
            'conditions': protocol_section.get('conditionsModule', {}).get('conditions', []),
            'keywords': protocol_section.get('conditionsModule', {}).get('keywords', [])
        }
        
    except Exception as e:
        logger.warning(f"Error getting trial details for {nct_id}: {e}")
        return {'error': str(e)}

@tool
def analyze_live_competitive_landscape(condition: str, max_studies: int = 500) -> Dict:
    """
    Analyze the current competitive landscape for a medical condition using live data.
    
    Args:
        condition: Medical condition to analyze (e.g., "breast cancer", "oncology")
        max_studies: Maximum number of studies to analyze
    
    Returns:
        Comprehensive competitive analysis including:
        - Current recruitment competition
        - Top sponsors and their market share
        - Phase distribution of active trials
        - Geographic distribution
        - Enrollment targets and capacity
        - Recent trends and new entrants
    
    Use this tool to understand the current competitive environment
    and identify market opportunities or threats.
    """
    try:
        client = get_api_client()
        
        # Get comprehensive data
        studies = client.search_all_pages(
            condition=condition,
            page_size=min(max_studies, 1000)
        )
        
        if not studies:
            return {'error': 'No studies found for the specified condition'}
        
        # Convert to DataFrame for analysis
        df = client.get_enrollment_data(studies)
        
        # Analyze recruiting competition
        recruiting_df = df[df['status'] == 'RECRUITING']
        
        # Sponsor analysis
        sponsor_counts = df['sponsor'].value_counts()
        recruiting_sponsor_counts = recruiting_df['sponsor'].value_counts()
        
        # Phase analysis
        phase_counts = df['phase'].value_counts()
        recruiting_phase_counts = recruiting_df['phase'].value_counts()
        
        # Geographic analysis
        all_countries = []
        for countries_str in df['countries'].dropna():
            all_countries.extend(countries_str.split('|'))
        country_counts = pd.Series(all_countries).value_counts()
        
        # Enrollment analysis
        total_enrollment = df['enrollment_count'].sum()
        recruiting_enrollment = recruiting_df['enrollment_count'].sum()
        
        return {
            'overview': {
                'total_studies': int(len(df)),
                'recruiting_studies': int(len(recruiting_df)),
                'completed_studies': int(len(df[df['status'] == 'COMPLETED'])),
                'total_planned_enrollment': int(total_enrollment),
                'recruiting_enrollment_capacity': int(recruiting_enrollment),
                'avg_enrollment_per_study': round(float(df['enrollment_count'].mean()), 1)
            },
            'sponsor_landscape': {
                'total_unique_sponsors': int(len(sponsor_counts)),
                'top_sponsors_all': {k: int(v) for k, v in sponsor_counts.head(10).to_dict().items()},
                'top_sponsors_recruiting': {k: int(v) for k, v in recruiting_sponsor_counts.head(10).to_dict().items()},
                'sponsor_concentration': {
                    'top_5_market_share': round(float(sponsor_counts.head(5).sum()) / len(df) * 100, 1),
                    'top_10_market_share': round(float(sponsor_counts.head(10).sum()) / len(df) * 100, 1)
                }
            },
            'phase_distribution': {
                'all_studies': {k: int(v) for k, v in phase_counts.to_dict().items()},
                'recruiting_studies': {k: int(v) for k, v in recruiting_phase_counts.to_dict().items()},
                'early_phase_percentage': round(
                    len(df[df['phase'].str.contains('PHASE1', na=False)]) / len(df) * 100, 1
                )
            },
            'geographic_distribution': {
                'top_countries': {k: int(v) for k, v in country_counts.head(10).to_dict().items()},
                'international_studies': int(len(df[df['countries'].str.contains('\\|', na=False)])),
                'us_studies': int(country_counts.get('United States', 0))
            },
            'recruitment_competition': {
                'actively_recruiting': int(len(recruiting_df)),
                'recruitment_capacity': int(recruiting_enrollment),
                'avg_recruiting_enrollment': round(float(recruiting_df['enrollment_count'].mean()), 1) if len(recruiting_df) > 0 else 0,
                'competition_intensity': 'High' if len(recruiting_df) > 50 else 'Medium' if len(recruiting_df) > 20 else 'Low'
            },
            'market_insights': {
                'market_maturity': 'Mature' if len(df) > 100 else 'Developing' if len(df) > 50 else 'Emerging',
                'innovation_activity': 'High' if len(recruiting_df) > 20 else 'Medium' if len(recruiting_df) > 10 else 'Low',
                'entry_barriers': 'High' if recruiting_enrollment > 10000 else 'Medium' if recruiting_enrollment > 5000 else 'Low'
            }
        }
        
    except Exception as e:
        logger.warning(f"Error analyzing competitive landscape: {e}")
        return {'error': str(e)}

@tool
def find_recruiting_trials_by_location(
    condition: str,
    country: Optional[str] = None,
    state: Optional[str] = None,
    city: Optional[str] = None
) -> Dict:
    """
    Find currently recruiting trials by geographic location.
    
    Args:
        condition: Medical condition
        country: Country name (e.g., "United States")
        state: State/province name (e.g., "California")
        city: City name (e.g., "San Francisco")
    
    Returns:
        List of recruiting trials in the specified location with:
        - Trial details and contact information
        - Enrollment targets and current status
        - Facility information
        - Geographic competition analysis
    
    Use this tool to understand recruitment competition in specific
    geographic markets and identify expansion opportunities.
    """
    try:
        client = get_api_client()
        
        # Search for recruiting trials
        studies = client.search_all_pages(
            condition=condition,
            status=['RECRUITING'],
            location_country=country,
            page_size=1000
        )
        
        if not studies:
            return {'error': 'No recruiting studies found for the specified criteria'}
        
        # Filter by state/city if specified
        filtered_studies = []
        for study in studies:
            protocol_section = study.get('protocolSection', {})
            contacts_locations_module = protocol_section.get('contactsLocationsModule', {})
            locations = contacts_locations_module.get('locations', [])
            
            # Check if study has locations matching criteria
            matching_locations = []
            for location in locations:
                location_match = True
                
                if state and location.get('state', '').lower() != state.lower():
                    location_match = False
                if city and location.get('city', '').lower() != city.lower():
                    location_match = False
                
                if location_match:
                    matching_locations.append(location)
            
            if matching_locations:
                # Add study with matching locations
                study_info = {
                    'nct_id': protocol_section.get('identificationModule', {}).get('nctId'),
                    'title': protocol_section.get('identificationModule', {}).get('briefTitle'),
                    'sponsor': protocol_section.get('sponsorCollaboratorsModule', {}).get('leadSponsor', {}).get('name'),
                    'phase': '|'.join(protocol_section.get('designModule', {}).get('phases', [])),
                    'enrollment': protocol_section.get('designModule', {}).get('enrollmentInfo', {}).get('count', 0),
                    'matching_locations': matching_locations,
                    'total_locations': len(locations)
                }
                filtered_studies.append(study_info)
        
        # Calculate competition metrics
        total_enrollment = sum(study['enrollment'] for study in filtered_studies)
        
        return {
            'search_criteria': {
                'condition': condition,
                'country': country,
                'state': state,
                'city': city
            },
            'results': {
                'recruiting_trials_found': len(filtered_studies),
                'total_enrollment_capacity': total_enrollment,
                'avg_enrollment_per_trial': round(total_enrollment / max(len(filtered_studies), 1), 1),
                'trials': filtered_studies
            },
            'competition_analysis': {
                'competition_level': 'High' if len(filtered_studies) > 10 else 'Medium' if len(filtered_studies) > 5 else 'Low',
                'market_saturation': 'High' if total_enrollment > 5000 else 'Medium' if total_enrollment > 2000 else 'Low',
                'opportunity_assessment': 'Limited' if len(filtered_studies) > 15 else 'Moderate' if len(filtered_studies) > 8 else 'Good'
            }
        }
        
    except Exception as e:
        logger.warning(f"Error finding recruiting trials by location: {e}")
        return {'error': str(e)}

@tool
def track_enrollment_trends(condition: str, months_back: int = 12) -> Dict:
    """
    Track enrollment trends and new trial starts over time.
    
    Args:
        condition: Medical condition to track
        months_back: Number of months to look back for trend analysis
    
    Returns:
        Trend analysis including:
        - New trial starts by month
        - Enrollment capacity trends
        - Sponsor activity patterns
        - Market momentum indicators
    
    Use this tool to understand market dynamics and timing
    for competitive positioning and market entry decisions.
    """
    try:
        client = get_api_client()
        
        # Get all studies for the condition
        studies = client.search_all_pages(
            condition=condition,
            page_size=1000
        )
        
        if not studies:
            return {'error': 'No studies found for trend analysis'}
        
        # Convert to DataFrame for time series analysis
        df = client.get_enrollment_data(studies)
        
        # Convert dates and filter recent studies
        df['start_date'] = pd.to_datetime(df['start_date'], errors='coerce')
        
        # Filter to recent studies
        cutoff_date = pd.Timestamp.now() - pd.DateOffset(months=months_back)
        recent_df = df[df['start_date'] >= cutoff_date].copy()
        
        if recent_df.empty:
            return {'error': f'No studies started in the last {months_back} months'}
        
        # Group by month
        recent_df['start_month'] = recent_df['start_date'].dt.to_period('M')
        monthly_stats = recent_df.groupby('start_month').agg({
            'nct_id': 'count',
            'enrollment_count': 'sum',
            'sponsor': 'nunique'
        }).rename(columns={
            'nct_id': 'new_trials',
            'enrollment_count': 'total_enrollment',
            'sponsor': 'unique_sponsors'
        })
        
        # Calculate trends
        trend_data = []
        for month, stats in monthly_stats.iterrows():
            trend_data.append({
                'month': str(month),
                'new_trials': int(stats['new_trials']),
                'total_enrollment': int(stats['total_enrollment']),
                'unique_sponsors': int(stats['unique_sponsors']),
                'avg_enrollment_per_trial': round(stats['total_enrollment'] / stats['new_trials'], 1)
            })
        
        # Calculate overall trends
        total_new_trials = monthly_stats['new_trials'].sum()
        total_enrollment = monthly_stats['total_enrollment'].sum()
        
        # Identify most active sponsors in recent period
        recent_sponsor_activity = recent_df['sponsor'].value_counts()
        
        return {
            'analysis_period': {
                'months_analyzed': months_back,
                'start_date': str(cutoff_date.date()),
                'end_date': str(pd.Timestamp.now().date())
            },
            'overall_trends': {
                'total_new_trials': int(total_new_trials),
                'total_new_enrollment_capacity': int(total_enrollment),
                'avg_trials_per_month': round(total_new_trials / months_back, 1),
                'avg_enrollment_per_month': round(total_enrollment / months_back, 1)
            },
            'monthly_breakdown': trend_data,
            'sponsor_activity': {
                'most_active_sponsors': recent_sponsor_activity.head(10).to_dict(),
                'total_active_sponsors': len(recent_sponsor_activity)
            },
            'market_momentum': {
                'activity_level': 'High' if total_new_trials > months_back * 2 else 'Medium' if total_new_trials > months_back else 'Low',
                'growth_trend': 'Increasing' if len(trend_data) > 6 and trend_data[-3:][0]['new_trials'] < trend_data[-1]['new_trials'] else 'Stable',
                'market_interest': 'High' if len(recent_sponsor_activity) > 20 else 'Medium' if len(recent_sponsor_activity) > 10 else 'Low'
            }
        }
        
    except Exception as e:
        logger.warning(f"Error tracking enrollment trends: {e}")
        return {'error': str(e)}