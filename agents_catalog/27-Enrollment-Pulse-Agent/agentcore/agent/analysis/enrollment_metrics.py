"""
Enrollment metrics and calculations
"""
from datetime import datetime, timedelta
from typing import List, Dict, Tuple
import pandas as pd
import sys
from pathlib import Path

# Add src to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from data.models import EnrollmentSummary, Subject, Site, EnrollmentMetric


class EnrollmentAnalyzer:
    """Analyze enrollment performance and trends"""
    
    def __init__(self, summaries: List[EnrollmentSummary], subjects: List[Subject], 
                 sites: List[Site], metrics: List[EnrollmentMetric]):
        self.summaries = summaries
        self.subjects = subjects
        self.sites = sites
        self.metrics = metrics
    
    def get_overall_enrollment_status(self) -> Dict:
        """Calculate overall study enrollment status"""
        total_target = sum(s.target_enrollment for s in self.summaries)
        total_enrolled = sum(s.current_enrollment for s in self.summaries)
        overall_percentage = (total_enrolled / total_target) * 100 if total_target > 0 else 0
        
        # Count subjects by status
        randomized = len([s for s in self.subjects if s.status == 'Randomized'])
        screen_failed = len([s for s in self.subjects if s.status == 'Screen Failed'])
        total_screened = len(self.subjects)
        screen_failure_rate = (screen_failed / total_screened) * 100 if total_screened > 0 else 0
        
        return {
            'total_target': total_target,
            'total_enrolled': total_enrolled,
            'overall_percentage': round(overall_percentage, 1),
            'randomized_subjects': randomized,
            'screen_failed_subjects': screen_failed,
            'total_screened': total_screened,
            'screen_failure_rate': round(screen_failure_rate, 1)
        }
    
    def get_site_performance_ranking(self) -> List[Dict]:
        """Rank sites by enrollment performance"""
        ranked_sites = []
        
        for summary in sorted(self.summaries, key=lambda x: x.enrollment_percentage, reverse=True):
            ranked_sites.append({
                'site_number': summary.site_number,
                'site_name': summary.site_name,
                'enrollment_percentage': round(summary.enrollment_percentage, 1),
                'current_enrollment': summary.current_enrollment,
                'target_enrollment': summary.target_enrollment,
                'risk_level': summary.risk_level,
                'avg_monthly_enrollment': round(summary.avg_monthly_enrollment, 1)
            })
        
        return ranked_sites
    
    def identify_underperforming_sites(self, threshold: float = 60.0) -> List[Dict]:
        """Identify sites below enrollment threshold"""
        underperforming = []
        
        for summary in self.summaries:
            if summary.enrollment_percentage < threshold:
                # Calculate projected enrollment at current rate
                days_remaining = (datetime(2025, 9, 30) - datetime.now()).days
                months_remaining = max(1, days_remaining / 30)
                projected_enrollment = summary.current_enrollment + (summary.avg_monthly_enrollment * months_remaining)
                
                underperforming.append({
                    'site_number': summary.site_number,
                    'site_name': summary.site_name,
                    'current_percentage': round(summary.enrollment_percentage, 1),
                    'current_enrollment': summary.current_enrollment,
                    'target_enrollment': summary.target_enrollment,
                    'projected_final_enrollment': int(projected_enrollment),
                    'shortfall': summary.target_enrollment - int(projected_enrollment),
                    'risk_level': summary.risk_level,
                    'days_remaining': days_remaining
                })
        
        return sorted(underperforming, key=lambda x: x['shortfall'], reverse=True)
    
    def analyze_cra_performance(self) -> Dict:
        """Analyze CRA performance correlation with site enrollment"""
        # This would require site team member data to be fully implemented
        # For now, return placeholder based on requirements document
        return {
            'thomas_nguyen_sites': {
                'sites': ['1', '2'],  # Memorial Sloan, Dana-Farber
                'avg_enrollment_rate': 92.7,
                'total_sites': 2
            },
            'amanda_garcia_sites': {
                'sites': ['3', '4', '5'],  # MD Anderson, UCLA, Mayo
                'avg_enrollment_rate': 56.0,
                'total_sites': 3
            },
            'performance_gap': 36.7,
            'recommendation': 'Consider redistributing CRA workload or providing additional support to Amanda Garcia\'s sites'
        }
    
    def get_monthly_enrollment_trends(self) -> Dict:
        """Analyze monthly enrollment patterns by region"""
        trends = {}
        
        # Group sites by region
        site_regions = {}
        for site in self.sites:
            region = getattr(site, 'region', 'Unknown')
            if region not in site_regions:
                site_regions[region] = []
            site_regions[region].append(site.site_number)
        
        # Calculate monthly averages by region
        for region, site_numbers in site_regions.items():
            region_summaries = [s for s in self.summaries if s.site_number in site_numbers]
            avg_monthly = sum(s.avg_monthly_enrollment for s in region_summaries) / len(region_summaries) if region_summaries else 0
            
            trends[region] = {
                'avg_monthly_enrollment': round(avg_monthly, 1),
                'sites': len(site_numbers),
                'total_enrolled': sum(s.current_enrollment for s in region_summaries)
            }
        
        return trends
    
    def calculate_screening_efficiency(self) -> List[Dict]:
        """Calculate screening to randomization efficiency by site"""
        efficiency_data = []
        
        for summary in self.summaries:
            site_subjects = [s for s in self.subjects if s.site_number == summary.site_number]
            
            # Calculate average screening to randomization time
            randomized_subjects = [s for s in site_subjects if s.randomization_date and s.screen_date]
            
            if randomized_subjects:
                avg_screening_time = sum(
                    (s.randomization_date - s.screen_date).days 
                    for s in randomized_subjects
                ) / len(randomized_subjects)
            else:
                avg_screening_time = 0
            
            efficiency_data.append({
                'site_number': summary.site_number,
                'site_name': summary.site_name,
                'avg_screening_days': round(avg_screening_time, 1),
                'enrollment_percentage': summary.enrollment_percentage,
                'screen_failure_rate': summary.screen_failure_rate
            })
        
        return sorted(efficiency_data, key=lambda x: x['avg_screening_days'])
    
    def project_enrollment_timeline(self) -> Dict:
        """Project final enrollment based on current trends"""
        projections = {}
        
        for summary in self.summaries:
            days_remaining = (datetime(2025, 9, 30) - datetime.now()).days
            months_remaining = max(1, days_remaining / 30)
            
            projected_final = summary.current_enrollment + (summary.avg_monthly_enrollment * months_remaining)
            projected_percentage = (projected_final / summary.target_enrollment) * 100
            
            projections[summary.site_number] = {
                'site_name': summary.site_name,
                'current_enrollment': summary.current_enrollment,
                'projected_final': int(projected_final),
                'projected_percentage': round(projected_percentage, 1),
                'will_meet_target': projected_final >= summary.target_enrollment,
                'shortfall': max(0, summary.target_enrollment - int(projected_final))
            }
        
        return projections
    
    def get_historical_performance(self) -> List[Dict]:
        """Get historical performance trends for all sites"""
        historical_data = []
        
        # Process monthly enrollment metrics to create historical trends
        for site_summary in self.summaries:
            site_metrics = [m for m in self.metrics if m.site_number == site_summary.site_number]
            
            cumulative_enrollment = 0
            previous_month_enrollment = 0
            
            for i, metric in enumerate(sorted(site_metrics, key=lambda x: x.month)):
                cumulative_enrollment += metric.enrolled_count
                
                # Calculate enrollment rate (subjects per month)
                enrollment_rate = metric.enrolled_count
                
                # Calculate screen failure rate for this month
                total_screened = metric.screened_count + metric.enrolled_count
                screen_failure_rate = (metric.screen_failed_count / total_screened * 100) if total_screened > 0 else 0
                
                # Determine performance trend
                if i == 0:
                    trend = "Baseline"
                elif enrollment_rate > previous_month_enrollment * 1.1:
                    trend = "Improving"
                elif enrollment_rate < previous_month_enrollment * 0.9:
                    trend = "Declining"
                else:
                    trend = "Stable"
                
                historical_data.append({
                    'site_number': site_summary.site_number,
                    'site_name': site_summary.site_name,
                    'month': metric.month,
                    'enrollment_count': metric.enrolled_count,
                    'cumulative_enrollment': cumulative_enrollment,
                    'enrollment_rate': enrollment_rate,
                    'screen_failure_rate': round(screen_failure_rate, 1),
                    'performance_trend': trend
                })
                
                previous_month_enrollment = enrollment_rate
        
        return historical_data
    
    def get_alternative_site_recommendations(self, underperforming_site_number: str) -> List[Dict]:
        """Get alternative site recommendations for underperforming sites"""
        underperforming_site = next(
            (s for s in self.summaries if s.site_number == underperforming_site_number), 
            None
        )
        
        if not underperforming_site:
            return []
        
        recommendations = []
        
        # Find high-performing sites that could potentially take on additional subjects
        high_performing_sites = [
            s for s in self.summaries 
            if s.enrollment_percentage > 85 and s.site_number != underperforming_site_number
        ]
        
        for site in high_performing_sites:
            # Calculate historical performance score
            site_historical = [h for h in self.get_historical_performance() if h['site_number'] == site.site_number]
            
            # Calculate average monthly performance over time
            if site_historical:
                avg_monthly_rate = sum(h['enrollment_rate'] for h in site_historical) / len(site_historical)
                consistency_score = len([h for h in site_historical if h['performance_trend'] in ['Improving', 'Stable']]) / len(site_historical)
                historical_score = (avg_monthly_rate * 0.7) + (consistency_score * 30)
            else:
                historical_score = site.avg_monthly_enrollment * 10
            
            # Determine geographic proximity (simplified)
            proximity = self._get_geographic_proximity(underperforming_site.site_name, site.site_name)
            
            # Estimate capacity availability
            capacity_utilization = site.current_enrollment / site.target_enrollment
            if capacity_utilization < 0.8:
                capacity = "High Availability"
                success_prob = 0.9
            elif capacity_utilization < 0.95:
                capacity = "Moderate Availability"
                success_prob = 0.7
            else:
                capacity = "Limited Availability"
                success_prob = 0.4
            
            # Generate recommendation reason
            reason = f"High-performing site ({site.enrollment_percentage:.1f}% enrolled) with {capacity.lower()} and proven track record of {site.avg_monthly_enrollment:.1f} subjects/month"
            
            recommendations.append({
                'recommended_site_number': site.site_number,
                'recommended_site_name': site.site_name,
                'reason': reason,
                'historical_performance_score': round(historical_score, 1),
                'geographic_proximity': proximity,
                'capacity_availability': capacity,
                'success_probability': round(success_prob, 2)
            })
        
        # Sort by success probability and historical performance
        recommendations.sort(key=lambda x: (x['success_probability'], x['historical_performance_score']), reverse=True)
        
        return recommendations[:3]  # Return top 3 recommendations
    
    def _get_geographic_proximity(self, site1_name: str, site2_name: str) -> str:
        """Determine geographic proximity between sites (simplified)"""
        # Extract city/region from site names
        east_coast_sites = ['Memorial Sloan', 'Dana-Farber']
        west_coast_sites = ['UCLA', 'Mayo Clinic']
        central_sites = ['MD Anderson']
        
        site1_region = None
        site2_region = None
        
        for site in east_coast_sites:
            if site in site1_name:
                site1_region = 'East'
            if site in site2_name:
                site2_region = 'East'
        
        for site in west_coast_sites:
            if site in site1_name:
                site1_region = 'West'
            if site in site2_name:
                site2_region = 'West'
        
        for site in central_sites:
            if site in site1_name:
                site1_region = 'Central'
            if site in site2_name:
                site2_region = 'Central'
        
        if site1_region == site2_region:
            return "Same Region"
        elif site1_region and site2_region:
            return "Different Region"
        else:
            return "Unknown"