#!/usr/bin/env python3
import pandas as pd
import re
import json
from collections import defaultdict

def extract_clinvar_fields(csv_file):
    """Extract ClinVar annotation fields from annotation.csv"""
    df = pd.read_csv(csv_file)
    clinvar_fields = defaultdict(set)
    
    for attributes in df['attributes'].dropna():
        # Parse the attributes string
        attr_str = str(attributes).strip('{}')
        pairs = re.findall(r'(\w+)=([^,}]+)', attr_str)
        
        for key, value in pairs:
            clinvar_fields[key].add(value)
    
    return clinvar_fields

def extract_vep_fields(csv_file):
    """Extract VEP annotation fields from variant.csv"""
    df = pd.read_csv(csv_file)
    vep_fields = defaultdict(set)
    
    for annotations in df['annotations'].dropna():
        if 'vep=' in str(annotations):
            # Extract VEP data
            vep_match = re.search(r'vep=\[([^\]]+)\]', str(annotations))
            if vep_match:
                vep_data = vep_match.group(1)
                # Extract consequence, impact, biotype fields
                consequences = re.findall(r'consequence=\[([^\]]+)\]', vep_data)
                impacts = re.findall(r'impact=(\w+)', vep_data)
                biotypes = re.findall(r'biotype=([^,}]+)', vep_data)
                
                for cons in consequences:
                    for c in cons.split(', '):
                        vep_fields['consequence'].add(c.strip())
                
                for imp in impacts:
                    vep_fields['impact'].add(imp)
                    
                for bio in biotypes:
                    vep_fields['biotype'].add(bio)
    
    return vep_fields

# Analyze both files
print("=== ClinVar Annotation Fields (annotation.csv) ===")
clinvar_data = extract_clinvar_fields('annotation.csv')

print("=== VEP Annotation Fields (variant.csv) ===")
vep_data = extract_vep_fields('variant.csv')

# Output results
print("\n=== CLINVAR FIELDS ===")
for field, values in sorted(clinvar_data.items()):
    print(f"{field}: {sorted(list(values))[:10]}")  # Show first 10 values

print("\n=== VEP FIELDS ===")
for field, values in sorted(vep_data.items()):
    print(f"{field}: {sorted(list(values))}")
