#!/usr/bin/env python3
"""
Ontological Mappings for Pharmaceutical Pipeline Data

This module contains mappings to standard biomedical ontologies and controlled vocabularies
for enriching pharmaceutical pipeline data with semantic annotations.

Ontologies Used:
- MONDO: Monarch Disease Ontology
- CHEBI: Chemical Entities of Biological Interest
- EFO: Experimental Factor Ontology
- NCIT: NCI Thesaurus
- ATC: Anatomical Therapeutic Chemical Classification
- MeSH: Medical Subject Headings

Author: Data Science Team
Date: 2025-07-03
"""

# Therapeutic Area Mappings to EFO (Experimental Factor Ontology)
THERAPEUTIC_AREA_MAPPINGS = {
    "Cardiovascular/Metabolic": {
        "efo_id": "EFO_0000319",
        "efo_label": "cardiovascular disease",
        "mesh_id": "D002318",
        "mesh_label": "Cardiovascular Diseases",
        "atc_class": "C",
        "atc_label": "Cardiovascular System"
    },
    "Diabetes": {
        "efo_id": "EFO_0000400", 
        "efo_label": "diabetes mellitus",
        "mesh_id": "D003920",
        "mesh_label": "Diabetes Mellitus",
        "mondo_id": "MONDO_0005015",
        "mondo_label": "diabetes mellitus"
    },
    "Immunology": {
        "efo_id": "EFO_0000540",
        "efo_label": "immune system disease",
        "mesh_id": "D007154",
        "mesh_label": "Immune System Diseases",
        "atc_class": "L",
        "atc_label": "Antineoplastic and Immunomodulating Agents"
    },
    "Neuroscience": {
        "efo_id": "EFO_0000618",
        "efo_label": "nervous system disease",
        "mesh_id": "D009422",
        "mesh_label": "Nervous System Diseases",
        "atc_class": "N",
        "atc_label": "Nervous System"
    },
    "Obesity": {
        "efo_id": "EFO_0001073",
        "efo_label": "obesity",
        "mesh_id": "D009765",
        "mesh_label": "Obesity",
        "mondo_id": "MONDO_0011122",
        "mondo_label": "obesity disorder"
    },
    "Oncology": {
        "efo_id": "EFO_0000616",
        "efo_label": "neoplasm",
        "mesh_id": "D009369",
        "mesh_label": "Neoplasms",
        "mondo_id": "MONDO_0004992",
        "mondo_label": "cancer",
        "atc_class": "L01",
        "atc_label": "Antineoplastic Agents"
    },
    "Rare Diseases": {
        "efo_id": "EFO_0000651",
        "efo_label": "rare disease",
        "mesh_id": "D035583",
        "mesh_label": "Rare Diseases",
        "mondo_id": "MONDO_0021136",
        "mondo_label": "rare genetic disease"
    },
    "Vaccines": {
        "efo_id": "EFO_0000876",
        "efo_label": "vaccine",
        "mesh_id": "D014612",
        "mesh_label": "Vaccines",
        "atc_class": "J07",
        "atc_label": "Vaccines"
    }
}

