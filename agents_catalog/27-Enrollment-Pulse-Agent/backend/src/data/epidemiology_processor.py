"""
Epidemiology Data Processor for MTNBC Patient Population Analysis
"""
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import logging

logger = logging.getLogger(__name__)

class EpidemiologyProcessor:
    """Process epidemiological data for MTNBC patient populations"""
    
    def __init__(self, data_path: str = "data/epidemiology_synthetic.csv"):
        self.data_path = Path(data_path)
        self.data = None
        self.processed_data = None
        
    def load_data(self) -> pd.DataFrame:
        """Load epidemiology data from CSV"""
        try:
            self.data = pd.read_csv(self.data_path)
            logger.info(f"Loaded epidemiology data: {len(self.data)} records")
            return self.data
        except Exception as e:
            logger.warning(f"Error loading epidemiology data: {e}")
            raise
    
    def process_data(self) -> Dict:
        """Process epidemiology data for analysis"""
        if self.data is None:
            self.load_data()
        
        # Calculate additional metrics
        self.data['total_eligible_pool'] = (
            self.data['population_female_40plus'] * 
            self.data['mtnbc_prevalence_1y_per_100k_female'] / 100000
        )
        
        # Calculate market penetration potential
        self.data['market_penetration_potential'] = (
            self.data['est_trial_eligible_count'] / 
            self.data['total_eligible_pool'] * 100
        ).round(2)
        
        # Risk stratification based on biomarker prevalence
        self.data['biomarker_risk_category'] = pd.cut(
            self.data['pd_l1_positive_pct'],
            bins=[0, 35, 40, 100],
            labels=['Low', 'Medium', 'High']
        )
        
        # Calculate recruitment feasibility score
        self.data['recruitment_feasibility_score'] = (
            (self.data['mtnbc_patient_density_index'] * 0.3) +
            (self.data['trial_eligibility_rate_pct'] / 100 * 0.4) +
            (self.data['pd_l1_positive_pct'] / 100 * 0.3)
        ).round(3)
        
        self.processed_data = {
            'metro_areas': self.data.to_dict('records'),
            'summary_stats': self._calculate_summary_stats(),
            'top_markets': self._identify_top_markets(),
            'biomarker_analysis': self._analyze_biomarkers(),
            'recruitment_potential': self._assess_recruitment_potential()
        }
        
        return self.processed_data
    
    def _calculate_summary_stats(self) -> Dict:
        """Calculate summary statistics"""
        return {
            'total_metro_areas': len(self.data),
            'total_population_female_40plus': int(self.data['population_female_40plus'].sum()),
            'total_mtnbc_incidence': int(self.data['est_mtnbc_incidence_count'].sum()),
            'total_mtnbc_prevalence': int(self.data['est_mtnbc_prevalence_1y_count'].sum()),
            'total_trial_eligible': int(self.data['est_trial_eligible_count'].sum()),
            'avg_incidence_rate': round(self.data['mtnbc_incidence_rate_per_100k_female'].mean(), 2),
            'avg_prevalence_rate': round(self.data['mtnbc_prevalence_1y_per_100k_female'].mean(), 2),
            'avg_pd_l1_positive_pct': round(self.data['pd_l1_positive_pct'].mean(), 1),
            'avg_brca_mutation_pct': round(self.data['brca_mutation_pct'].mean(), 1),
            'avg_trial_eligibility_rate': round(self.data['trial_eligibility_rate_pct'].mean(), 1)
        }
    
    def _identify_top_markets(self) -> Dict:
        """Identify top markets by various metrics"""
        return {
            'by_patient_count': self.data.nlargest(5, 'est_mtnbc_prevalence_1y_count')[
                ['metro', 'state', 'est_mtnbc_prevalence_1y_count', 'est_trial_eligible_count']
            ].to_dict('records'),
            'by_density': self.data.nlargest(5, 'mtnbc_patient_density_index')[
                ['metro', 'state', 'mtnbc_patient_density_index', 'recruitment_feasibility_score']
            ].to_dict('records'),
            'by_eligibility': self.data.nlargest(5, 'est_trial_eligible_count')[
                ['metro', 'state', 'est_trial_eligible_count', 'trial_eligibility_rate_pct']
            ].to_dict('records'),
            'by_feasibility': self.data.nlargest(5, 'recruitment_feasibility_score')[
                ['metro', 'state', 'recruitment_feasibility_score', 'est_trial_eligible_count']
            ].to_dict('records')
        }
    
    def _analyze_biomarkers(self) -> Dict:
        """Analyze biomarker distributions"""
        return {
            'pd_l1_distribution': {
                'mean': round(self.data['pd_l1_positive_pct'].mean(), 1),
                'median': round(self.data['pd_l1_positive_pct'].median(), 1),
                'std': round(self.data['pd_l1_positive_pct'].std(), 1),
                'min': round(self.data['pd_l1_positive_pct'].min(), 1),
                'max': round(self.data['pd_l1_positive_pct'].max(), 1)
            },
            'brca_distribution': {
                'mean': round(self.data['brca_mutation_pct'].mean(), 1),
                'median': round(self.data['brca_mutation_pct'].median(), 1),
                'std': round(self.data['brca_mutation_pct'].std(), 1),
                'min': round(self.data['brca_mutation_pct'].min(), 1),
                'max': round(self.data['brca_mutation_pct'].max(), 1)
            },
            'biomarker_positive_pool': int(self.data['est_biomarker_positive_pool'].sum()),
            'risk_categories': self.data['biomarker_risk_category'].value_counts().to_dict()
        }
    
    def _assess_recruitment_potential(self) -> Dict:
        """Assess recruitment potential across markets"""
        high_potential = self.data[self.data['recruitment_feasibility_score'] >= 0.8]
        medium_potential = self.data[
            (self.data['recruitment_feasibility_score'] >= 0.6) & 
            (self.data['recruitment_feasibility_score'] < 0.8)
        ]
        low_potential = self.data[self.data['recruitment_feasibility_score'] < 0.6]
        
        return {
            'high_potential_markets': {
                'count': len(high_potential),
                'markets': high_potential[['metro', 'state', 'recruitment_feasibility_score', 'est_trial_eligible_count']].to_dict('records'),
                'total_eligible': int(high_potential['est_trial_eligible_count'].sum())
            },
            'medium_potential_markets': {
                'count': len(medium_potential),
                'markets': medium_potential[['metro', 'state', 'recruitment_feasibility_score', 'est_trial_eligible_count']].to_dict('records'),
                'total_eligible': int(medium_potential['est_trial_eligible_count'].sum())
            },
            'low_potential_markets': {
                'count': len(low_potential),
                'markets': low_potential[['metro', 'state', 'recruitment_feasibility_score', 'est_trial_eligible_count']].to_dict('records'),
                'total_eligible': int(low_potential['est_trial_eligible_count'].sum())
            }
        }
    
    def get_market_analysis(self, metro_name: Optional[str] = None) -> Dict:
        """Get detailed analysis for a specific market or all markets"""
        if self.processed_data is None:
            self.process_data()
        
        if metro_name:
            market_data = self.data[self.data['metro'].str.contains(metro_name, case=False, na=False)]
            if market_data.empty:
                return {"error": f"No market found matching '{metro_name}'"}
            
            market = market_data.iloc[0]
            return {
                'market_name': market['metro'],
                'state': market['state'],
                'population_analysis': {
                    'female_40plus_population': int(market['population_female_40plus']),
                    'mtnbc_incidence_rate': market['mtnbc_incidence_rate_per_100k_female'],
                    'mtnbc_prevalence_rate': market['mtnbc_prevalence_1y_per_100k_female'],
                    'estimated_mtnbc_patients': int(market['est_mtnbc_prevalence_1y_count']),
                    'patient_density_index': market['mtnbc_patient_density_index']
                },
                'biomarker_profile': {
                    'pd_l1_positive_pct': market['pd_l1_positive_pct'],
                    'brca_mutation_pct': market['brca_mutation_pct'],
                    'biomarker_positive_pool': int(market['est_biomarker_positive_pool']),
                    'risk_category': market['biomarker_risk_category']
                },
                'trial_potential': {
                    'eligibility_rate': market['trial_eligibility_rate_pct'],
                    'estimated_eligible_count': int(market['est_trial_eligible_count']),
                    'recruitment_feasibility_score': market['recruitment_feasibility_score'],
                    'market_penetration_potential': market['market_penetration_potential']
                }
            }
        
        return self.processed_data
    
    def compare_markets(self, market_names: List[str]) -> Dict:
        """Compare multiple markets"""
        if self.processed_data is None:
            self.process_data()
        
        comparison_data = []
        for market_name in market_names:
            market_data = self.data[self.data['metro'].str.contains(market_name, case=False, na=False)]
            if not market_data.empty:
                comparison_data.append(market_data.iloc[0])
        
        if not comparison_data:
            return {"error": "No markets found matching the provided names"}
        
        comparison_df = pd.DataFrame(comparison_data)
        
        return {
            'market_comparison': comparison_df[[
                'metro', 'state', 'est_mtnbc_prevalence_1y_count', 
                'est_trial_eligible_count', 'recruitment_feasibility_score',
                'pd_l1_positive_pct', 'trial_eligibility_rate_pct'
            ]].to_dict('records'),
            'ranking_analysis': {
                'by_patient_count': comparison_df.nlargest(len(comparison_df), 'est_mtnbc_prevalence_1y_count')['metro'].tolist(),
                'by_eligible_count': comparison_df.nlargest(len(comparison_df), 'est_trial_eligible_count')['metro'].tolist(),
                'by_feasibility': comparison_df.nlargest(len(comparison_df), 'recruitment_feasibility_score')['metro'].tolist()
            }
        }