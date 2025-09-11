"""
Data processors for CTMS CSV files
"""
import pandas as pd
from datetime import datetime
from typing import Dict, List, Optional
from pathlib import Path

from .models import (
    Study, Site, Subject, StudyTeamMember, SiteTeamMember, 
    Milestone, EnrollmentMetric, EnrollmentSummary
)


class CTMSDataProcessor:
    """Process CTMS CSV data into structured models"""
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self._raw_data = {}
        self._processed_data = {}
    
    def load_csv_files(self) -> None:
        """Load all CSV files into pandas DataFrames"""
        csv_files = [
            'study.csv', 'site.csv', 'subject.csv', 'enrollment_metric.csv',
            'study_team_member.csv', 'site_team_member.csv', 'milestone.csv'
        ]
        
        for file in csv_files:
            file_path = self.data_dir / file
            if file_path.exists():
                self._raw_data[file.replace('.csv', '')] = pd.read_csv(file_path)
                print(f"Loaded {file}: {len(self._raw_data[file.replace('.csv', '')])} records")
    
    def process_studies(self) -> List[Study]:
        """Process study data"""
        if 'study' not in self._raw_data:
            return []
        
        studies = []
        for _, row in self._raw_data['study'].iterrows():
            study = Study(
                study_number=row['study_number'],
                study_name=row['study_name'],
                phase=row['phase'],
                indication=row['indication'],
                target_enrollment=row['total_planned_subjects'],
                enrollment_start_date=pd.to_datetime(row['enrollment_start_date']),
                enrollment_end_date=pd.to_datetime(row['enrollment_end_date']),
                status=row['status']
            )
            studies.append(study)
        
        self._processed_data['studies'] = studies
        return studies
    
    def process_sites(self) -> List[Site]:
        """Process site data"""
        if 'site' not in self._raw_data:
            return []
        
        sites = []
        for _, row in self._raw_data['site'].iterrows():
            # Extract study number from site data
            study_number = "ONCO-2025-117"  # From the data pattern
            
            site = Site(
                site_number=str(row['site_number']),
                site_name=row['site_name'],
                study_number=study_number,
                target_enrollment=row['enrollment_target'],
                site_activated_date=pd.to_datetime(row['site_activated_date']),
                status=row['status'],
                region=self._get_region_from_state(row['state_province']),
                country=row['country']
            )
            sites.append(site)
        
        self._processed_data['sites'] = sites
        return sites
    
    def process_subjects(self) -> List[Subject]:
        """Process subject enrollment data"""
        if 'subject' not in self._raw_data:
            return []
        
        subjects = []
        for _, row in self._raw_data['subject'].iterrows():
            # Extract site number from subject_id (e.g., "001-001" -> site "1")
            site_number = row['subject_id'].split('-')[0].lstrip('0') or '1'
            
            subject = Subject(
                subject_id=row['subject_id'],
                site_number=site_number,
                study_number="ONCO-2025-117",
                screen_date=pd.to_datetime(row['screen_date']),
                enrollment_date=pd.to_datetime(row['enrollment_date']) if pd.notna(row['enrollment_date']) else None,
                randomization_date=pd.to_datetime(row['randomization_date']) if pd.notna(row['randomization_date']) else None,
                status=row['status'],
                screen_failure_reason=row['screen_failure_reason'] if pd.notna(row['screen_failure_reason']) else None
            )
            subjects.append(subject)
        
        self._processed_data['subjects'] = subjects
        return subjects
    
    def process_enrollment_metrics(self) -> List[EnrollmentMetric]:
        """Process monthly enrollment metrics"""
        if 'enrollment_metric' not in self._raw_data:
            return []
        
        metrics = []
        for _, row in self._raw_data['enrollment_metric'].iterrows():
            # Extract month from metric_date
            metric_date = pd.to_datetime(row['metric_date'])
            month = metric_date.strftime('%Y-%m')
            
            # Map site ID to site number (simplified mapping)
            site_mapping = {
                'a0C5f000000JtS9EAK': '1',
                'a0C5f000000JtSAEA0': '2', 
                'a0C5f000000JtSBEA0': '3',
                'a0C5f000000JtSCEA0': '4',
                'a0C5f000000JtSDEA0': '5'
            }
            site_number = site_mapping.get(row['site'], '1')
            
            metric = EnrollmentMetric(
                site_number=site_number,
                study_number="ONCO-2025-117",
                month=month,
                enrolled_count=row['enrolled_count'],
                screened_count=row['screened_count'],
                screen_failed_count=row['screen_failure_count'],
                randomized_count=row['randomized_count']
            )
            metrics.append(metric)
        
        self._processed_data['enrollment_metrics'] = metrics
        return metrics
    
    def calculate_enrollment_summaries(self) -> List[EnrollmentSummary]:
        """Calculate enrollment summaries for each site"""
        sites = self._processed_data.get('sites', [])
        subjects = self._processed_data.get('subjects', [])
        
        if not sites or not subjects:
            return []
        
        summaries = []
        
        for site in sites:
            # Get subjects for this site
            site_subjects = [s for s in subjects if s.site_number == site.site_number]
            
            # Calculate metrics
            enrolled_subjects = [s for s in site_subjects if s.status in ['Randomized', 'Active']]
            screen_failed = [s for s in site_subjects if s.status == 'Screen Failed']
            
            current_enrollment = len(enrolled_subjects)
            total_screened = len(site_subjects)
            screen_failure_rate = len(screen_failed) / total_screened if total_screened > 0 else 0
            
            # Calculate days since activation
            days_since_activation = (datetime.now() - site.site_activated_date).days
            
            # Calculate average monthly enrollment
            months_active = max(1, days_since_activation / 30)
            avg_monthly_enrollment = current_enrollment / months_active
            
            # Determine risk level
            enrollment_percentage = (current_enrollment / site.target_enrollment) * 100
            risk_level = self._calculate_risk_level(enrollment_percentage, avg_monthly_enrollment)
            
            summary = EnrollmentSummary(
                site_number=site.site_number,
                site_name=site.site_name,
                target_enrollment=site.target_enrollment,
                current_enrollment=current_enrollment,
                enrollment_percentage=enrollment_percentage,
                screen_failure_rate=screen_failure_rate * 100,
                avg_monthly_enrollment=avg_monthly_enrollment,
                days_since_activation=days_since_activation,
                risk_level=risk_level
            )
            summaries.append(summary)
        
        self._processed_data['enrollment_summaries'] = summaries
        return summaries
    
    def _get_region_from_state(self, state: str) -> str:
        """Map state to region"""
        east_coast = ['NY', 'MA', 'FL', 'NC', 'VA']
        west_coast = ['CA', 'WA', 'OR']
        
        if state in east_coast:
            return 'East Coast'
        elif state in west_coast:
            return 'West Coast'
        else:
            return 'Midwest/South'
    
    def _calculate_risk_level(self, enrollment_percentage: float, avg_monthly_enrollment: float) -> str:
        """Calculate risk level based on enrollment metrics"""
        if enrollment_percentage < 50 or avg_monthly_enrollment < 2:
            return 'High'
        elif enrollment_percentage < 75 or avg_monthly_enrollment < 4:
            return 'Medium'
        else:
            return 'Low'
    
    def get_processed_data(self) -> Dict:
        """Get all processed data"""
        return self._processed_data
    
    def process_all(self) -> Dict:
        """Process all data and return summaries"""
        self.load_csv_files()
        self.process_studies()
        self.process_sites()
        self.process_subjects()
        self.process_enrollment_metrics()
        self.calculate_enrollment_summaries()
        
        return self.get_processed_data()