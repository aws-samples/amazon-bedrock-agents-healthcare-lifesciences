import requests
from strands import tool

@tool
def search_clinical_trials(condition: str, max_results: int = 5) -> str:
    """
    Search ClinicalTrials.gov for clinical trials information.

    Args:
        condition (str): Medical condition or intervention to search for.
        max_results (int): Maximum number of results to return (default: 5).

    Returns:
        str: Clinical trials search results.
    """
    try:
        url = "https://clinicaltrials.gov/api/v2/studies"
        params = {
            "query.cond": condition,
            "pageSize": max_results,
            "format": "json"
        }
        
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        
        if not data.get("studies"):
            return f"No clinical trials found for condition: {condition}"
        
        studies = data["studies"]
        results = []
        
        for study in studies:
            protocol = study.get("protocolSection", {})
            identification = protocol.get("identificationModule", {})
            status_module = protocol.get("statusModule", {})
            design_module = protocol.get("designModule", {})
            conditions_module = protocol.get("conditionsModule", {})
            interventions_module = protocol.get("armsInterventionsModule", {})
            
            nct_id = identification.get("nctId", "Unknown")
            title = identification.get("briefTitle", "No title")
            conditions = ", ".join(conditions_module.get("conditions", ["Unknown"]))
            
            interventions = []
            for intervention in interventions_module.get("interventions", []):
                interventions.append(intervention.get("name", "Unknown"))
            interventions_str = ", ".join(interventions) if interventions else "Unknown"
            
            phases = design_module.get("phases", ["Unknown"])
            phase = ", ".join(phases)
            
            status = status_module.get("overallStatus", "Unknown")
            start_date = status_module.get("startDateStruct", {}).get("date", "Unknown")
            completion_date = status_module.get("completionDateStruct", {}).get("date", "Unknown")
            
            results.append(f"NCT ID: {nct_id}\nTitle: {title}\nConditions: {conditions}\nInterventions: {interventions_str}\nPhase: {phase}\nStatus: {status}\nStart Date: {start_date}\nCompletion Date: {completion_date}\nURL: https://clinicaltrials.gov/study/{nct_id}\n")
        
        return "\n".join(results)
        
    except Exception as e:
        return f"Error searching clinical trials: {str(e)}"