#!/usr/bin/env python3
import csv
import re

def search_drug_fields():
    drug_keywords = ['drug', 'pharm', 'medic', 'therap', 'treat', 'cpic', 'pharmgkb', 'fda', 'dosing', 'response']
    
    print("=== SEARCHING FOR DRUG-RELATED FIELDS ===\n")
    
    # Search annotation.csv
    print("ClinVar Annotations (annotation.csv):")
    found_clinvar = False
    with open('annotation.csv', 'r') as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            if i > 100:  # Limit search for performance
                break
            attributes = row.get('attributes', '').lower()
            for keyword in drug_keywords:
                if keyword in attributes:
                    print(f"  Found '{keyword}' in: {row.get('attributes', '')[:200]}...")
                    found_clinvar = True
                    break
    
    if not found_clinvar:
        print("  No drug-related fields found in ClinVar annotations")
    
    # Search variant.csv
    print("\nVEP Annotations (variant.csv):")
    found_vep = False
    with open('variant.csv', 'r') as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            if i > 100:  # Limit search for performance
                break
            annotations = row.get('annotations', '').lower()
            for keyword in drug_keywords:
                if keyword in annotations:
                    print(f"  Found '{keyword}' in: {row.get('annotations', '')[:200]}...")
                    found_vep = True
                    break
    
    if not found_vep:
        print("  No drug-related fields found in VEP annotations")
    
    # Check all unique field names
    print("\n=== ALL AVAILABLE FIELDS ===")
    
    # ClinVar fields
    clinvar_fields = set()
    with open('annotation.csv', 'r') as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            if i > 50:
                break
            attributes = row.get('attributes', '')
            if attributes:
                pairs = re.findall(r'(\w+)=', attributes)
                clinvar_fields.update(pairs)
    
    print("ClinVar fields:", sorted(list(clinvar_fields)))
    
    # Check if any field names suggest drug info
    drug_related_fields = []
    for field in clinvar_fields:
        for keyword in drug_keywords:
            if keyword.lower() in field.lower():
                drug_related_fields.append(field)
    
    if drug_related_fields:
        print(f"Potentially drug-related ClinVar fields: {drug_related_fields}")
    else:
        print("No obviously drug-related field names in ClinVar")

search_drug_fields()
