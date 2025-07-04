#!/usr/bin/env python3
"""
Pipeline Data Harmonization Script

This script creates a common data model and combines pipeline data from 
Novo Nordisk, Pfizer, and Novartis into a unified JSON structure.

Author: Data Science Team
Date: 2025-07-03
"""

import json
from pathlib import Path
from datetime import datetime
import re

class PipelineDataHarmonizer:
    """Class to harmonize pharmaceutical pipeline data across companies"""
    
    def __init__(self, data_directory):
        self.data_dir = Path(data_directory)
        self.companies = {
            'novo_nordisk': 'novo_nordisk_pipeline.json',
            'pfizer': 'pfizer_pipeline.json', 
            'novartis': 'novartis_pipeline.json'
        }
        self.raw_data = {}
        self.harmonized_data = {
            "metadata": {
                "harmonization_date": datetime.now().isoformat(),
                "version": "1.0",
                "description": "Harmonized pharmaceutical pipeline data from Novo Nordisk, Pfizer, and Novartis",
                "data_sources": [],
                "total_companies": 3,
                "total_candidates": 0
            },
            "companies": [],
            "unified_pipeline": [],
            "therapeutic_areas": [],
            "development_phases": ["Phase 1", "Phase 2", "Phase 3", "Registration/Filed"],
            "compound_types": [],
            "mechanisms_of_action": [],
            "summary_statistics": {}
        }
        
    def load_raw_data(self):
        """Load raw pipeline data from JSON files"""
        for company_key, filename in self.companies.items():
            file_path = self.data_dir / filename
            try:
                with open(file_path, 'r') as f:
                    self.raw_data[company_key] = json.load(f)
                    self.harmonized_data["metadata"]["data_sources"].append({
                        "company": company_key,
                        "source_url": self.raw_data[company_key].get("data_source", ""),
                        "extraction_date": self.raw_data[company_key].get("extraction_date", "")
                    })
                print(f"✓ Loaded {company_key} data")
            except FileNotFoundError:
                print(f"✗ Could not find {file_path}")
                
    def normalize_phase(self, phase):
        """Normalize development phase names"""
        phase_mapping = {
            "phase 1": "Phase 1",
            "phase_1": "Phase 1",
            "phase 2": "Phase 2", 
            "phase_2": "Phase 2",
            "phase 3": "Phase 3",
            "phase_3": "Phase 3",
            "filed": "Registration/Filed",
            "registration": "Registration/Filed"
        }
        return phase_mapping.get(phase.lower().replace(" ", "_"), phase)
    
    def normalize_therapeutic_area(self, area):
        """Normalize therapeutic area names"""
        area_mapping = {
            "inflammation & immunology": "Immunology",
            "internal medicine": "Cardiovascular/Metabolic",
            "cardiovascular disease": "Cardiovascular/Metabolic",
            "oncology: solid tumors": "Oncology",
            "oncology: hematology": "Oncology", 
            "emerging therapy areas": "Other/Emerging",
            "rare blood disorders": "Rare Diseases",
            "rare endocrine disorders": "Rare Diseases",
            "in-market brands and global health": "Other/Emerging",
            "neuroscience": "Neuroscience",
            "vaccines": "Vaccines"
        }
        return area_mapping.get(area.lower(), area)
    
    def extract_compound_type(self, candidate_data, company):
        """Extract and normalize compound type"""
        if company == "pfizer":
            return candidate_data.get("compound_type", "Unknown")
        elif company == "novartis":
            mechanism = candidate_data.get("mechanism", "")
            if "radioligand" in mechanism.lower():
                return "Radioligand"
            elif "monoclonal antibody" in mechanism.lower():
                return "Biologic"
            else:
                return "Unknown"
        else:  # novo_nordisk
            description = candidate_data.get("description", "").lower()
            if any(word in description for word in ["insulin", "peptide", "protein", "antibody"]):
                return "Biologic"
            elif any(word in description for word in ["small molecule", "oral"]):
                return "Small Molecule"
            elif "cell therapy" in description:
                return "Cell Therapy"
            elif "sirna" in description:
                return "RNA Therapy"
            else:
                return "Unknown"
    
    def harmonize_novo_nordisk_data(self):
        """Harmonize Novo Nordisk pipeline data"""
        data = self.raw_data['novo_nordisk']
        company_info = {
            "company_name": "Novo Nordisk",
            "company_code": "NVO",
            "data_source": data.get("data_source", ""),
            "extraction_date": data.get("extraction_date", ""),
            "pipeline_overview": data.get("pipeline_overview", {}),
            "total_candidates": 0,
            "phase_distribution": {}
        }
        
        candidates = []
        candidate_id = 1
        
        # Process candidates by phase
        pipeline_candidates = data.get("pipeline_candidates", {})
        for phase_key, phase_candidates in pipeline_candidates.items():
            normalized_phase = self.normalize_phase(phase_key)
            company_info["phase_distribution"][normalized_phase] = len(phase_candidates)
            
            for candidate in phase_candidates:
                harmonized_candidate = {
                    "candidate_id": f"NVO_{candidate_id:03d}",
                    "company": "Novo Nordisk",
                    "company_code": "NVO",
                    "compound_name": candidate.get("name", ""),
                    "compound_code": candidate.get("code", ""),
                    "brand_name": None,
                    "indication": candidate.get("indication", ""),
                    "therapeutic_area": self.normalize_therapeutic_area(candidate.get("therapy_area", "")),
                    "development_phase": normalized_phase,
                    "compound_type": self.extract_compound_type(candidate, "novo_nordisk"),
                    "mechanism_of_action": candidate.get("description", ""),
                    "submission_type": None,
                    "regulatory_designations": [],
                    "filing_date": None,
                    "lead_indication": False,
                    "status": "Current",
                    "source_data": candidate
                }
                candidates.append(harmonized_candidate)
                candidate_id += 1
        
        company_info["total_candidates"] = len(candidates)
        return company_info, candidates
    
    def harmonize_pfizer_data(self):
        """Harmonize Pfizer pipeline data"""
        data = self.raw_data['pfizer']
        company_info = {
            "company_name": "Pfizer",
            "company_code": "PFE", 
            "data_source": data.get("data_source", ""),
            "extraction_date": data.get("extraction_date", ""),
            "pipeline_overview": data.get("pipeline_overview", {}),
            "total_candidates": data.get("pipeline_statistics", {}).get("total_candidates", 0),
            "phase_distribution": {}
        }
        
        # Get phase distribution
        stats = data.get("pipeline_statistics", {})
        company_info["phase_distribution"] = {
            "Phase 1": stats.get("phase_1", 0),
            "Phase 2": stats.get("phase_2", 0), 
            "Phase 3": stats.get("phase_3", 0),
            "Registration/Filed": stats.get("registration", 0)
        }
        
        candidates = []
        candidate_id = 1
        
        # Process sample candidates (Pfizer only provides samples)
        sample_candidates = data.get("sample_pipeline_candidates", {})
        for phase_key, phase_candidates in sample_candidates.items():
            normalized_phase = self.normalize_phase(phase_key)
            
            for candidate in phase_candidates:
                # Extract regulatory designations from indication
                indication = candidate.get("indication", "")
                regulatory_designations = []
                if "FAST TRACK" in indication:
                    regulatory_designations.append("Fast Track")
                if "BREAKTHROUGH" in indication:
                    regulatory_designations.append("Breakthrough Designation")
                if "ORPHAN" in indication:
                    regulatory_designations.append("Orphan Drug")
                
                harmonized_candidate = {
                    "candidate_id": f"PFE_{candidate_id:03d}",
                    "company": "Pfizer",
                    "company_code": "PFE",
                    "compound_name": candidate.get("name", ""),
                    "compound_code": self.extract_compound_code(candidate.get("name", "")),
                    "brand_name": None,
                    "indication": indication,
                    "therapeutic_area": self.normalize_therapeutic_area(candidate.get("area_of_focus", "")),
                    "development_phase": normalized_phase,
                    "compound_type": candidate.get("compound_type", "Unknown"),
                    "mechanism_of_action": None,
                    "submission_type": candidate.get("submission_type", ""),
                    "regulatory_designations": regulatory_designations,
                    "filing_date": None,
                    "lead_indication": False,
                    "status": candidate.get("status", "Current"),
                    "source_data": candidate
                }
                candidates.append(harmonized_candidate)
                candidate_id += 1
        
        return company_info, candidates
    
    def harmonize_novartis_data(self):
        """Harmonize Novartis pipeline data"""
        data = self.raw_data['novartis']
        company_info = {
            "company_name": "Novartis",
            "company_code": "NVS",
            "data_source": data.get("data_source", ""),
            "extraction_date": data.get("extraction_date", ""),
            "pipeline_overview": data.get("pipeline_overview", {}),
            "total_candidates": 0,
            "phase_distribution": {}
        }
        
        candidates = []
        candidate_id = 1
        phase_counts = {"Phase 1": 0, "Phase 2": 0, "Phase 3": 0, "Registration/Filed": 0}
        
        # Process candidates
        pipeline_candidates = data.get("pipeline_candidates", [])
        for candidate in pipeline_candidates:
            normalized_phase = self.normalize_phase(candidate.get("phase", ""))
            phase_counts[normalized_phase] += 1
            
            harmonized_candidate = {
                "candidate_id": f"NVS_{candidate_id:03d}",
                "company": "Novartis",
                "company_code": "NVS",
                "compound_name": candidate.get("compound", ""),
                "compound_code": candidate.get("compound", ""),
                "brand_name": candidate.get("brand_name", ""),
                "indication": candidate.get("indication", ""),
                "therapeutic_area": self.normalize_therapeutic_area(candidate.get("therapeutic_area", "")),
                "development_phase": normalized_phase,
                "compound_type": self.extract_compound_type(candidate, "novartis"),
                "mechanism_of_action": candidate.get("mechanism", ""),
                "submission_type": None,
                "regulatory_designations": [],
                "filing_date": candidate.get("filing_date", ""),
                "lead_indication": candidate.get("lead_indication", False),
                "status": "Current",
                "source_data": candidate
            }
            candidates.append(harmonized_candidate)
            candidate_id += 1
        
        company_info["phase_distribution"] = phase_counts
        company_info["total_candidates"] = len(candidates)
        return company_info, candidates
    
    def extract_compound_code(self, compound_name):
        """Extract compound code from compound name"""
        # Look for patterns like PF-12345678 or NN1234
        patterns = [
            r'PF-\d+',
            r'NN\d+',
            r'AAA\d+',
            r'\([A-Z0-9-]+\)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, compound_name)
            if match:
                return match.group().strip('()')
        
        return None
    
    def collect_unique_values(self, candidates):
        """Collect unique therapeutic areas, compound types, and mechanisms"""
        therapeutic_areas = set()
        compound_types = set()
        mechanisms = set()
        
        for candidate in candidates:
            if candidate["therapeutic_area"]:
                therapeutic_areas.add(candidate["therapeutic_area"])
            if candidate["compound_type"]:
                compound_types.add(candidate["compound_type"])
            if candidate["mechanism_of_action"]:
                mechanisms.add(candidate["mechanism_of_action"])
        
        return sorted(list(therapeutic_areas)), sorted(list(compound_types)), sorted(list(mechanisms))
    
    def calculate_summary_statistics(self, all_candidates):
        """Calculate summary statistics across all companies"""
        stats = {
            "total_candidates": len(all_candidates),
            "by_company": {},
            "by_phase": {},
            "by_therapeutic_area": {},
            "by_compound_type": {}
        }
        
        # Count by company
        for candidate in all_candidates:
            company = candidate["company"]
            stats["by_company"][company] = stats["by_company"].get(company, 0) + 1
        
        # Count by phase
        for candidate in all_candidates:
            phase = candidate["development_phase"]
            stats["by_phase"][phase] = stats["by_phase"].get(phase, 0) + 1
        
        # Count by therapeutic area
        for candidate in all_candidates:
            area = candidate["therapeutic_area"]
            stats["by_therapeutic_area"][area] = stats["by_therapeutic_area"].get(area, 0) + 1
        
        # Count by compound type
        for candidate in all_candidates:
            comp_type = candidate["compound_type"]
            stats["by_compound_type"][comp_type] = stats["by_compound_type"].get(comp_type, 0) + 1
        
        return stats
    
    def harmonize_all_data(self):
        """Harmonize data from all companies"""
        print("Starting data harmonization...")
        
        # Load raw data
        self.load_raw_data()
        
        if not self.raw_data:
            print("No data loaded. Exiting.")
            return
        
        all_candidates = []
        
        # Harmonize each company's data
        print("\nHarmonizing Novo Nordisk data...")
        nvo_info, nvo_candidates = self.harmonize_novo_nordisk_data()
        self.harmonized_data["companies"].append(nvo_info)
        all_candidates.extend(nvo_candidates)
        
        print("Harmonizing Pfizer data...")
        pfe_info, pfe_candidates = self.harmonize_pfizer_data()
        self.harmonized_data["companies"].append(pfe_info)
        all_candidates.extend(pfe_candidates)
        
        print("Harmonizing Novartis data...")
        nvs_info, nvs_candidates = self.harmonize_novartis_data()
        self.harmonized_data["companies"].append(nvs_info)
        all_candidates.extend(nvs_candidates)
        
        # Add all candidates to unified pipeline
        self.harmonized_data["unified_pipeline"] = all_candidates
        
        # Collect unique values
        therapeutic_areas, compound_types, mechanisms = self.collect_unique_values(all_candidates)
        self.harmonized_data["therapeutic_areas"] = therapeutic_areas
        self.harmonized_data["compound_types"] = compound_types
        self.harmonized_data["mechanisms_of_action"] = mechanisms[:50]  # Limit to first 50
        
        # Calculate summary statistics
        self.harmonized_data["summary_statistics"] = self.calculate_summary_statistics(all_candidates)
        self.harmonized_data["metadata"]["total_candidates"] = len(all_candidates)
        
        print(f"\n✓ Harmonization complete!")
        print(f"  Total candidates: {len(all_candidates)}")
        print(f"  Novo Nordisk: {len(nvo_candidates)} candidates")
        print(f"  Pfizer: {len(pfe_candidates)} candidates") 
        print(f"  Novartis: {len(nvs_candidates)} candidates")
        
        return self.harmonized_data
    
    def save_harmonized_data(self, output_filename="harmonized_pipeline_data.json"):
        """Save harmonized data to JSON file"""
        output_path = self.data_dir / output_filename
        
        with open(output_path, 'w') as f:
            json.dump(self.harmonized_data, f, indent=2, ensure_ascii=False)
        
        print(f"\n✓ Harmonized data saved to: {output_path}")
        print(f"  File size: {output_path.stat().st_size / 1024:.1f} KB")
        
        return output_path

def main():
    """Main function to run the harmonization"""
    # Set data directory
    data_directory = Path(__file__).parent
    
    # Create harmonizer instance
    harmonizer = PipelineDataHarmonizer(data_directory)
    
    # Harmonize all data
    harmonized_data = harmonizer.harmonize_all_data()
    
    if harmonized_data:
        # Save harmonized data
        harmonizer.save_harmonized_data()
        
        # Print summary
        print("\n" + "="*60)
        print("HARMONIZATION SUMMARY")
        print("="*60)
        stats = harmonized_data["summary_statistics"]
        print(f"Total Candidates: {stats['total_candidates']}")
        print("\nBy Company:")
        for company, count in stats["by_company"].items():
            print(f"  {company}: {count}")
        print("\nBy Development Phase:")
        for phase, count in stats["by_phase"].items():
            print(f"  {phase}: {count}")
        print("\nBy Therapeutic Area:")
        for area, count in stats["by_therapeutic_area"].items():
            print(f"  {area}: {count}")

if __name__ == "__main__":
    main()
