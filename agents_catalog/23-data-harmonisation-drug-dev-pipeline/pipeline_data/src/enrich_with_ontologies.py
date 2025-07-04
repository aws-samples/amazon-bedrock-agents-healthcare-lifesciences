#!/usr/bin/env python3
"""
Ontological Enrichment Script for Pharmaceutical Pipeline Data

This script enriches the harmonized pharmaceutical pipeline data with 
ontological annotations from standard biomedical vocabularies.

Author: Data Science Team
Date: 2025-07-03
"""

import json
from pathlib import Path
from datetime import datetime
from ontology_mappings import (
    get_therapeutic_area_ontology,
    get_indication_ontology, 
    get_compound_type_ontology,
    get_development_phase_ontology,
    get_mechanism_ontology,
    get_regulatory_ontology
)

class PipelineOntologyEnricher:
    """Class to enrich pipeline data with ontological annotations"""
    
    def __init__(self, input_file, output_file):
        self.input_file = Path(input_file)
        self.output_file = Path(output_file)
        self.input_data = None
        self.enriched_data = None
        
    def load_harmonized_data(self):
        """Load the harmonized pipeline data"""
        try:
            with open(self.input_file, 'r') as f:
                self.input_data = json.load(f)
            print(f"✓ Loaded harmonized data from {self.input_file}")
            return True
        except FileNotFoundError:
            print(f"✗ Could not find {self.input_file}")
            return False
        except json.JSONDecodeError as e:
            print(f"✗ Invalid JSON format: {e}")
            return False
    
    def create_enriched_structure(self):
        """Create the enriched data structure with ontological metadata"""
        self.enriched_data = {
            "metadata": {
                "enrichment_date": datetime.now().isoformat(),
                "version": "1.0",
                "description": "Ontologically enriched pharmaceutical pipeline data with semantic annotations",
                "base_data_source": str(self.input_file),
                "ontologies_used": [
                    {
                        "name": "MONDO",
                        "full_name": "Monarch Disease Ontology",
                        "url": "https://mondo.monarchinitiative.org/",
                        "description": "Comprehensive disease ontology"
                    },
                    {
                        "name": "ChEBI", 
                        "full_name": "Chemical Entities of Biological Interest",
                        "url": "https://www.ebi.ac.uk/chebi/",
                        "description": "Chemical ontology for biological entities"
                    },
                    {
                        "name": "EFO",
                        "full_name": "Experimental Factor Ontology", 
                        "url": "https://www.ebi.ac.uk/efo/",
                        "description": "Ontology for experimental variables"
                    },
                    {
                        "name": "NCIT",
                        "full_name": "NCI Thesaurus",
                        "url": "https://ncithesaurus.nci.nih.gov/",
                        "description": "Cancer and biomedical terminology"
                    },
                    {
                        "name": "MeSH",
                        "full_name": "Medical Subject Headings",
                        "url": "https://www.nlm.nih.gov/mesh/",
                        "description": "Medical vocabulary thesaurus"
                    },
                    {
                        "name": "ATC",
                        "full_name": "Anatomical Therapeutic Chemical Classification",
                        "url": "https://www.whocc.no/atc/",
                        "description": "Drug classification system"
                    },
                    {
                        "name": "ICD-10",
                        "full_name": "International Classification of Diseases",
                        "url": "https://icd.who.int/",
                        "description": "Disease classification standard"
                    },
                    {
                        "name": "SNOMED CT",
                        "full_name": "Systematized Nomenclature of Medicine Clinical Terms",
                        "url": "https://www.snomed.org/",
                        "description": "Clinical terminology system"
                    }
                ],
                "total_candidates": len(self.input_data.get("unified_pipeline", [])),
                "enrichment_statistics": {}
            },
            "ontological_vocabularies": {
                "therapeutic_areas": {},
                "indications": {},
                "compound_types": {},
                "development_phases": {},
                "mechanisms": {},
                "regulatory_designations": {}
            },
            "enriched_pipeline": [],
            "original_metadata": self.input_data.get("metadata", {}),
            "companies": self.input_data.get("companies", []),
            "summary_statistics": self.input_data.get("summary_statistics", {})
        }
    
    def enrich_candidate(self, candidate):
        """Enrich a single candidate with ontological annotations"""
        enriched_candidate = candidate.copy()
        
        # Add ontological annotations section
        enriched_candidate["ontological_annotations"] = {
            "therapeutic_area": {},
            "indication": {},
            "compound_type": {},
            "development_phase": {},
            "mechanism_of_action": {},
            "regulatory_designations": []
        }
        
        # Enrich therapeutic area
        if candidate.get("therapeutic_area"):
            area_ontology = get_therapeutic_area_ontology(candidate["therapeutic_area"])
            enriched_candidate["ontological_annotations"]["therapeutic_area"] = area_ontology
        
        # Enrich indication
        if candidate.get("indication"):
            indication_ontology = get_indication_ontology(candidate["indication"])
            enriched_candidate["ontological_annotations"]["indication"] = indication_ontology
        
        # Enrich compound type
        if candidate.get("compound_type"):
            compound_ontology = get_compound_type_ontology(candidate["compound_type"])
            enriched_candidate["ontological_annotations"]["compound_type"] = compound_ontology
        
        # Enrich development phase
        if candidate.get("development_phase"):
            phase_ontology = get_development_phase_ontology(candidate["development_phase"])
            enriched_candidate["ontological_annotations"]["development_phase"] = phase_ontology
        
        # Enrich mechanism of action
        if candidate.get("mechanism_of_action"):
            mechanism_ontology = get_mechanism_ontology(candidate["mechanism_of_action"])
            enriched_candidate["ontological_annotations"]["mechanism_of_action"] = mechanism_ontology
        
        # Enrich regulatory designations
        if candidate.get("regulatory_designations"):
            reg_ontologies = []
            for designation in candidate["regulatory_designations"]:
                reg_ontology = get_regulatory_ontology(designation)
                if reg_ontology:
                    reg_ontologies.append({
                        "designation": designation,
                        "ontology": reg_ontology
                    })
            enriched_candidate["ontological_annotations"]["regulatory_designations"] = reg_ontologies
        
        return enriched_candidate
    
    def build_vocabulary_index(self):
        """Build index of all ontological vocabularies used"""
        candidates = self.enriched_data["enriched_pipeline"]
        
        # Collect unique ontological terms
        therapeutic_areas = {}
        indications = {}
        compound_types = {}
        development_phases = {}
        mechanisms = {}
        regulatory_designations = {}
        
        for candidate in candidates:
            annotations = candidate.get("ontological_annotations", {})
            
            # Therapeutic areas
            if annotations.get("therapeutic_area"):
                area = candidate.get("therapeutic_area")
                if area and area not in therapeutic_areas:
                    therapeutic_areas[area] = annotations["therapeutic_area"]
            
            # Indications
            if annotations.get("indication"):
                indication = candidate.get("indication")
                if indication and indication not in indications:
                    indications[indication] = annotations["indication"]
            
            # Compound types
            if annotations.get("compound_type"):
                comp_type = candidate.get("compound_type")
                if comp_type and comp_type not in compound_types:
                    compound_types[comp_type] = annotations["compound_type"]
            
            # Development phases
            if annotations.get("development_phase"):
                phase = candidate.get("development_phase")
                if phase and phase not in development_phases:
                    development_phases[phase] = annotations["development_phase"]
            
            # Mechanisms
            if annotations.get("mechanism_of_action"):
                mechanism = candidate.get("mechanism_of_action")
                if mechanism and mechanism not in mechanisms:
                    mechanisms[mechanism] = annotations["mechanism_of_action"]
            
            # Regulatory designations
            for reg_item in annotations.get("regulatory_designations", []):
                designation = reg_item.get("designation")
                if designation and designation not in regulatory_designations:
                    regulatory_designations[designation] = reg_item.get("ontology", {})
        
        # Update vocabulary index
        self.enriched_data["ontological_vocabularies"] = {
            "therapeutic_areas": therapeutic_areas,
            "indications": indications,
            "compound_types": compound_types,
            "development_phases": development_phases,
            "mechanisms": mechanisms,
            "regulatory_designations": regulatory_designations
        }
    
    def calculate_enrichment_statistics(self):
        """Calculate statistics about the ontological enrichment"""
        candidates = self.enriched_data["enriched_pipeline"]
        total_candidates = len(candidates)
        
        stats = {
            "total_candidates": total_candidates,
            "enrichment_coverage": {},
            "ontology_usage": {},
            "unique_terms": {}
        }
        
        # Calculate coverage for each field
        fields = ["therapeutic_area", "indication", "compound_type", "development_phase", "mechanism_of_action"]
        
        for field in fields:
            enriched_count = sum(1 for c in candidates 
                               if c.get("ontological_annotations", {}).get(field))
            coverage = (enriched_count / total_candidates * 100) if total_candidates > 0 else 0
            stats["enrichment_coverage"][field] = {
                "enriched_count": enriched_count,
                "total_count": total_candidates,
                "coverage_percentage": round(coverage, 1)
            }
        
        # Count ontology usage
        ontology_counts = {
            "MONDO": 0, "ChEBI": 0, "EFO": 0, "NCIT": 0, 
            "MeSH": 0, "ATC": 0, "ICD-10": 0, "SNOMED_CT": 0
        }
        
        for candidate in candidates:
            annotations = candidate.get("ontological_annotations", {})
            for field_annotations in annotations.values():
                if isinstance(field_annotations, dict):
                    if "mondo_id" in field_annotations:
                        ontology_counts["MONDO"] += 1
                    if "chebi_id" in field_annotations:
                        ontology_counts["ChEBI"] += 1
                    if "efo_id" in field_annotations:
                        ontology_counts["EFO"] += 1
                    if "ncit_id" in field_annotations:
                        ontology_counts["NCIT"] += 1
                    if "mesh_id" in field_annotations:
                        ontology_counts["MeSH"] += 1
                    if "atc_class" in field_annotations:
                        ontology_counts["ATC"] += 1
                    if "icd10" in field_annotations:
                        ontology_counts["ICD-10"] += 1
                    if "snomed_ct" in field_annotations:
                        ontology_counts["SNOMED_CT"] += 1
        
        stats["ontology_usage"] = ontology_counts
        
        # Count unique terms
        vocab = self.enriched_data["ontological_vocabularies"]
        stats["unique_terms"] = {
            "therapeutic_areas": len(vocab["therapeutic_areas"]),
            "indications": len(vocab["indications"]),
            "compound_types": len(vocab["compound_types"]),
            "development_phases": len(vocab["development_phases"]),
            "mechanisms": len(vocab["mechanisms"]),
            "regulatory_designations": len(vocab["regulatory_designations"])
        }
        
        self.enriched_data["metadata"]["enrichment_statistics"] = stats
    
    def enrich_all_candidates(self):
        """Enrich all candidates with ontological annotations"""
        print("Enriching candidates with ontological annotations...")
        
        candidates = self.input_data.get("unified_pipeline", [])
        enriched_candidates = []
        
        for i, candidate in enumerate(candidates):
            enriched_candidate = self.enrich_candidate(candidate)
            enriched_candidates.append(enriched_candidate)
            
            if (i + 1) % 10 == 0:
                print(f"  Processed {i + 1}/{len(candidates)} candidates")
        
        self.enriched_data["enriched_pipeline"] = enriched_candidates
        print(f"✓ Enriched {len(enriched_candidates)} candidates")
    
    def run_enrichment(self):
        """Run the complete ontological enrichment process"""
        print("Starting ontological enrichment...")
        
        # Load data
        if not self.load_harmonized_data():
            return False
        
        # Create enriched structure
        print("Creating enriched data structure...")
        self.create_enriched_structure()
        
        # Enrich all candidates
        self.enrich_all_candidates()
        
        # Build vocabulary index
        print("Building ontological vocabulary index...")
        self.build_vocabulary_index()
        
        # Calculate statistics
        print("Calculating enrichment statistics...")
        self.calculate_enrichment_statistics()
        
        print("✓ Ontological enrichment complete!")
        return True
    
    def save_enriched_data(self):
        """Save the enriched data to JSON file"""
        with open(self.output_file, 'w') as f:
            json.dump(self.enriched_data, f, indent=2, ensure_ascii=False)
        
        file_size = self.output_file.stat().st_size / 1024
        print(f"✓ Enriched data saved to: {self.output_file}")
        print(f"  File size: {file_size:.1f} KB")
        
        return self.output_file
    
    def print_enrichment_summary(self):
        """Print summary of the enrichment process"""
        stats = self.enriched_data["metadata"]["enrichment_statistics"]
        
        print("\n" + "="*60)
        print("ONTOLOGICAL ENRICHMENT SUMMARY")
        print("="*60)
        print(f"Total Candidates: {stats['total_candidates']}")
        
        print(f"\nEnrichment Coverage:")
        for field, coverage in stats["enrichment_coverage"].items():
            print(f"  {field}: {coverage['coverage_percentage']}% ({coverage['enriched_count']}/{coverage['total_count']})")
        
        print(f"\nOntology Usage:")
        for ontology, count in stats["ontology_usage"].items():
            if count > 0:
                print(f"  {ontology}: {count} annotations")
        
        print(f"\nUnique Terms:")
        for category, count in stats["unique_terms"].items():
            print(f"  {category}: {count} unique terms")

def main():
    """Main function to run ontological enrichment"""
    # Set file paths
    input_file = Path(__file__).parent / "harmonized_pipeline_data.json"
    output_file = Path(__file__).parent / "enriched_pipeline_data.json"
    
    # Create enricher instance
    enricher = PipelineOntologyEnricher(input_file, output_file)
    
    # Run enrichment
    if enricher.run_enrichment():
        # Save enriched data
        enricher.save_enriched_data()
        
        # Print summary
        enricher.print_enrichment_summary()
        
        return 0
    else:
        print("✗ Enrichment failed")
        return 1

if __name__ == "__main__":
    exit(main())
