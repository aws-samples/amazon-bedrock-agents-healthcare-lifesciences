
import json
import ast

def group_survival_data(biomarker: list, survival_duration: list, survival_status: list, threshold: float):
    """
    Separate biomarker values, survival durations, and survival statuses into two groups
    based on a given threshold.

    Args:
        biomarker (list): List of biomarker values.
        survival_duration (list): List of survival durations.
        survival_status (list): List of survival statuses (0 for Alive, 1 for Dead).
        threshold (float): Threshold value for separating the data.

    Returns:
        tuple: A tuple containing four lists:
            - baseline_durations: Survival durations for the baseline group.
            - baseline_events: Survival statuses for the baseline group.
            - condition_durations: Survival durations for the condition group.
            - condition_events: Survival statuses for the condition group.
    """
    baseline_durations = []
    baseline_events = []
    condition_durations = []
    condition_events = []

    for i, value in enumerate(biomarker):
        print(value)
        print(type(value))
        if float(value) <= float(threshold):
            baseline_durations.append(survival_duration[i])
            baseline_events.append(survival_status[i])
        else:
            condition_durations.append(survival_duration[i])
            condition_events.append(survival_status[i])
    # Create a dictionary with the output data
    data = {
        "baseline": {
            "durations": baseline_durations,
            "events": baseline_events
        },
        "condition": {
            "durations": condition_durations,
            "events": condition_events
        }
    }

    # Convert the dictionary to JSON
    json_data = json.dumps(data)

    return json_data


def lambda_handler(event, context):
    agent = event['agent']
    actionGroup = event['actionGroup']
    function = event['function']
    parameters = event.get('parameters', [])
    try:
        if function == "group_survival_data":
            for param in parameters:
                if param["name"] == "biomarker":
                    biomarker = param["value"]
                if param["name"] == "survival_duration":
                    survival_duration = param["value"]
                if param["name"] == "survival_status":
                    survival_status = param["value"]
                if param["name"] == "threshold":
                    threshold = param["value"]
            print(type(biomarker))
            print(biomarker)
            print(survival_duration)
            print(survival_status)
            print(threshold)
            biomarker = ast.literal_eval(biomarker)
            survival_duration = ast.literal_eval(survival_duration)
            survival_status = ast.literal_eval(survival_status)
            print(type(biomarker))
            print(biomarker)
            print(survival_duration)
            print(survival_status)
            print(threshold)
            
            json_data = group_survival_data(biomarker, survival_duration, survival_status, threshold)

        # Execute your business logic here. For more information, refer to: https://docs.aws.amazon.com/bedrock/latest/userguide/agents-lambda.html
        responseBody =  {
            "TEXT": {
                "body": json_data
            }
        }
    
        action_response = {
            'actionGroup': actionGroup,
            'function': function,
            'functionResponse': {
                'responseBody': responseBody
            }
    
        }
    
        dummy_function_response = {'response': action_response}
        print("Response: {}".format(dummy_function_response))
        return dummy_function_response
    except Exception as e:
        error_message = str(e)
        print(f"Error occurred: {error_message}")
        return error_message

    