# Disease/Indication Mappings to MONDO and MeSH
INDICATION_MAPPINGS = {
    "Type 1 diabetes": {
        "mondo_id": "MONDO_0005147",
        "mondo_label": "type 1 diabetes mellitus",
        "mesh_id": "D003922",
        "mesh_label": "Diabetes Mellitus, Type 1",
        "icd10": "E10",
        "snomed_ct": "46635009"
    },
    "Type 2 diabetes": {
        "mondo_id": "MONDO_0005148", 
        "mondo_label": "type 2 diabetes mellitus",
        "mesh_id": "D003924",
        "mesh_label": "Diabetes Mellitus, Type 2",
        "icd10": "E11",
        "snomed_ct": "44054006"
    },
    "Obesity": {
        "mondo_id": "MONDO_0011122",
        "mondo_label": "obesity disorder",
        "mesh_id": "D009765",
        "mesh_label": "Obesity",
        "icd10": "E66",
        "snomed_ct": "414915002"
    },
    "Alzheimer's disease": {
        "mondo_id": "MONDO_0004975",
        "mondo_label": "Alzheimer disease",
        "mesh_id": "D000544",
        "mesh_label": "Alzheimer Disease",
        "icd10": "G30",
        "snomed_ct": "26929004"
    },
    "Parkinson's Disease": {
        "mondo_id": "MONDO_0005180",
        "mondo_label": "Parkinson disease",
        "mesh_id": "D010300",
        "mesh_label": "Parkinson Disease",
        "icd10": "G20",
        "snomed_ct": "49049000"
    },
    "Rheumatoid Arthritis": {
        "mondo_id": "MONDO_0008383",
        "mondo_label": "rheumatoid arthritis",
        "mesh_id": "D001172",
        "mesh_label": "Arthritis, Rheumatoid",
        "icd10": "M06",
        "snomed_ct": "69896004"
    },
    "Heart failure": {
        "mondo_id": "MONDO_0005252",
        "mondo_label": "heart failure",
        "mesh_id": "D006333",
        "mesh_label": "Heart Failure",
        "icd10": "I50",
        "snomed_ct": "84114007"
    },
    "Prostate cancer": {
        "mondo_id": "MONDO_0008315",
        "mondo_label": "prostate cancer",
        "mesh_id": "D011471",
        "mesh_label": "Prostatic Neoplasms",
        "icd10": "C61",
        "snomed_ct": "399068003"
    },
    "Breast cancer": {
        "mondo_id": "MONDO_0007254",
        "mondo_label": "breast cancer",
        "mesh_id": "D001943",
        "mesh_label": "Breast Neoplasms",
        "icd10": "C50",
        "snomed_ct": "254837009"
    },
    "Glioblastoma": {
        "mondo_id": "MONDO_0018177",
        "mondo_label": "glioblastoma",
        "mesh_id": "D005909",
        "mesh_label": "Glioblastoma",
        "icd10": "C71",
        "snomed_ct": "393563007"
    },
    "Sickle Cell Disease": {
        "mondo_id": "MONDO_0011382",
        "mondo_label": "sickle cell disease",
        "mesh_id": "D000755",
        "mesh_label": "Anemia, Sickle Cell",
        "icd10": "D57",
        "snomed_ct": "417357006"
    },
    "Thalassemia": {
        "mondo_id": "MONDO_0019402",
        "mondo_label": "thalassemia",
        "mesh_id": "D013789",
        "mesh_label": "Thalassemia",
        "icd10": "D56",
        "snomed_ct": "40108008"
    },
    "Haemophilia": {
        "mondo_id": "MONDO_0001475",
        "mondo_label": "hemophilia",
        "mesh_id": "D006467",
        "mesh_label": "Hemophilia A",
        "icd10": "D66",
        "snomed_ct": "90935002"
    },
    "Multiple sclerosis": {
        "mondo_id": "MONDO_0005301",
        "mondo_label": "multiple sclerosis",
        "mesh_id": "D009103",
        "mesh_label": "Multiple Sclerosis",
        "icd10": "G35",
        "snomed_ct": "24700007"
    },
    "Ulcerative Colitis": {
        "mondo_id": "MONDO_0005101",
        "mondo_label": "ulcerative colitis",
        "mesh_id": "D003093",
        "mesh_label": "Colitis, Ulcerative",
        "icd10": "K51",
        "snomed_ct": "64766004"
    },
    "Inflammatory Bowel Disease": {
        "mondo_id": "MONDO_0005265",
        "mondo_label": "inflammatory bowel disease",
        "mesh_id": "D015212",
        "mesh_label": "Inflammatory Bowel Diseases",
        "icd10": "K50-K52",
        "snomed_ct": "24526004"
    }
}

# Compound Type Mappings to ChEBI and NCIT
COMPOUND_TYPE_MAPPINGS = {
    "Biologic": {
        "chebi_id": "CHEBI_33695",
        "chebi_label": "biological macromolecule",
        "ncit_id": "C1909",
        "ncit_label": "Biological Products",
        "definition": "Large molecules produced by living organisms, including proteins, antibodies, and nucleic acids"
    },
    "Small Molecule": {
        "chebi_id": "CHEBI_25367",
        "chebi_label": "molecule",
        "ncit_id": "C1908",
        "ncit_label": "Chemical",
        "definition": "Low molecular weight compounds typically under 900 daltons"
    },
    "Vaccine": {
        "chebi_id": "CHEBI_59132",
        "chebi_label": "vaccine",
        "ncit_id": "C906",
        "ncit_label": "Vaccine",
        "definition": "Biological preparation that provides immunity to a particular infectious disease"
    },
    "Cell Therapy": {
        "ncit_id": "C15262",
        "ncit_label": "Cell Therapy",
        "mesh_id": "D064987",
        "mesh_label": "Cell- and Tissue-Based Therapy",
        "definition": "Treatment using living cells to restore or establish normal function"
    },
    "RNA Therapy": {
        "chebi_id": "CHEBI_33697",
        "chebi_label": "ribonucleic acid",
        "ncit_id": "C13280",
        "ncit_label": "RNA",
        "definition": "Therapeutic use of RNA molecules including siRNA, mRNA, and antisense oligonucleotides"
    },
    "Radioligand": {
        "ncit_id": "C17262",
        "ncit_label": "Radioligand",
        "definition": "Radioactive compound that binds to specific molecular targets for imaging or therapy"
    }
}

