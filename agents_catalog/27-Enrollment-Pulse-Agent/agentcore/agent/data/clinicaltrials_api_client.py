"""
ClinicalTrials.gov API Client for Live Data Integration
"""
import requests
import pandas as pd
from typing import Dict, List, Optional, Union
import logging
import time
from datetime import datetime, timedelta
import json

logger = logging.getLogger(__name__)

class ClinicalTrialsAPIClient:
    """Client for ClinicalTrials.gov API v2"""
    
    def __init__(self):
        self.base_url = "https://clinicaltrials.gov/api/v2"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'EnrollmentPulse/1.0 (Clinical Trial Analysis Tool)',
            'Accept': 'application/json'
        })
        
    def search_studies(self, 
                      query: Optional[str] = None,
                      condition: Optional[str] = None,
                      intervention: Optional[str] = None,
                      status: Optional[List[str]] = None,
                      phase: Optional[List[str]] = None,
                      sponsor_type: Optional[str] = None,
                      location_country: Optional[str] = None,
                      min_age: Optional[str] = None,
                      max_age: Optional[str] = None,
                      gender: Optional[str] = None,
                      page_size: int = 100,
                      page_token: Optional[str] = None) -> Dict:
        """
        Search studies using ClinicalTrials.gov API v2
        
        Args:
            query: Free text search query
            condition: Condition or disease
            intervention: Intervention name
            status: List of study statuses (e.g., ['RECRUITING', 'ACTIVE_NOT_RECRUITING'])
            phase: List of phases (e.g., ['PHASE1', 'PHASE2'])
            sponsor_type: 'INDUSTRY', 'NIH', 'OTHER_GOV', 'OTHER'
            location_country: Country name
            min_age: Minimum age (e.g., '18 Years')
            max_age: Maximum age (e.g., '65 Years')
            gender: 'ALL', 'FEMALE', 'MALE'
            page_size: Number of results per page (max 1000)
            page_token: Token for pagination
            
        Returns:
            API response with studies data
        """
        url = f"{self.base_url}/studies"
        
        params = {
            'format': 'json',
            'pageSize': min(page_size, 1000)
        }
        
        # Add search parameters
        if query:
            params['query.term'] = query
        if condition:
            params['query.cond'] = condition
        if intervention:
            params['query.intr'] = intervention
        if status:
            params['filter.overallStatus'] = '|'.join(status)
        if phase:
            params['filter.phase'] = '|'.join(phase)
        if sponsor_type:
            params['filter.leadSponsorClass'] = sponsor_type
        if location_country:
            params['filter.geo'] = location_country
        if min_age:
            params['filter.minAge'] = min_age
        if max_age:
            params['filter.maxAge'] = max_age
        if gender:
            params['filter.sex'] = gender
        if page_token:
            params['pageToken'] = page_token
            
        try:
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.warning(f"Error searching studies: {e}")
            raise
    
    def get_study_details(self, nct_id: str) -> Dict:
        """
        Get detailed information for a specific study
        
        Args:
            nct_id: NCT number (e.g., 'NCT05035745')
            
        Returns:
            Detailed study information
        """
        url = f"{self.base_url}/studies/{nct_id}"
        
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.warning(f"Error getting study details for {nct_id}: {e}")
            raise
    
    def get_multiple_studies(self, nct_ids: List[str]) -> Dict:
        """
        Get details for multiple studies in a single request
        
        Args:
            nct_ids: List of NCT numbers
            
        Returns:
            Studies data
        """
        url = f"{self.base_url}/studies"
        params = {
            'filter.ids': '|'.join(nct_ids),
            'format': 'json'
        }
        
        try:
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.warning(f"Error getting multiple studies: {e}")
            raise
    
    def search_all_pages(self, **search_params) -> List[Dict]:
        """
        Search all pages of results for a query
        
        Args:
            **search_params: Parameters to pass to search_studies
            
        Returns:
            List of all studies from all pages
        """
        all_studies = []
        page_token = None
        max_pages = 50  # Safety limit
        page_count = 0
        
        while page_count < max_pages:
            try:
                response = self.search_studies(page_token=page_token, **search_params)
                
                studies = response.get('studies', [])
                all_studies.extend(studies)
                
                # Check if there are more pages
                page_token = response.get('nextPageToken')
                if not page_token:
                    break
                    
                page_count += 1
                # Rate limiting handled by API server
                
            except Exception as e:
                logger.warning(f"Error on page {page_count}: {e}")
                break
        
        logger.info(f"Retrieved {len(all_studies)} studies across {page_count + 1} pages")
        return all_studies
    
    def search_oncology_trials(self, 
                              cancer_type: Optional[str] = None,
                              include_recruiting: bool = True) -> List[Dict]:
        """
        Search for oncology/cancer trials
        
        Args:
            cancer_type: Specific cancer type (e.g., 'breast cancer', 'lung cancer')
            include_recruiting: Whether to include only recruiting trials
            
        Returns:
            List of oncology trials
        """
        search_params = {
            'condition': cancer_type or 'cancer',
            'page_size': 1000
        }
        
        if include_recruiting:
            search_params['status'] = ['RECRUITING', 'ACTIVE_NOT_RECRUITING']
        
        return self.search_all_pages(**search_params)
    
    def search_breast_cancer_trials(self, 
                                   subtype: Optional[str] = None,
                                   phase: Optional[List[str]] = None) -> List[Dict]:
        """
        Search specifically for breast cancer trials
        
        Args:
            subtype: Breast cancer subtype (e.g., 'triple negative', 'HER2 positive')
            phase: Trial phases to include
            
        Returns:
            List of breast cancer trials
        """
        condition = "breast cancer"
        if subtype:
            condition = f"breast cancer {subtype}"
        
        search_params = {
            'condition': condition,
            'status': ['RECRUITING', 'ACTIVE_NOT_RECRUITING', 'COMPLETED'],
            'page_size': 1000
        }
        
        if phase:
            search_params['phase'] = phase
        
        return self.search_all_pages(**search_params)
    
    def get_enrollment_data(self, studies: List[Dict]) -> pd.DataFrame:
        """
        Extract enrollment data from studies for analysis
        
        Args:
            studies: List of study data from API
            
        Returns:
            DataFrame with enrollment information
        """
        enrollment_data = []
        
        for study in studies:
            protocol_section = study.get('protocolSection', {})
            design_module = protocol_section.get('designModule', {})
            status_module = protocol_section.get('statusModule', {})
            identification_module = protocol_section.get('identificationModule', {})
            
            enrollment_info = design_module.get('enrollmentInfo', {})
            
            data = {
                'nct_id': identification_module.get('nctId'),
                'title': identification_module.get('briefTitle'),
                'status': status_module.get('overallStatus'),
                'phase': '|'.join(design_module.get('phases', [])),
                'enrollment_count': enrollment_info.get('count', 0),
                'enrollment_type': enrollment_info.get('type'),
                'start_date': status_module.get('startDateStruct', {}).get('date'),
                'completion_date': status_module.get('primaryCompletionDateStruct', {}).get('date'),
                'last_update': status_module.get('lastUpdatePostDateStruct', {}).get('date'),
                'sponsor': protocol_section.get('sponsorCollaboratorsModule', {}).get('leadSponsor', {}).get('name'),
                'sponsor_class': protocol_section.get('sponsorCollaboratorsModule', {}).get('leadSponsor', {}).get('class')
            }
            
            # Extract conditions
            conditions_module = protocol_section.get('conditionsModule', {})
            data['conditions'] = '|'.join(conditions_module.get('conditions', []))
            
            # Extract interventions
            interventions_module = protocol_section.get('armsInterventionsModule', {})
            interventions = interventions_module.get('interventions', [])
            data['interventions'] = '|'.join([
                f"{i.get('type', '')}:{i.get('name', '')}" for i in interventions
            ])
            
            # Extract locations
            contacts_locations_module = protocol_section.get('contactsLocationsModule', {})
            locations = contacts_locations_module.get('locations', [])
            data['location_count'] = len(locations)
            data['countries'] = '|'.join(list(set([
                loc.get('country', '') for loc in locations if loc.get('country')
            ])))
            
            enrollment_data.append(data)
        
        return pd.DataFrame(enrollment_data)
    
    def get_competitive_landscape(self, condition: str) -> Dict:
        """
        Get competitive landscape analysis for a specific condition
        
        Args:
            condition: Medical condition to analyze
            
        Returns:
            Competitive landscape analysis
        """
        studies = self.search_all_pages(condition=condition, page_size=1000)
        df = self.get_enrollment_data(studies)
        
        # Analyze sponsors
        sponsor_counts = df['sponsor'].value_counts()
        sponsor_class_counts = df['sponsor_class'].value_counts()
        
        # Analyze phases
        phase_counts = df['phase'].value_counts()
        
        # Analyze status
        status_counts = df['status'].value_counts()
        
        return {
            'total_studies': int(len(df)),
            'top_sponsors': {k: int(v) for k, v in sponsor_counts.head(10).to_dict().items()},
            'sponsor_types': {k: int(v) for k, v in sponsor_class_counts.to_dict().items()},
            'phase_distribution': {k: int(v) for k, v in phase_counts.to_dict().items()},
            'status_distribution': {k: int(v) for k, v in status_counts.to_dict().items()},
            'total_planned_enrollment': int(df['enrollment_count'].sum()),
            'avg_enrollment': float(df['enrollment_count'].mean()),
            'recruiting_studies': int(len(df[df['status'] == 'RECRUITING'])),
            'unique_sponsors': int(len(sponsor_counts))
        }