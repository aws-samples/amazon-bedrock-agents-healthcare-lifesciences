"""
Clinical Trials Data Processor for ClinicalTrials.gov Data Analysis
"""
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import re
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class ClinicalTrialsProcessor:
    """Process clinical trials data from ClinicalTrials.gov"""
    
    def __init__(self, data_path: str = "data/clinical_trials_gov.csv"):
        self.data_path = Path(data_path)
        self.data = None
        self.processed_data = None
        
    def load_data(self) -> pd.DataFrame:
        """Load clinical trials data from CSV"""
        try:
            self.data = pd.read_csv(self.data_path)
            logger.info(f"Loaded clinical trials data: {len(self.data)} records")
            return self.data
        except Exception as e:
            logger.warning(f"Error loading clinical trials data: {e}")
            raise
    
    def process_data(self) -> Dict:
        """Process clinical trials data for analysis"""
        if self.data is None:
            self.load_data()
        
        # Clean and process data
        self._clean_data()
        self._extract_features()
        self._categorize_trials()
        
        self.processed_data = {
            'trials': self.data.to_dict('records'),
            'summary_stats': self._calculate_summary_stats(),
            'status_analysis': self._analyze_trial_status(),
            'phase_analysis': self._analyze_phases(),
            'condition_analysis': self._analyze_conditions(),
            'intervention_analysis': self._analyze_interventions(),
            'geographic_analysis': self._analyze_geography(),
            'enrollment_analysis': self._analyze_enrollment(),
            'timeline_analysis': self._analyze_timelines(),
            'competitive_landscape': self._analyze_competitive_landscape()
        }
        
        return self.processed_data
    
    def _clean_data(self):
        """Clean and standardize the data"""
        # Convert dates
        date_columns = ['Start Date', 'Primary Completion Date', 'Completion Date', 'First Posted']
        for col in date_columns:
            if col in self.data.columns:
                self.data[col] = pd.to_datetime(self.data[col], errors='coerce')
        
        # Clean enrollment numbers
        if 'Enrollment' in self.data.columns:
            self.data['Enrollment'] = pd.to_numeric(self.data['Enrollment'], errors='coerce')
        
        # Standardize status
        if 'Study Status' in self.data.columns:
            self.data['Study Status'] = self.data['Study Status'].str.upper().str.strip()
    
    def _extract_features(self):
        """Extract additional features from the data"""
        # Extract number of locations
        if 'Locations' in self.data.columns:
            self.data['location_count'] = self.data['Locations'].apply(
                lambda x: len(str(x).split('|')) if pd.notna(x) else 0
            )
        
        # Extract countries from locations
        if 'Locations' in self.data.columns:
            self.data['countries'] = self.data['Locations'].apply(self._extract_countries)
            self.data['is_international'] = self.data['countries'].apply(
                lambda x: len(x) > 1 if isinstance(x, list) else False
            )
        
        # Extract phase information
        if 'Phases' in self.data.columns:
            self.data['phase_list'] = self.data['Phases'].apply(
                lambda x: str(x).split('|') if pd.notna(x) else []
            )
            self.data['is_early_phase'] = self.data['phase_list'].apply(
                lambda x: any(phase in ['PHASE1', 'PHASE1|PHASE2'] for phase in x)
            )
        
        # Calculate study duration
        if 'Start Date' in self.data.columns and 'Primary Completion Date' in self.data.columns:
            self.data['planned_duration_months'] = (
                (self.data['Primary Completion Date'] - self.data['Start Date']).dt.days / 30.44
            ).round(1)
        
        # Extract intervention types
        if 'Interventions' in self.data.columns:
            self.data['intervention_types'] = self.data['Interventions'].apply(self._extract_intervention_types)
            self.data['has_drug_intervention'] = self.data['intervention_types'].apply(
                lambda x: 'DRUG' in x if isinstance(x, list) else False
            )
    
    def _extract_countries(self, locations_str: str) -> List[str]:
        """Extract unique countries from locations string"""
        if pd.isna(locations_str):
            return []
        
        countries = set()
        locations = str(locations_str).split('|')
        for location in locations:
            # Extract country (usually the last part after the last comma)
            parts = location.strip().split(',')
            if parts:
                country = parts[-1].strip()
                countries.add(country)
        
        return list(countries)
    
    def _extract_intervention_types(self, interventions_str: str) -> List[str]:
        """Extract intervention types from interventions string"""
        if pd.isna(interventions_str):
            return []
        
        types = set()
        interventions = str(interventions_str).split('|')
        for intervention in interventions:
            # Extract type (usually before the colon)
            if ':' in intervention:
                intervention_type = intervention.split(':')[0].strip()
                types.add(intervention_type)
        
        return list(types)
    
    def _categorize_trials(self):
        """Categorize trials based on various criteria"""
        # Categorize by enrollment size
        if 'Enrollment' in self.data.columns:
            self.data['enrollment_category'] = pd.cut(
                self.data['Enrollment'],
                bins=[0, 50, 100, 300, float('inf')],
                labels=['Small (<50)', 'Medium (50-100)', 'Large (100-300)', 'Very Large (>300)']
            )
        
        # Categorize by study age
        if 'Start Date' in self.data.columns:
            current_date = datetime.now()
            self.data['study_age_years'] = (
                (current_date - self.data['Start Date']).dt.days / 365.25
            ).round(1)
            
            self.data['study_age_category'] = pd.cut(
                self.data['study_age_years'],
                bins=[-float('inf'), 0, 1, 3, 5, float('inf')],
                labels=['Future', 'New (<1yr)', 'Recent (1-3yr)', 'Established (3-5yr)', 'Mature (>5yr)']
            )
    
    def _calculate_summary_stats(self) -> Dict:
        """Calculate summary statistics"""
        stats = {
            'total_trials': len(self.data),
            'unique_conditions': len(self.data['Conditions'].dropna().unique()) if 'Conditions' in self.data.columns else 0,
            'total_planned_enrollment': int(self.data['Enrollment'].sum()) if 'Enrollment' in self.data.columns else 0,
            'avg_enrollment_per_trial': round(self.data['Enrollment'].mean()) if 'Enrollment' in self.data.columns else 0,
            'median_enrollment': int(self.data['Enrollment'].median()) if 'Enrollment' in self.data.columns else 0,
            'international_trials': int(self.data['is_international'].sum()) if 'is_international' in self.data.columns else 0,
            'avg_locations_per_trial': round(self.data['location_count'].mean(), 1) if 'location_count' in self.data.columns else 0
        }
        
        if 'planned_duration_months' in self.data.columns:
            stats.update({
                'avg_study_duration_months': round(self.data['planned_duration_months'].mean(), 1),
                'median_study_duration_months': round(self.data['planned_duration_months'].median(), 1)
            })
        
        return stats
    
    def _analyze_trial_status(self) -> Dict:
        """Analyze trial status distribution"""
        if 'Study Status' not in self.data.columns:
            return {}
        
        status_counts = self.data['Study Status'].value_counts()
        
        return {
            'status_distribution': status_counts.to_dict(),
            'active_trials': int(status_counts.get('RECRUITING', 0) + status_counts.get('ACTIVE, NOT RECRUITING', 0)),
            'completed_trials': int(status_counts.get('COMPLETED', 0)),
            'recruiting_trials': int(status_counts.get('RECRUITING', 0)),
            'recruitment_rate': round(status_counts.get('RECRUITING', 0) / len(self.data) * 100, 1)
        }
    
    def _analyze_phases(self) -> Dict:
        """Analyze trial phases"""
        if 'Phases' not in self.data.columns:
            return {}
        
        # Count phase occurrences
        phase_counts = {}
        for phases_str in self.data['Phases'].dropna():
            phases = str(phases_str).split('|')
            for phase in phases:
                phase = phase.strip()
                phase_counts[phase] = phase_counts.get(phase, 0) + 1
        
        early_phase_count = int(self.data['is_early_phase'].sum()) if 'is_early_phase' in self.data.columns else 0
        
        return {
            'phase_distribution': phase_counts,
            'early_phase_trials': early_phase_count,
            'early_phase_percentage': round(early_phase_count / len(self.data) * 100, 1)
        }
    
    def _analyze_conditions(self) -> Dict:
        """Analyze conditions being studied"""
        if 'Conditions' not in self.data.columns:
            return {}
        
        # Extract individual conditions
        condition_counts = {}
        for conditions_str in self.data['Conditions'].dropna():
            conditions = str(conditions_str).split('|')
            for condition in conditions:
                condition = condition.strip()
                condition_counts[condition] = condition_counts.get(condition, 0) + 1
        
        # Sort by frequency
        sorted_conditions = dict(sorted(condition_counts.items(), key=lambda x: x[1], reverse=True))
        
        return {
            'condition_distribution': sorted_conditions,
            'top_conditions': dict(list(sorted_conditions.items())[:10]),
            'unique_conditions_count': len(condition_counts)
        }
    
    def _analyze_interventions(self) -> Dict:
        """Analyze intervention types"""
        if 'Interventions' not in self.data.columns:
            return {}
        
        # Count intervention types
        intervention_counts = {}
        for types_list in self.data['intervention_types'].dropna():
            if isinstance(types_list, list):
                for intervention_type in types_list:
                    intervention_counts[intervention_type] = intervention_counts.get(intervention_type, 0) + 1
        
        drug_trials = int(self.data['has_drug_intervention'].sum()) if 'has_drug_intervention' in self.data.columns else 0
        
        return {
            'intervention_type_distribution': intervention_counts,
            'drug_intervention_trials': drug_trials,
            'drug_intervention_percentage': round(drug_trials / len(self.data) * 100, 1)
        }
    
    def _analyze_geography(self) -> Dict:
        """Analyze geographic distribution"""
        if 'countries' not in self.data.columns:
            return {}
        
        # Count countries
        country_counts = {}
        for countries_list in self.data['countries'].dropna():
            if isinstance(countries_list, list):
                for country in countries_list:
                    country_counts[country] = country_counts.get(country, 0) + 1
        
        # Sort by frequency
        sorted_countries = dict(sorted(country_counts.items(), key=lambda x: x[1], reverse=True))
        
        international_count = int(self.data['is_international'].sum()) if 'is_international' in self.data.columns else 0
        
        return {
            'country_distribution': sorted_countries,
            'top_countries': dict(list(sorted_countries.items())[:10]),
            'international_trials': international_count,
            'international_percentage': round(international_count / len(self.data) * 100, 1),
            'unique_countries': len(country_counts)
        }
    
    def _analyze_enrollment(self) -> Dict:
        """Analyze enrollment patterns"""
        if 'Enrollment' not in self.data.columns:
            return {}
        
        enrollment_data = self.data['Enrollment'].dropna()
        
        analysis = {
            'enrollment_statistics': {
                'mean': round(enrollment_data.mean(), 1),
                'median': int(enrollment_data.median()),
                'std': round(enrollment_data.std(), 1),
                'min': int(enrollment_data.min()),
                'max': int(enrollment_data.max()),
                'q25': int(enrollment_data.quantile(0.25)),
                'q75': int(enrollment_data.quantile(0.75))
            }
        }
        
        if 'enrollment_category' in self.data.columns:
            analysis['enrollment_size_distribution'] = self.data['enrollment_category'].value_counts().to_dict()
        
        return analysis
    
    def _analyze_timelines(self) -> Dict:
        """Analyze study timelines"""
        analysis = {}
        
        if 'planned_duration_months' in self.data.columns:
            duration_data = self.data['planned_duration_months'].dropna()
            analysis['duration_statistics'] = {
                'mean_months': round(duration_data.mean(), 1),
                'median_months': round(duration_data.median(), 1),
                'std_months': round(duration_data.std(), 1),
                'min_months': round(duration_data.min(), 1),
                'max_months': round(duration_data.max(), 1)
            }
        
        if 'study_age_category' in self.data.columns:
            analysis['study_age_distribution'] = self.data['study_age_category'].value_counts().to_dict()
        
        return analysis
    
    def _analyze_competitive_landscape(self) -> Dict:
        """Analyze competitive landscape"""
        if 'Sponsor' not in self.data.columns:
            return {}
        
        # Count sponsors
        sponsor_counts = self.data['Sponsor'].value_counts()
        
        # Categorize by sponsor type (simplified)
        industry_keywords = ['Inc', 'Ltd', 'Corp', 'Company', 'Pharmaceutical', 'Pharma', 'Therapeutics']
        academic_keywords = ['University', 'Hospital', 'Medical Center', 'Institute', 'Foundation']
        
        sponsor_types = {'Industry': 0, 'Academic': 0, 'Other': 0}
        
        for sponsor in self.data['Sponsor'].dropna():
            sponsor_str = str(sponsor)
            if any(keyword in sponsor_str for keyword in industry_keywords):
                sponsor_types['Industry'] += 1
            elif any(keyword in sponsor_str for keyword in academic_keywords):
                sponsor_types['Academic'] += 1
            else:
                sponsor_types['Other'] += 1
        
        return {
            'top_sponsors': sponsor_counts.head(10).to_dict(),
            'sponsor_type_distribution': sponsor_types,
            'unique_sponsors': len(sponsor_counts)
        }
    
    def search_trials(self, 
                     condition: Optional[str] = None,
                     intervention: Optional[str] = None,
                     status: Optional[str] = None,
                     phase: Optional[str] = None,
                     sponsor: Optional[str] = None) -> Dict:
        """Search trials based on criteria"""
        if self.processed_data is None:
            self.process_data()
        
        filtered_data = self.data.copy()
        
        # Apply filters
        if condition:
            filtered_data = filtered_data[
                filtered_data['Conditions'].str.contains(condition, case=False, na=False)
            ]
        
        if intervention:
            filtered_data = filtered_data[
                filtered_data['Interventions'].str.contains(intervention, case=False, na=False)
            ]
        
        if status:
            filtered_data = filtered_data[
                filtered_data['Study Status'].str.contains(status, case=False, na=False)
            ]
        
        if phase:
            filtered_data = filtered_data[
                filtered_data['Phases'].str.contains(phase, case=False, na=False)
            ]
        
        if sponsor:
            filtered_data = filtered_data[
                filtered_data['Sponsor'].str.contains(sponsor, case=False, na=False)
            ]
        
        return {
            'matching_trials': len(filtered_data),
            'trials': filtered_data[[
                'NCT Number', 'Study Title', 'Study Status', 'Phases', 
                'Enrollment', 'Sponsor', 'Conditions', 'Interventions'
            ]].to_dict('records')
        }
    
    def get_trial_details(self, nct_number: str) -> Dict:
        """Get detailed information for a specific trial"""
        if self.processed_data is None:
            self.process_data()
        
        trial_data = self.data[self.data['NCT Number'] == nct_number]
        
        if trial_data.empty:
            return {"error": f"Trial {nct_number} not found"}
        
        trial = trial_data.iloc[0]
        
        return {
            'nct_number': trial['NCT Number'],
            'title': trial['Study Title'],
            'status': trial['Study Status'],
            'brief_summary': trial.get('Brief Summary', ''),
            'conditions': trial.get('Conditions', ''),
            'interventions': trial.get('Interventions', ''),
            'phases': trial.get('Phases', ''),
            'enrollment': trial.get('Enrollment', 0),
            'sponsor': trial.get('Sponsor', ''),
            'start_date': trial.get('Start Date', ''),
            'completion_date': trial.get('Primary Completion Date', ''),
            'locations': trial.get('Locations', ''),
            'study_url': trial.get('Study URL', ''),
            'location_count': trial.get('location_count', 0),
            'countries': trial.get('countries', []),
            'is_international': trial.get('is_international', False),
            'planned_duration_months': trial.get('planned_duration_months', 0)
        }