# Development Phase Mappings to NCIT
DEVELOPMENT_PHASE_MAPPINGS = {
    "Phase 1": {
        "ncit_id": "C15600",
        "ncit_label": "Phase I Trial",
        "definition": "Initial studies to determine safety and dosage range"
    },
    "Phase 2": {
        "ncit_id": "C15601", 
        "ncit_label": "Phase II Trial",
        "definition": "Studies to assess effectiveness while monitoring safety"
    },
    "Phase 3": {
        "ncit_id": "C15602",
        "ncit_label": "Phase III Trial", 
        "definition": "Large-scale studies comparing new treatment to standard treatment"
    },
    "Registration/Filed": {
        "ncit_id": "C25646",
        "ncit_label": "Regulatory Submission",
        "definition": "Submission of data to regulatory authorities for approval"
    }
}

# Mechanism of Action Mappings (sample - would be expanded)
MECHANISM_MAPPINGS = {
    "insulin": {
        "chebi_id": "CHEBI_145810",
        "chebi_label": "insulin",
        "go_id": "GO_0005179",
        "go_label": "hormone activity"
    },
    "GLP-1": {
        "chebi_id": "CHEBI_80270", 
        "chebi_label": "GLP-1",
        "go_id": "GO_0005179",
        "go_label": "hormone activity"
    },
    "monoclonal antibody": {
        "chebi_id": "CHEBI_59132",
        "chebi_label": "monoclonal antibody",
        "go_id": "GO_0003823",
        "go_label": "antigen binding"
    }
}

# Regulatory Designation Mappings
REGULATORY_MAPPINGS = {
    "Fast Track": {
        "ncit_id": "C48660",
        "ncit_label": "Fast Track Designation",
        "definition": "FDA designation for drugs addressing unmet medical needs"
    },
    "Breakthrough Designation": {
        "ncit_id": "C116477",
        "ncit_label": "Breakthrough Therapy Designation", 
        "definition": "FDA designation for drugs showing substantial improvement over existing treatments"
    },
    "Orphan Drug": {
        "ncit_id": "C1512",
        "ncit_label": "Orphan Drug",
        "definition": "Drug developed for rare diseases affecting fewer than 200,000 people"
    },
    "Priority Review": {
        "ncit_id": "C48661",
        "ncit_label": "Priority Review",
        "definition": "FDA review process with 6-month timeline for significant improvements"
    }
}

def get_therapeutic_area_ontology(area):
    """Get ontological annotations for therapeutic area"""
    return THERAPEUTIC_AREA_MAPPINGS.get(area, {})

def get_indication_ontology(indication):
    """Get ontological annotations for indication/disease"""
    # Direct match first
    if indication in INDICATION_MAPPINGS:
        return INDICATION_MAPPINGS[indication]
    
    # Fuzzy matching for partial matches
    for key, value in INDICATION_MAPPINGS.items():
        if key.lower() in indication.lower() or indication.lower() in key.lower():
            return value
    
    return {}

def get_compound_type_ontology(compound_type):
    """Get ontological annotations for compound type"""
    return COMPOUND_TYPE_MAPPINGS.get(compound_type, {})

def get_development_phase_ontology(phase):
    """Get ontological annotations for development phase"""
    return DEVELOPMENT_PHASE_MAPPINGS.get(phase, {})

def get_mechanism_ontology(mechanism_text):
    """Get ontological annotations for mechanism of action"""
    if not mechanism_text:
        return {}
    
    mechanism_lower = mechanism_text.lower()
    for key, value in MECHANISM_MAPPINGS.items():
        if key in mechanism_lower:
            return value
    
    return {}

def get_regulatory_ontology(designation):
    """Get ontological annotations for regulatory designation"""
    return REGULATORY_MAPPINGS.get(designation, {})
