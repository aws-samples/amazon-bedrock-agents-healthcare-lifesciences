#!/usr/bin/env python3
"""
Pharmaceutical Pipeline Data Analysis Script

This script analyzes and visualizes drug development pipeline data 
for Novo Nordisk, Pfizer, and Novartis.

Author: Data Science Team
Date: 2025-07-03
"""

import json
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import numpy as np

class PipelineAnalyzer:
    """Class to analyze pharmaceutical pipeline data"""
    
    def __init__(self, data_directory):
        self.data_dir = Path(data_directory)
        self.companies = ['novo_nordisk', 'pfizer', 'novartis']
        self.pipeline_data = {}
        
    def load_data(self):
        """Load pipeline data from JSON files"""
        for company in self.companies:
            file_path = self.data_dir / f"{company}_pipeline.json"
            try:
                with open(file_path, 'r') as f:
                    self.pipeline_data[company] = json.load(f)
                print(f"✓ Loaded {company} pipeline data")
            except FileNotFoundError:
                print(f"✗ Could not find {file_path}")
                
    def analyze_phase_distribution(self):
        """Analyze distribution of candidates across development phases"""
        phase_data = {}
        
        # Extract phase data for each company
        for company, data in self.pipeline_data.items():
            if company == 'novo_nordisk':
                phases = data['pipeline_candidates']
                phase_data[company] = {
                    'Phase 1': len(phases.get('phase_1', [])),
                    'Phase 2': len(phases.get('phase_2', [])),
                    'Phase 3': len(phases.get('phase_3', [])),
                    'Filed/Registration': len(phases.get('filed', []))
                }
            elif company == 'pfizer':
                stats = data['pipeline_statistics']
                phase_data[company] = {
                    'Phase 1': stats['phase_1'],
                    'Phase 2': stats['phase_2'],
                    'Phase 3': stats['phase_3'],
                    'Filed/Registration': stats['registration']
                }
            elif company == 'novartis':
                # Count phases from candidate list
                candidates = data['pipeline_candidates']
                phase_counts = {'Phase 1': 0, 'Phase 2': 0, 'Phase 3': 0, 'Filed/Registration': 0}
                for candidate in candidates:
                    phase = candidate['phase']
                    if phase == 'Registration':
                        phase_counts['Filed/Registration'] += 1
                    else:
                        phase_counts[phase] += 1
                phase_data[company] = phase_counts
                
        return phase_data
    
    def analyze_therapeutic_areas(self):
        """Analyze therapeutic area focus for each company"""
        therapeutic_areas = {}
        
        for company, data in self.pipeline_data.items():
            if company == 'novo_nordisk':
                areas = data['pipeline_overview']['therapy_areas']
                therapeutic_areas[company] = areas
            elif company == 'pfizer':
                areas = data['pipeline_overview']['areas_of_focus']
                therapeutic_areas[company] = areas
            elif company == 'novartis':
                areas = data['pipeline_overview']['therapeutic_areas']
                therapeutic_areas[company] = areas
                
        return therapeutic_areas
    
    def create_phase_distribution_chart(self, phase_data):
        """Create visualization of phase distribution"""
        # Convert to DataFrame for easier plotting
        df = pd.DataFrame(phase_data).T
        
        # Create stacked bar chart
        fig, ax = plt.subplots(figsize=(12, 8))
        df.plot(kind='bar', stacked=True, ax=ax, 
                color=['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4'])
        
        plt.title('Drug Development Pipeline Phase Distribution by Company', 
                 fontsize=16, fontweight='bold', pad=20)
        plt.xlabel('Company', fontsize=12, fontweight='bold')
        plt.ylabel('Number of Candidates', fontsize=12, fontweight='bold')
        plt.legend(title='Development Phase', bbox_to_anchor=(1.05, 1), loc='upper left')
        plt.xticks(rotation=45)
        plt.tight_layout()
        
        # Save chart
        plt.savefig(self.data_dir / 'phase_distribution_chart.png', 
                   dpi=300, bbox_inches='tight')
        plt.show()
        
    def create_therapeutic_area_comparison(self, therapeutic_areas):
        """Create comparison of therapeutic area focus"""
        # Create a comprehensive list of all therapeutic areas
        all_areas = set()
        for areas in therapeutic_areas.values():
            all_areas.update(areas)
        
        # Create binary matrix showing which companies focus on which areas
        comparison_data = {}
        for company, areas in therapeutic_areas.items():
            comparison_data[company] = [1 if area in areas else 0 for area in sorted(all_areas)]
        
        # Create heatmap
        df = pd.DataFrame(comparison_data, index=sorted(all_areas))
        
        fig, ax = plt.subplots(figsize=(10, 12))
        sns.heatmap(df, annot=True, cmap='RdYlBu_r', cbar_kws={'label': 'Focus Area'}, 
                   ax=ax, fmt='d')
        
        plt.title('Therapeutic Area Focus Comparison', fontsize=16, fontweight='bold', pad=20)
        plt.xlabel('Company', fontsize=12, fontweight='bold')
        plt.ylabel('Therapeutic Area', fontsize=12, fontweight='bold')
        plt.tight_layout()
        
        # Save chart
        plt.savefig(self.data_dir / 'therapeutic_area_comparison.png', 
                   dpi=300, bbox_inches='tight')
        plt.show()
        
    def generate_summary_report(self):
        """Generate a comprehensive summary report"""
        report = []
        report.append("=" * 60)
        report.append("PHARMACEUTICAL PIPELINE ANALYSIS REPORT")
        report.append("=" * 60)
        report.append(f"Analysis Date: 2025-07-03")
        report.append(f"Companies Analyzed: {', '.join([c.replace('_', ' ').title() for c in self.companies])}")
        report.append("")
        
        # Phase distribution analysis
        phase_data = self.analyze_phase_distribution()
        report.append("PHASE DISTRIBUTION SUMMARY:")
        report.append("-" * 30)
        for company, phases in phase_data.items():
            total = sum(phases.values())
            report.append(f"{company.replace('_', ' ').title()}: {total} total candidates")
            for phase, count in phases.items():
                percentage = (count/total)*100 if total > 0 else 0
                report.append(f"  {phase}: {count} ({percentage:.1f}%)")
            report.append("")
        
        # Therapeutic area analysis
        therapeutic_areas = self.analyze_therapeutic_areas()
        report.append("THERAPEUTIC AREA FOCUS:")
        report.append("-" * 25)
        for company, areas in therapeutic_areas.items():
            report.append(f"{company.replace('_', ' ').title()}:")
            for area in areas:
                report.append(f"  • {area}")
            report.append("")
        
        # Key insights
        report.append("KEY INSIGHTS:")
        report.append("-" * 15)
        report.append("• Novo Nordisk: Specialized focus on diabetes, obesity, and rare diseases")
        report.append("• Pfizer: Broad portfolio across multiple therapeutic areas")
        report.append("• Novartis: Strong focus on oncology with innovative radioligand therapy")
        report.append("• All companies have substantial Phase 1 and Phase 2 portfolios")
        report.append("• Competition is intense in oncology and immunology spaces")
        
        # Save report
        with open(self.data_dir / 'pipeline_analysis_report.txt', 'w') as f:
            f.write('\n'.join(report))
        
        return '\n'.join(report)
    
    def run_full_analysis(self):
        """Run complete pipeline analysis"""
        print("Starting pharmaceutical pipeline analysis...")
        
        # Load data
        self.load_data()
        
        if not self.pipeline_data:
            print("No data loaded. Please check data files.")
            return
        
        # Analyze phase distribution
        print("\nAnalyzing phase distribution...")
        phase_data = self.analyze_phase_distribution()
        self.create_phase_distribution_chart(phase_data)
        
        # Analyze therapeutic areas
        print("Analyzing therapeutic areas...")
        therapeutic_areas = self.analyze_therapeutic_areas()
        self.create_therapeutic_area_comparison(therapeutic_areas)
        
        # Generate summary report
        print("Generating summary report...")
        report = self.generate_summary_report()
        print("\n" + report)
        
        print(f"\nAnalysis complete! Files saved to: {self.data_dir}")
        print("Generated files:")
        print("• phase_distribution_chart.png")
        print("• therapeutic_area_comparison.png") 
        print("• pipeline_analysis_report.txt")

def main():
    """Main function to run the analysis"""
    # Set data directory (current directory by default)
    data_directory = Path(__file__).parent
    
    # Create analyzer instance
    analyzer = PipelineAnalyzer(data_directory)
    
    # Run full analysis
    analyzer.run_full_analysis()

if __name__ == "__main__":
    main()
