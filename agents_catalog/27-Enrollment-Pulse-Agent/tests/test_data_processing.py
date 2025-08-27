#!/usr/bin/env python3
"""
Test script to validate CTMS data processing
"""
import sys
from pathlib import Path

# Set up backend environment
from test_helper import setup_backend_environment
setup_backend_environment()

from src.data.processors import CTMSDataProcessor
from src.analysis.enrollment_metrics import EnrollmentAnalyzer


def main():
    print("🔬 Testing CTMS Data Processing...")
    print("=" * 50)
    
    # Initialize processor
    processor = CTMSDataProcessor()
    
    # Process all data
    processed_data = processor.process_all()
    
    print(f"\n📊 Data Processing Results:")
    print(f"Studies: {len(processed_data.get('studies', []))}")
    print(f"Sites: {len(processed_data.get('sites', []))}")
    print(f"Subjects: {len(processed_data.get('subjects', []))}")
    print(f"Enrollment Metrics: {len(processed_data.get('enrollment_metrics', []))}")
    print(f"Site Summaries: {len(processed_data.get('enrollment_summaries', []))}")
    
    # Test analytics
    if processed_data.get('enrollment_summaries'):
        print(f"\n📈 Running Analytics...")
        
        analyzer = EnrollmentAnalyzer(
            summaries=processed_data['enrollment_summaries'],
            subjects=processed_data['subjects'],
            sites=processed_data['sites'],
            metrics=processed_data.get('enrollment_metrics', [])
        )
        
        # Overall status
        overall = analyzer.get_overall_enrollment_status()
        print(f"\n🎯 Overall Enrollment Status:")
        print(f"  Total Enrolled: {overall['total_enrolled']}/{overall['total_target']} ({overall['overall_percentage']}%)")
        print(f"  Screen Failure Rate: {overall['screen_failure_rate']}%")
        
        # Site performance
        site_rankings = analyzer.get_site_performance_ranking()
        print(f"\n🏆 Site Performance Rankings:")
        for i, site in enumerate(site_rankings, 1):
            print(f"  {i}. {site['site_name']}: {site['enrollment_percentage']}% ({site['current_enrollment']}/{site['target_enrollment']})")
        
        # Underperforming sites
        underperforming = analyzer.identify_underperforming_sites()
        print(f"\n⚠️  Underperforming Sites:")
        for site in underperforming:
            print(f"  {site['site_name']}: {site['current_percentage']}% - Projected shortfall: {site['shortfall']} subjects")
        
        # CRA analysis
        cra_analysis = analyzer.analyze_cra_performance()
        print(f"\n👥 CRA Performance Analysis:")
        print(f"  Thomas Nguyen sites avg: {cra_analysis['thomas_nguyen_sites']['avg_enrollment_rate']}%")
        print(f"  Amanda Garcia sites avg: {cra_analysis['amanda_garcia_sites']['avg_enrollment_rate']}%")
        print(f"  Performance gap: {cra_analysis['performance_gap']}%")
        
        print(f"\n✅ Data processing and analytics test completed successfully!")
    else:
        print("❌ No enrollment summaries generated")


if __name__ == "__main__":
    main()