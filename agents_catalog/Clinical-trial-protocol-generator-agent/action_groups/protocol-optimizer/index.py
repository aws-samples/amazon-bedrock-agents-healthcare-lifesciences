import json
import logging
import os
import math

# Configure logging
logger = logging.getLogger()
log_level = os.environ.get("LOG_LEVEL", "INFO")
logger.setLevel(log_level)

# Inclusion/exclusion criteria templates by condition
CRITERIA_TEMPLATES = {
    "type 2 diabetes": {
        "inclusion": [
            "Diagnosis of type 2 diabetes for at least 6 months",
            "HbA1c between 7.0% and 10.0%",
            "Age 18-75 years",
            "Body mass index (BMI) between 25 and 40 kg/m²",
            "Stable dose of current antidiabetic medication for at least 3 months"
        ],
        "exclusion": [
            "Type 1 diabetes",
            "History of diabetic ketoacidosis",
            "Severe hypoglycemia requiring hospitalization within the past 6 months",
            "Estimated glomerular filtration rate (eGFR) < 45 mL/min/1.73m²",
            "History of pancreatitis or pancreatic cancer",
            "Current use of insulin or GLP-1 receptor agonists",
            "Pregnant or breastfeeding women"
        ]
    },
    "breast cancer": {
        "inclusion": [
            "Histologically confirmed breast cancer",
            "ECOG performance status 0-1",
            "Adequate bone marrow function",
            "Adequate liver and renal function",
            "Measurable disease according to RECIST v1.1 criteria"
        ],
        "exclusion": [
            "Prior chemotherapy within 4 weeks of study entry",
            "Known brain metastases",
            "History of other malignancy within the past 5 years",
            "Significant cardiovascular disease",
            "Pregnant or breastfeeding women",
            "Known hypersensitivity to study drug or its excipients"
        ]
    },
    "depression": {
        "inclusion": [
            "DSM-5 diagnosis of major depressive disorder",
            "Hamilton Depression Rating Scale (HAM-D) score ≥ 18",
            "Age 18-65 years",
            "Inadequate response to at least one antidepressant treatment in the current episode",
            "Stable dose of current antidepressant for at least 4 weeks"
        ],
        "exclusion": [
            "Bipolar disorder or psychotic features",
            "Substance use disorder within the past 6 months",
            "Significant risk of suicide",
            "History of seizure disorder",
            "Electroconvulsive therapy within the past 3 months",
            "Pregnant or breastfeeding women"
        ]
    }
}

# Endpoint recommendations by condition and phase
ENDPOINT_RECOMMENDATIONS = {
    "type 2 diabetes": {
        "Phase 1": {
            "primary": ["Safety and tolerability", "Pharmacokinetic parameters"],
            "secondary": ["Changes in fasting plasma glucose", "Changes in postprandial glucose"]
        },
        "Phase 2": {
            "primary": ["Change in HbA1c from baseline to week 12"],
            "secondary": ["Proportion of patients achieving HbA1c < 7.0%", "Change in fasting plasma glucose", "Change in body weight", "Incidence of hypoglycemia"]
        },
        "Phase 3": {
            "primary": ["Change in HbA1c from baseline to week 26"],
            "secondary": ["Proportion of patients achieving HbA1c < 7.0%", "Change in fasting plasma glucose", "Change in body weight", "Time to rescue medication", "Patient-reported outcomes", "Cardiovascular safety endpoints"]
        }
    },
    "heart failure": {
        "Phase 1": {
            "primary": ["Safety and tolerability", "Pharmacokinetic parameters"],
            "secondary": ["Changes in NT-proBNP levels", "Hemodynamic parameters"]
        },
        "Phase 2": {
            "primary": ["Change in NT-proBNP levels from baseline to week 12"],
            "secondary": ["Change in 6-minute walk distance", "Change in NYHA functional class", "Change in quality of life scores", "Incidence of worsening heart failure"]
        },
        "Phase 3": {
            "primary": ["Composite of cardiovascular death or heart failure hospitalization"],
            "secondary": ["All-cause mortality", "Total heart failure hospitalizations", "Change in quality of life scores", "Change in 6-minute walk distance", "Change in NYHA functional class"]
        }
    },
    "depression": {
        "Phase 1": {
            "primary": ["Safety and tolerability", "Pharmacokinetic parameters"],
            "secondary": ["Changes in mood assessment scales"]
        },
        "Phase 2": {
            "primary": ["Change in Montgomery-Åsberg Depression Rating Scale (MADRS) from baseline to week 6"],
            "secondary": ["Response rate (≥50% reduction in MADRS)", "Remission rate (MADRS ≤10)", "Change in Hamilton Anxiety Rating Scale", "Change in Clinical Global Impression scale"]
        },
        "Phase 3": {
            "primary": ["Change in Montgomery-Åsberg Depression Rating Scale (MADRS) from baseline to week 8"],
            "secondary": ["Response and remission rates", "Change in Hamilton Anxiety Rating Scale", "Change in Clinical Global Impression scale", "Change in quality of life measures", "Relapse rates during follow-up phase"]
        }
    }
}

