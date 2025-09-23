#!/usr/bin/env python3
import re
import csv
from collections import defaultdict

def analyze_clinvar_annotations():
    """Analyze ClinVar fields from annotation.csv"""
    clinvar_fields = defaultdict(set)
    
    with open('annotation.csv', 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            attributes = row.get('attributes', '')
            if attributes and attributes != '':
                # Remove outer braces and parse key=value pairs
                attr_clean = attributes.strip('{}')
                # Find all key=value pairs
                pairs = re.findall(r'(\w+)=([^,}]+)', attr_clean)
                for key, value in pairs:
                    clinvar_fields[key].add(value.strip())
    
    return clinvar_fields

def analyze_vep_annotations():
    """Analyze VEP fields from variant.csv"""
    vep_fields = defaultdict(set)
    
    with open('variant.csv', 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            annotations = row.get('annotations', '')
            if 'vep=' in annotations:
                # Extract consequence values
                consequences = re.findall(r'consequence=\[([^\]]+)\]', annotations)
                for cons_list in consequences:
                    for cons in cons_list.split(', '):
                        vep_fields['consequence'].add(cons.strip())
                
                # Extract impact values
                impacts = re.findall(r'impact=(\w+)', annotations)
                for impact in impacts:
                    vep_fields['impact'].add(impact)
                
                # Extract biotype values
                biotypes = re.findall(r'biotype=([^,}]+)', annotations)
                for biotype in biotypes:
                    vep_fields['biotype'].add(biotype.strip())
    
    return vep_fields

# Run analysis
print("Analyzing ClinVar annotations...")
clinvar_data = analyze_clinvar_annotations()

print("Analyzing VEP annotations...")
vep_data = analyze_vep_annotations()

print("\n=== CLINVAR ANNOTATION FIELDS ===")
for field, values in sorted(clinvar_data.items()):
    print(f"\n{field}:")
    for value in sorted(list(values))[:15]:  # Show first 15 values
        print(f"  - {value}")

print("\n=== VEP ANNOTATION FIELDS ===")
for field, values in sorted(vep_data.items()):
    print(f"\n{field}:")
    for value in sorted(list(values)):
        print(f"  - {value}")
