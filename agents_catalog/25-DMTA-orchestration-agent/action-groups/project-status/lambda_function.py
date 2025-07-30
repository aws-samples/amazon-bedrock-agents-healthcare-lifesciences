import json
import boto3
import os
from decimal import Decimal

# Initialize AWS clients
dynamodb = boto3.resource('dynamodb')

def lambda_handler(event, context):
    """Handle project_status function"""
    print(f"Received event: {json.dumps(event)}")
    
    parameters = event.get('parameters', [])
    param_dict = {param['name']: param['value'] for param in parameters}
    
    query_type = param_dict.get('query_type', 'all_projects')
    project_id = param_dict.get('project_id', '')
    
    try:
        if query_type == 'project_count':
            result = get_project_count()
        elif query_type == 'project_progress':
            result = get_project_progress(project_id)
        else:
            result = get_all_projects_status()
    except Exception as e:
        result = {'error': str(e)}
    
    return {
        'response': {
            'actionGroup': event['actionGroup'],
            'function': event['function'],
            'functionResponse': {
                'responseBody': {
                    'TEXT': {
                        'body': json.dumps({
                            'message': 'Project status retrieved',
                            'status_data': convert_decimals_to_float(result)
                        })
                    }
                }
            }
        }
    }

def get_project_count():
    """Get total number of projects"""
    try:
        project_table = dynamodb.Table(os.environ['PROJECT_TABLE'])
        response = project_table.scan(
            Select='COUNT'
        )
        return {
            'total_projects': response['Count']
        }
    except Exception as e:
        return {'error': str(e)}

def get_project_progress(project_id):
    """Get project progress"""
    try:
        # Get project table
        project_table = dynamodb.Table(os.environ['PROJECT_TABLE'])
        
        if not project_id:
            # Get first project ID
            response = project_table.scan(
                ProjectionExpression='project_id',
                Limit=1
            )
            if response['Items']:
                project_id = response['Items'][0]['project_id']
            else:
                project_id = 'demo-project'
        
        # Get cycles
        cycle_table = dynamodb.Table(os.environ['CYCLE_TABLE'])
        cycle_response = cycle_table.query(
            KeyConditionExpression='project_id = :pid',
            ExpressionAttributeValues={
                ':pid': project_id
            }
        )
        cycles = cycle_response.get('Items', [])
        
        # Get variants
        variant_table = dynamodb.Table(os.environ['VARIANT_TABLE'])
        variant_response = variant_table.query(
            KeyConditionExpression='project_id = :pid',
            ExpressionAttributeValues={
                ':pid': project_id
            }
        )
        variants = variant_response.get('Items', [])
        
        return {
            'project_id': project_id,
            'cycles_completed': len(cycles),
            'variants_generated': len(variants),
            'current_phase': determine_current_phase(cycles, variants),
            'cycles_summary': cycles
        }
    except Exception as e:
        return {'error': str(e)}

def get_all_projects_status():
    """Get all projects status"""
    try:
        project_table = dynamodb.Table(os.environ['PROJECT_TABLE'])
        response = project_table.scan()
        projects = response.get('Items', [])
        
        return {
            'total_projects': len(projects),
            'projects': projects
        }
    except Exception as e:
        return {'error': str(e)}

def determine_current_phase(cycles, variants):
    """Determine current phase"""
    if not cycles and not variants:
        return "Project planned - ready to start Cycle 1 Design"
    
    if not cycles:
        current_cycle = max([int(v.get('cycle_number', 1)) for v in variants])
        return f"Cycle {current_cycle} Design completed - ready for Make-Test"
    
    latest_cycle = max([int(c['cycle_number']) for c in cycles])
    next_cycle = latest_cycle + 1
    next_variants = [v for v in variants if int(v.get('cycle_number', 0)) == next_cycle]
    
    if next_variants:
        return f"Cycle {next_cycle} Design completed - ready for Make-Test"
    else:
        return f"Cycle {latest_cycle} completed - ready for Cycle {next_cycle} Design"

def convert_decimals_to_float(obj):
    """Recursively convert Decimal objects to float for JSON serialization"""
    if isinstance(obj, list):
        return [convert_decimals_to_float(item) for item in obj]
    elif isinstance(obj, dict):
        return {key: convert_decimals_to_float(value) for key, value in obj.items()}
    elif isinstance(obj, Decimal):
        return float(obj)
    else:
        return obj