def generate_inclusion_exclusion_criteria(condition, intervention, population, study_phase=None):
    """
    Generate inclusion and exclusion criteria for a clinical trial.
    """
    logger.info(f"Generating criteria for {condition} with {intervention} in {population}")
    
    # Find the best matching condition template
    condition_lower = condition.lower()
    best_match = None
    for template_condition in CRITERIA_TEMPLATES:
        if template_condition in condition_lower:
            best_match = template_condition
            break
    
    # Use default template if no match found
    if not best_match:
        if "diabetes" in condition_lower:
            best_match = "type 2 diabetes"
        elif "cancer" in condition_lower:
            best_match = "breast cancer"
        elif "depress" in condition_lower:
            best_match = "depression"
        else:
            # Create generic criteria if no template matches
            return {
                "inclusion": [
                    f"Diagnosis of {condition}",
                    "Age 18 years or older",
                    "Able to provide informed consent",
                    "Adequate organ function"
                ],
                "exclusion": [
                    "Participation in another clinical trial within 30 days",
                    "Known hypersensitivity to study drug or its components",
                    "Pregnant or breastfeeding women",
                    "Any condition that would compromise patient safety or study integrity"
                ],
                "note": "These are generic criteria. Consider consulting with clinical experts for condition-specific criteria."
            }
    
    # Get base criteria from template
    base_criteria = CRITERIA_TEMPLATES[best_match]
    
    # Customize criteria based on intervention and population
    custom_criteria = {
        "inclusion": base_criteria["inclusion"].copy(),
        "exclusion": base_criteria["exclusion"].copy()
    }
    
    # Add intervention-specific criteria
    intervention_lower = intervention.lower()
    if "monoclonal antibody" in intervention_lower or "biologic" in intervention_lower:
        custom_criteria["exclusion"].append("History of severe allergic reactions")
        custom_criteria["exclusion"].append("Active infection or recent live vaccination")
    
    if "gene therapy" in intervention_lower:
        custom_criteria["exclusion"].append("Prior gene therapy treatment")
        custom_criteria["exclusion"].append("Presence of neutralizing antibodies to the viral vector")
    
    # Add population-specific criteria
    population_lower = population.lower()
    if "elderly" in population_lower or "older" in population_lower:
        custom_criteria["inclusion"] = [c for c in custom_criteria["inclusion"] if "18-" not in c]
        custom_criteria["inclusion"].append("Age 65 years or older")
    
    if "pediatric" in population_lower or "children" in population_lower:
        custom_criteria["inclusion"] = [c for c in custom_criteria["inclusion"] if "18" not in c]
        custom_criteria["inclusion"].append("Age 2-17 years")
        custom_criteria["inclusion"].append("Parental/guardian informed consent and child assent (when appropriate)")
    
    # Add phase-specific criteria
    if study_phase:
        phase = study_phase.lower()
        if "1" in phase:
            custom_criteria["inclusion"].append("Healthy volunteers or patients with mild disease")
            custom_criteria["exclusion"].append("Multiple comorbidities")
        elif "3" in phase:
            custom_criteria["inclusion"].append("Representative of the broader target population")
    
    return custom_criteria

