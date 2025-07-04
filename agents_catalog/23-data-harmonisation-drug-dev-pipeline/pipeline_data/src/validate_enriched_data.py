#!/usr/bin/env python3
"""
Validation Script for Ontologically Enriched Pipeline Data

This script validates the enriched pharmaceutical pipeline data
to ensure ontological annotations are properly applied.

Author: Data Science Team
Date: 2025-07-03
"""

import json
from pathlib import Path

def validate_enriched_data(file_path):
    """Validate the enriched pipeline data"""
    
    with open(file_path, 'r') as f:
        data = json.load(f)
    
    print("="*60)
    print("ENRICHED DATA VALIDATION REPORT")
    print("="*60)
    
    # Basic structure validation
    candidates = data.get("enriched_pipeline", [])
    print(f"Total Candidates: {len(candidates)}")
    
    # Sample a few candidates to show enrichment
    print(f"\nSample Enriched Candidates:")
    print("-" * 40)
    
    for i, candidate in enumerate(candidates[:3]):
        print(f"\n{i+1}. {candidate.get('compound_name', 'Unknown')} ({candidate.get('candidate_id', 'Unknown')})")
        print(f"   Company: {candidate.get('company', 'Unknown')}")
        print(f"   Indication: {candidate.get('indication', 'Unknown')}")
        print(f"   Therapeutic Area: {candidate.get('therapeutic_area', 'Unknown')}")
        
        annotations = candidate.get("ontological_annotations", {})
        
        # Show therapeutic area ontology
        if annotations.get("therapeutic_area"):
            ta_ont = annotations["therapeutic_area"]
            print(f"   Therapeutic Area Ontology:")
            if ta_ont.get("efo_id"):
                print(f"     EFO: {ta_ont['efo_id']} - {ta_ont.get('efo_label', '')}")
            if ta_ont.get("mesh_id"):
                print(f"     MeSH: {ta_ont['mesh_id']} - {ta_ont.get('mesh_label', '')}")
        
        # Show indication ontology
        if annotations.get("indication"):
            ind_ont = annotations["indication"]
            print(f"   Indication Ontology:")
            if ind_ont.get("mondo_id"):
                print(f"     MONDO: {ind_ont['mondo_id']} - {ind_ont.get('mondo_label', '')}")
            if ind_ont.get("icd10"):
                print(f"     ICD-10: {ind_ont['icd10']}")
        
        # Show compound type ontology
        if annotations.get("compound_type"):
            ct_ont = annotations["compound_type"]
            print(f"   Compound Type Ontology:")
            if ct_ont.get("chebi_id"):
                print(f"     ChEBI: {ct_ont['chebi_id']} - {ct_ont.get('chebi_label', '')}")
            if ct_ont.get("ncit_id"):
                print(f"     NCIT: {ct_ont['ncit_id']} - {ct_ont.get('ncit_label', '')}")
    
    # Show ontological vocabulary summary
    vocab = data.get("ontological_vocabularies", {})
    print(f"\n\nOntological Vocabulary Summary:")
    print("-" * 40)
    
    for category, terms in vocab.items():
        print(f"{category.replace('_', ' ').title()}: {len(terms)} unique terms")
        if len(terms) > 0:
            # Show first few terms as examples
            sample_terms = list(terms.keys())[:3]
            for term in sample_terms:
                ontology_info = terms[term]
                ids = []
                if ontology_info.get("mondo_id"):
                    ids.append(f"MONDO:{ontology_info['mondo_id']}")
                if ontology_info.get("efo_id"):
                    ids.append(f"EFO:{ontology_info['efo_id']}")
                if ontology_info.get("chebi_id"):
                    ids.append(f"ChEBI:{ontology_info['chebi_id']}")
                if ontology_info.get("ncit_id"):
                    ids.append(f"NCIT:{ontology_info['ncit_id']}")
                if ontology_info.get("mesh_id"):
                    ids.append(f"MeSH:{ontology_info['mesh_id']}")
                
                id_str = ", ".join(ids[:2]) if ids else "No IDs"
                print(f"  • {term}: {id_str}")
    
    # Show enrichment statistics
    stats = data.get("metadata", {}).get("enrichment_statistics", {})
    if stats:
        print(f"\n\nEnrichment Statistics:")
        print("-" * 40)
        
        coverage = stats.get("enrichment_coverage", {})
        for field, cov_stats in coverage.items():
            print(f"{field.replace('_', ' ').title()}: {cov_stats.get('coverage_percentage', 0)}% coverage")
        
        print(f"\nOntology Usage:")
        usage = stats.get("ontology_usage", {})
        for ontology, count in usage.items():
            if count > 0:
                print(f"  {ontology}: {count} annotations")

def main():
    """Main validation function"""
    file_path = Path(__file__).parent / "enriched_pipeline_data.json"
    
    if file_path.exists():
        validate_enriched_data(file_path)
    else:
        print(f"Enriched data file not found: {file_path}")

if __name__ == "__main__":
    main()
