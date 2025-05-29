import json
import requests

# Mapping input parameters to ClinicalTrials.gov API v2 query keys
QUERY_MAP = {
    "condition": "query.cond",
    "location": "query.locn",
    "title": "query.titles",
    "intervention": "query.intr",
    "outcome": "query.outc",
    "sponsor": "query.spons",
    "lead_sponsor": "query.lead",
    "study_id": "query.id",
    "patient": "query.patient",
}

def search_studies(query_fields=None, page_size=10, max_pages=1, fields=None):
    base_url = "https://clinicaltrials.gov/api/v2/studies"
    query_fields = query_fields or {}
    fields = fields or [
        "NCTId", "BriefTitle", "OverallStatus", "InterventionName", "PrimaryOutcomeMeasure"
    ]

    params = {
        "format": "json",
        "pageSize": page_size,
        "fields": ",".join(fields)
    }

    print("[DEBUG] Initial query fields:")
    print(json.dumps(query_fields, indent=2))

    for key, value in query_fields.items():
        if key in QUERY_MAP and value:
            param_key = QUERY_MAP[key]
            param_val = value.strip()
            params[param_key] = param_val
            print(f"[DEBUG] Added query param: {param_key} = {param_val}")

    results = []
    next_token = None
    page = 0

    while page < max_pages:
        if next_token:
            params["pageToken"] = next_token
            print(f"[DEBUG] Fetching page {page + 1} with token: {next_token}")

        print("[DEBUG] Sending request to ClinicalTrials.gov with params:")
        print(json.dumps(params, indent=2))

        res = requests.get(base_url, params=params)
        print(f"[DEBUG] Requested URL: {res.url}")

        if res.status_code != 200:
            print(f"[ERROR] API call failed with status code {res.status_code}")
            raise Exception(f"API call failed: {res.status_code} - {res.text}")

        data = res.json()
        page_results = data.get("studies", [])
        print(f"[DEBUG] Retrieved {len(page_results)} results on page {page + 1}")
        results.extend(page_results)

        next_token = data.get("nextPageToken")
        if not next_token:
            print("[DEBUG] No more pages to fetch.")
            break

        page += 1

    print(f"[DEBUG] Total results retrieved: {len(results)}")
    return results

def get_study_details(nct_id):
    print(f"[DEBUG] Fetching study details for NCT ID: {nct_id}")

    url = f"https://clinicaltrials.gov/api/v2/studies/{nct_id}"
    params = {
        "format": "json",
        "markupFormat": "markdown",
        "fields": ",".join([
            "NCTId", "BriefTitle", "BriefSummary", "Phase",
            "StartDate", "CompletionDate", "OverallStatus",
            "ConditionsModule", "EligibilityModule",
            "ArmsInterventionsModule", "SponsorCollaboratorsModule",
            "OutcomesModule"
        ])
    }

    print("[DEBUG] Sending request to ClinicalTrials.gov:")
    print(json.dumps(params, indent=2))

    res = requests.get(url, params=params)
    print(f"[DEBUG] Requested URL: {res.url}")

    if res.status_code != 200:
        print(f"[ERROR] Study details API failed with status {res.status_code}")
        raise Exception(f"Study details API failed: {res.status_code}")

    study_data = res.json()
    print("[DEBUG] Study data retrieved successfully.")
    return study_data

def lambda_handler(event, context):
    agent = event.get('agent', '')
    actionGroup = event.get('actionGroup', '')
    function = event.get('function', '')
    parameter_list = event.get('parameters', [])

    print("[INFO] Lambda function invoked")
    print(f"Agent: {agent}")
    print(f"Action Group: {actionGroup}")
    print(f"Function: {function}")
    print(f"Raw Parameter List:\n{json.dumps(parameter_list, indent=2)}")

    parameters = {param["name"]: param["value"] for param in parameter_list if "name" in param and "value" in param}

    print("[DEBUG] Converted Parameters Dictionary:")
    print(json.dumps(parameters, indent=2))

    try:
        if function == "search_trials":
            query_fields = {
                "condition": parameters.get("condition"),
                "intervention": parameters.get("intervention"),
                "comparison": parameters.get("comparison"),
                "outcome": parameters.get("outcome"),
                "location": parameters.get("location"),
                "title": parameters.get("title"),
                "sponsor": parameters.get("sponsor"),
                "lead_sponsor": parameters.get("lead_sponsor"),
                "study_id": parameters.get("study_id"),
                "patient": parameters.get("patient"),
            }

            print("[DEBUG] Mapped Query Fields for API:")
            print(json.dumps(query_fields, indent=2))

            results = search_studies(
                query_fields=query_fields,
                page_size=10,
                max_pages=1,
                fields=[
                    "NCTId", "BriefTitle", "OverallStatus", "InterventionName", "Phase",
                    "StartDate", "CompletionDate", "LeadSponsorName"
                ]
            )

            print("[DEBUG] Printing summary of retrieved studies:")
            for study in results:
                study_id = study.get('protocolSection', {}).get('identificationModule', {}).get('nctId')
                title = study.get('protocolSection', {}).get('identificationModule', {}).get('briefTitle')
                print(f" - {study_id} | {title}")

            response_body = {
                "TEXT": {
                    "body": f"Here are the top search results from ClinicalTrials.gov '{results}'"
                }
            }

        elif function == "get_trial_details":
            nct_id = parameters.get("nctId")
            if not nct_id:
                raise ValueError("Missing or invalid NCT ID.")
            study = get_study_details(nct_id)
            response_body = {
                "TEXT": {
                    "body": f"Study details for {nct_id} : '{study}'"
                }
            }

        else:
            raise ValueError(f"Unsupported function: {function}")
    
        function_response = {
            'actionGroup': actionGroup,
            'function': function,
            'functionResponse': {
                'responseBody': response_body
            }
        }

    except Exception as e:
        print(f"[ERROR] Exception occurred: {str(e)}")
        response_state = "FAILURE"
        response_body = {
            "TEXT": {
                "body": f"An error occurred: {str(e)}"
            }
        }

        function_response = {
            'actionGroup': actionGroup,
            'function': function,
            'functionResponse': {
                'responseState': response_state,
                'responseBody': response_body
            }
        }

    action_response = {
        'messageVersion': '1.0',
        'response': function_response,
        'sessionAttributes': event.get('sessionAttributes', {}),
        'promptSessionAttributes': event.get('promptSessionAttributes', {})
    }

    print("[INFO] Final Formatted Lambda Response:")
    print(json.dumps(action_response, indent=2))

    return action_response