def recommend_endpoints(condition, intervention, study_phase):
    """
    Recommend appropriate primary and secondary endpoints for a clinical trial.
    """
    logger.info(f"Recommending endpoints for {condition} with {intervention} in {study_phase}")
    
    # Find the best matching condition template
    condition_lower = condition.lower()
    best_match = None
    for template_condition in ENDPOINT_RECOMMENDATIONS:
        if template_condition in condition_lower:
            best_match = template_condition
            break
    
    # Use default template if no match found
    if not best_match:
        if "diabetes" in condition_lower:
            best_match = "type 2 diabetes"
        elif "heart" in condition_lower or "cardiac" in condition_lower:
            best_match = "heart failure"
        elif "depress" in condition_lower or "mood" in condition_lower:
            best_match = "depression"
        else:
            # Create generic endpoints if no template matches
            return {
                "primary": ["Safety and tolerability" if "1" in study_phase else "Efficacy measure specific to condition"],
                "secondary": [
                    "Pharmacokinetic parameters" if "1" in study_phase else "Additional efficacy measures",
                    "Patient-reported outcomes",
                    "Quality of life assessments"
                ],
                "exploratory": [
                    "Biomarker assessments",
                    "Long-term outcomes"
                ],
                "note": "These are generic endpoints. Consider consulting with clinical experts for condition-specific endpoints."
            }
    
    # Get phase-specific endpoints
    phase = None
    if "1" in study_phase:
        phase = "Phase 1"
    elif "2" in study_phase:
        phase = "Phase 2"
    elif "3" in study_phase:
        phase = "Phase 3"
    else:
        phase = "Phase 2"  # Default to Phase 2 if unclear
    
    # Get endpoints from template
    endpoints = ENDPOINT_RECOMMENDATIONS[best_match].get(phase, ENDPOINT_RECOMMENDATIONS[best_match]["Phase 2"])
    
    # Add exploratory endpoints based on intervention
    exploratory = []
    intervention_lower = intervention.lower()
    
    if "monoclonal antibody" in intervention_lower or "biologic" in intervention_lower:
        exploratory.append("Immunogenicity assessments")
        exploratory.append("Biomarker analysis for target engagement")
    
    if "gene therapy" in intervention_lower:
        exploratory.append("Vector shedding analysis")
        exploratory.append("Long-term expression of therapeutic gene")
    
    # Add exploratory endpoints to the recommendation
    endpoints["exploratory"] = exploratory
    
    return endpoints

