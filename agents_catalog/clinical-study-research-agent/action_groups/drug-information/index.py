import json
import requests

OPEN_FDA_URL = "https://api.fda.gov/drug/drugsfda.json"

def sanitize(value):
    if value and ' ' in value and not value.startswith('"'):
        return f'"{value}"'
    return value
    
def query_fda(condition=None, route=None, limit=100):
    search_terms = []
    if condition:
        search_terms.append(f'indications_and_usage:{sanitize(condition)}')
    if route:
        search_terms.append(f'route:{sanitize(route)}')


    params = {
        'search': '+AND+'.join(search_terms),
        'limit': limit
    }

    print("[DEBUG] FDA Query Params:")
    print(json.dumps(params, indent=2))

    response = requests.get(OPEN_FDA_URL, params=params)
    print(f"[DEBUG] Requested URL: {response.url}")

    if response.status_code != 200:
        raise Exception(f"OpenFDA API call failed: {response.status_code} - {response.text}")

    return response.json().get("results", [])

def summarize_drugs(fda_results):
    unique_drugs = set()
    route_counts = {}

    for item in fda_results:
        products = item.get("products", [])
        for product in products:
            brand_name = product.get("brand_name")
            route = product.get("route")

            if brand_name:
                unique_drugs.add(brand_name)

            if route:
                route_counts[route] = route_counts.get(route, 0) + 1

    return {
        "total_drugs": len(unique_drugs),
        "routes": route_counts,
        "drug_names": list(unique_drugs)[:10]  # Limit to top 10 for brevity
    }

def lambda_handler(event, context):
    agent = event.get('agent', '')
    actionGroup = event.get('actionGroup', '')
    function = event.get('function', '')
    parameter_list = event.get('parameters', [])
    session_attributes = event.get('sessionAttributes', {})
    prompt_session_attributes = event.get('promptSessionAttributes', {})

    print("[INFO] Lambda function invoked")
    print(f"Function: {function}")
    print(f"Parameters:\n{json.dumps(parameter_list, indent=2)}")

    # Convert to dict
    parameters = {param["name"]: param["value"] for param in parameter_list if "name" in param and "value" in param}
    condition = parameters.get("condition")
    route = parameters.get("route")

    try:
        raw_results = query_fda(condition=condition, route=route)
        summary = summarize_drugs(raw_results)

        response_body = {
            "TEXT": {
                "body": f"Found {summary['total_drugs']} approved drugs for '{condition}'"
                        + (f" with route '{route}'" if route else "") + ".",
                "routeBreakdown": summary["routes"],
                "exampleDrugs": summary["drug_names"]
            }
        }
        response_state = "SUCCESS"

    except Exception as e:
        print(f"[ERROR] {str(e)}")
        response_state = "FAILURE"
        response_body = {
            "TEXT": {
                "body": f"Failed to retrieve approved drugs. Error: {str(e)}"
            }
        }

    return {
        "messageVersion": "1.0",
        "response": {
            "actionGroup": actionGroup,
            "function": function,
            "functionResponse": {
                "responseState": response_state,
                "responseBody": response_body
            }
        },
        "sessionAttributes": session_attributes,
        "promptSessionAttributes": prompt_session_attributes
    }