def calculate_sample_size(study_design, power, effect_size, endpoint_type):
    """
    Calculate the required sample size for a clinical trial based on statistical parameters.
    """
    logger.info(f"Calculating sample size for {study_design} trial with {power} power to detect {effect_size} in {endpoint_type} endpoint")
    
    # Parse power value
    power_value = float(power.strip("%")) / 100 if "%" in power else float(power)
    
    # Set alpha (significance level)
    alpha = 0.05
    
    # Calculate z-scores
    z_alpha = 1.96  # For alpha = 0.05
    z_beta = 0.84 if power_value == 0.8 else 1.28  # For power = 80% or 90%
    
    # Parse effect size
    effect_size_value = None
    if "%" in effect_size:
        effect_size_value = float(effect_size.strip("%")) / 100
    elif "point" in effect_size.lower():
        effect_size_value = float(effect_size.split()[0])
    else:
        try:
            effect_size_value = float(effect_size)
        except:
            effect_size_value = 0.3  # Default moderate effect size
    
    # Calculate sample size based on endpoint type and study design
    sample_size = None
    sample_size_per_group = None
    
    if endpoint_type.lower() == "binary":
        # For binary endpoints (proportions)
        # Assuming control proportion is 0.5 if not specified
        control_prop = 0.5
        treatment_prop = control_prop + effect_size_value if "%" in effect_size else control_prop * (1 + effect_size_value)
        
        pooled_prop = (control_prop + treatment_prop) / 2
        variance = 2 * pooled_prop * (1 - pooled_prop)
        
        sample_size_per_group = math.ceil((z_alpha + z_beta)**2 * variance / (control_prop - treatment_prop)**2)
        
    elif endpoint_type.lower() == "continuous":
        # For continuous endpoints
        # Assuming standardized effect size if not specified
        standardized_effect = effect_size_value
        
        sample_size_per_group = math.ceil(2 * ((z_alpha + z_beta) / standardized_effect)**2)
        
    elif endpoint_type.lower() == "time-to-event":
        # For time-to-event endpoints
        # Assuming hazard ratio
        hazard_ratio = 1 - effect_size_value if effect_size_value < 1 else effect_size_value
        
        # Simplified calculation for time-to-event
        sample_size_per_group = math.ceil(4 * ((z_alpha + z_beta) / math.log(hazard_ratio))**2)
    
    # Adjust for study design
    if study_design.lower() == "non-inferiority" or study_design.lower() == "equivalence":
        sample_size_per_group = math.ceil(sample_size_per_group * 1.25)  # 25% increase for non-inferiority
    
    # Calculate total sample size
    sample_size = sample_size_per_group * 2
    
    # Add 15% for potential dropouts
    sample_size_with_dropout = math.ceil(sample_size * 1.15)
    
    return {
        "sample_size_per_group": sample_size_per_group,
        "total_sample_size": sample_size,
        "recommended_sample_size": sample_size_with_dropout,
        "assumptions": {
            "alpha": alpha,
            "power": power_value,
            "effect_size": effect_size_value,
            "endpoint_type": endpoint_type,
            "dropout_rate": "15%"
        },
        "notes": "This is an approximate calculation. Consider consulting with a statistician for a more precise sample size calculation based on your specific study parameters."
    }

def lambda_handler(event, context):
    """
    Lambda handler for the protocol optimizer action group.
    """
    logger.info(f"Received event: {json.dumps(event)}")
    
    try:
        # Extract action group parameters
        api_path = event.get('apiPath')
        parameters = event.get('parameters', {})
        
        # Process based on API path
        if api_path == 'generate_inclusion_exclusion_criteria':
            condition = parameters.get('condition')
            intervention = parameters.get('intervention')
            population = parameters.get('population')
            study_phase = parameters.get('study_phase')
            
            result = generate_inclusion_exclusion_criteria(
                condition, 
                intervention, 
                population, 
                study_phase
            )
            
            return {
                'response': result,
                'messageVersion': '1.0'
            }
            
        elif api_path == 'recommend_endpoints':
            condition = parameters.get('condition')
            intervention = parameters.get('intervention')
            study_phase = parameters.get('study_phase')
            
            result = recommend_endpoints(condition, intervention, study_phase)
            
            return {
                'response': result,
                'messageVersion': '1.0'
            }
            
        elif api_path == 'calculate_sample_size':
            study_design = parameters.get('study_design')
            power = parameters.get('power')
            effect_size = parameters.get('effect_size')
            endpoint_type = parameters.get('endpoint_type')
            
            result = calculate_sample_size(study_design, power, effect_size, endpoint_type)
            
            return {
                'response': result,
                'messageVersion': '1.0'
            }
            
        else:
            return {
                'response': {
                    'error': f'Unsupported API path: {api_path}'
                },
                'messageVersion': '1.0'
            }
            
    except Exception as e:
        logger.error(f"Error processing request: {str(e)}")
        return {
            'response': {
                'error': f'Error processing request: {str(e)}'
            },
            'messageVersion': '1.0'
        }
