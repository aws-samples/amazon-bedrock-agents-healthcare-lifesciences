import json
import boto3
import os
import random
import statistics
from datetime import datetime
from decimal import Decimal

# Initialize AWS clients
s3 = boto3.client('s3')
lambda_client = boto3.client('lambda')
dynamodb = boto3.resource('dynamodb')

def lambda_handler(event, context):
    """Handle make_test function - Execute expression and SPR binding assays with FactorX simulation"""
    print(f"Received event: {json.dumps(event)}")
    
    # Extract parameters from the event
    parameters = event.get('parameters', [])
    param_dict = {param['name']: param['value'] for param in parameters}
    
    variant_list = param_dict.get('variant_list', '[]')
    config_str = param_dict.get('config', '{}')
    cycle_number = int(param_dict.get('cycle_number', 1))  # Added cycle_number parameter
    
    try:
        config = json.loads(config_str) if config_str else {}
    except:
        config = {}
    
    assay_type = config.get('assay_type', 'SPR binding assay')
    target_protein = config.get('target_protein', 'vWF A1 domain')
    quality_controls = config.get('quality_controls', '{}')
    use_opentrons = config.get('use_opentrons', 'true').lower() == 'true'
    
    # Parse variant list
    if isinstance(variant_list, str):
        try:
            # Handle string format "[VAR_1_01, VAR_1_02, ...]"
            variant_list = variant_list.strip('[]').split(',')
            variant_list = [{'variant_id': v.strip()} for v in variant_list if v.strip()]
        except:
            variant_list = []
    elif isinstance(variant_list, list):
        # Handle list format already
        variant_list = [{'variant_id': v} if isinstance(v, str) else v for v in variant_list]
    
    try:
        qc_params = quality_controls if isinstance(quality_controls, dict) else json.loads(str(quality_controls)) if quality_controls else {}
    except:
        qc_params = {}
    
    # Execute Opentrons OT-2 automation if requested
    opentrons_results = None
    if use_opentrons and variant_list:
        opentrons_results = execute_opentrons_automation(variant_list)
    
    # Generate FactorX experimental data with OT-2 integration
    results = generate_factorx_data(variant_list, assay_type, target_protein, qc_params, opentrons_results)
    
    # Store results in DynamoDB and S3
    experiment_id = store_experimental_data(results, assay_type)
    
    # Update cycle data with experimental results
    try:
        project_table = dynamodb.Table(os.environ['PROJECT_TABLE'])
        cycle_table = dynamodb.Table(os.environ['CYCLE_TABLE'])
        
        # Get the latest project
        response = project_table.scan(
            ProjectionExpression='project_id',
            Limit=1
        )
        project_id = response['Items'][0]['project_id'] if response['Items'] else 'default-project'
        
        # Convert results to Decimal before storing in DynamoDB
        dynamodb_results = convert_floats_to_decimals(results)
        
        # Update cycle with experimental results
        cycle_table.update_item(
            Key={
                'project_id': project_id,
                'cycle_number': cycle_number
            },
            UpdateExpression="SET experimental_results = :r, cycle_stage = :s, #ts = :t",
            ExpressionAttributeValues={
                ':r': dynamodb_results,
                ':s': 'test',
                ':t': datetime.now().isoformat()
            },
            ExpressionAttributeNames={
                '#ts': 'timestamp'
            }
        )
        print(f"Updated cycle data with experimental results: {project_id}, cycle {cycle_number}")
    except Exception as e:
        print(f"Error updating cycle data: {str(e)}")
        raise e
    
    # Generate assay report
    assay_report = generate_assay_report(results, assay_type, target_protein)
    
    # Convert Decimal to float for JSON serialization
    results_json = convert_decimals_to_float(results)
    assay_report_json = convert_decimals_to_float(assay_report)
    
    response_body = {
        'message': f'Completed {assay_type} for {len(results)} variants against {target_protein}' + (' with OT-2 automation' if use_opentrons else ''),
        'experiment_id': experiment_id,
        'experimental_results': results_json,
        'assay_report': assay_report_json,
        'opentrons_automation': opentrons_results if use_opentrons else None,
        'next_steps': 'Ready to start Analyze phase - update GP model and plan next cycle'
    }
    
    return {
        'response': {
            'actionGroup': event['actionGroup'],
            'function': event['function'],
            'functionResponse': {
                'responseBody': {
                    'TEXT': {
                        'body': json.dumps(response_body)
                    }
                }
            }
        }
    }

def execute_opentrons_automation(variant_list):
    """Execute Opentrons OT-2 automation via dedicated Lambda function"""
    try:
        # Prepare payload for Opentrons Lambda
        opentrons_payload = {
            'variant_list': variant_list,
            'protocol_type': 'spr_sample_prep',
            'concentrations': [100, 33.3, 11.1, 3.7, 1.2, 0.4]
        }
        
        # Invoke Opentrons Lambda function directly
        response = lambda_client.invoke(
            FunctionName='dmta-opentrons-simulator',
            InvocationType='RequestResponse',
            Payload=json.dumps(opentrons_payload)
        )
        
        # Parse response
        response_payload = json.loads(response['Payload'].read())
        
        if response_payload.get('statusCode') == 200:
            opentrons_data = response_payload['body']
            print(f"OT-2 automation completed: {opentrons_data['samples_prepared']} samples in {opentrons_data['execution_time_min']} minutes")
            return opentrons_data
        else:
            print(f"OT-2 automation failed: {response_payload}")
            return None
            
    except Exception as e:
        print(f"Error executing OT-2 automation: {str(e)}")
        return None

def generate_factorx_data(variant_list, assay_type, target_protein, qc_params, opentrons_results=None):
    """Generate realistic FactorX dummy data for expression and SPR binding assays"""
    results = []
    num_variants = len(variant_list) if variant_list else 8
    
    for i in range(num_variants):
        variant_id = variant_list[i].get('variant_id', f'VAR_01_{i+1:02d}') if variant_list else f'VAR_01_{i+1:02d}'
        
        # Expression phase simulation
        base_yield = 60 + random.gauss(0, 15)
        expression_yield = max(10, base_yield + (i * 5))  # Some variants express better
        
        # SPR binding simulation with realistic kinetics
        ka_base = 1.5e5 + random.gauss(0, 2e4)
        kd_base = 3e-4 + random.gauss(0, 5e-5)
        
        # Calculate KD from kinetics
        binding_kd_nm = (kd_base / ka_base) * 1e9
        binding_kd_nm = max(0.1, binding_kd_nm - (i * 0.2))  # Progressive improvement
        
        # Apply OT-2 precision improvement if available
        if opentrons_results and opentrons_results.get('simulation_success'):
            # Enhanced precision with OT-2 automation
            precision_factor = 0.3  # 70% reduction in measurement error
            binding_kd_nm *= (1 + random.gauss(0, 0.05 * precision_factor))  # Reduced noise
        
        # Quality assessment
        quality_factors = {
            'expression_quality': 1.0 if expression_yield > 30 else 0.7,
            'binding_specificity': 0.9 + random.gauss(0, 0.05),
            'stability_score': 0.85 + random.gauss(0, 0.1)
        }
        quality_score = statistics.mean(list(quality_factors.values()))
        
        result = {
            'variant_id': variant_id,
            'expression_data': {
                'yield_mg_per_l': Decimal(str(round(expression_yield, 1))),
                'purity_percent': Decimal(str(round(85 + random.gauss(0, 5), 1))),
                'aggregation_percent': Decimal(str(round(max(0, 5 + random.gauss(0, 2)), 1)))
            },
            'spr_binding_data': {
                'binding_kd_nm': Decimal(str(round(binding_kd_nm, 2))),
                'kinetics': {
                    'ka_per_m_per_s': Decimal(str(round(ka_base, 0))),
                    'kd_per_s': Decimal(str(round(kd_base, 6))),
                    'rmax_ru': Decimal(str(round(150 + random.gauss(0, 30), 1)))
                },
                'binding_response': generate_spr_curve(ka_base, kd_base, opentrons_results is not None)
            },
            'opentrons_data': {
                'automated_preparation': opentrons_results is not None,
                'sample_quality': 'enhanced' if opentrons_results else 'standard',
                'precision_improvement': 'Manual ±5% → OT-2 ±1.5%' if opentrons_results else 'Manual ±5%'
            },
            'quality_assessment': {
                'overall_score': Decimal(str(round(quality_score, 2))),
                'factors': {
                    'expression_quality': Decimal(str(quality_factors['expression_quality'])),
                    'binding_specificity': Decimal(str(quality_factors['binding_specificity'])),
                    'stability_score': Decimal(str(quality_factors['stability_score']))
                }
            },
            'timestamp': datetime.now().isoformat()
        }
        results.append(result)
    
    return results

def generate_spr_curve(ka, kd, ot2_enhanced=False):
    """Generate realistic SPR binding curve data"""
    concentrations = [0.1, 0.3, 1.0, 3.0, 10.0, 30.0]  # nM
    responses = []
    
    for conc in concentrations:
        # Steady-state binding response
        conc_m = conc * 1e-9
        response = (150 * conc_m) / (kd/ka + conc_m)  # Langmuir binding
        
        # Apply noise based on sample preparation method
        noise_factor = 0.015 if ot2_enhanced else 0.05  # Reduced noise with OT-2
        response += random.gauss(0, response * noise_factor)
        responses.append(round(max(0, response), 1))
    
    return {
        'concentrations_nm': concentrations,
        'responses_ru': responses,
        'r_squared': round((0.98 if ot2_enhanced else 0.95) + random.gauss(0, 0.02), 3),
        'sample_preparation': 'OT-2 automated' if ot2_enhanced else 'manual'
    }

def store_experimental_data(results, assay_type):
    """Store experimental results in DynamoDB and S3"""
    experiment_id = f'EXP_{datetime.now().strftime("%Y%m%d_%H%M%S")}'
    
    try:
        # Get the latest project by scanning the project table
        project_table = dynamodb.Table(os.environ['PROJECT_TABLE'])
        response = project_table.scan(
            ProjectionExpression='project_id',
            Limit=1
        )
        project_id = response['Items'][0]['project_id'] if response['Items'] else 'default-project'
        
        # Store results in DynamoDB
        variant_table = dynamodb.Table(os.environ['VARIANT_TABLE'])
        for result in results:
            experiment_data = {
                'project_id': project_id,
                'experiment_id': experiment_id,
                'variant_id': result['variant_id'],
                'assay_type': assay_type,
                'binding_kd_nm': result['spr_binding_data']['binding_kd_nm'],
                'expression_yield': result['expression_data']['yield_mg_per_l'],
                'quality_score': result['quality_assessment']['overall_score'],
                'timestamp': result['timestamp']
            }
            
            variant_table.put_item(Item=experiment_data)
            
        # Store detailed data in S3
        s3_key = f'projects/{project_id}/experiments/{experiment_id}/results.json'
        results_json = convert_decimals_to_float(results)
        s3.put_object(
            Bucket=os.environ['S3_BUCKET'],
            Key=s3_key,
            Body=json.dumps(results_json, indent=2)
        )
        
        print(f"Stored experimental data: {experiment_id}")
        
    except Exception as e:
        print(f"Error storing data: {str(e)}")
        raise e
    
    return experiment_id

def generate_assay_report(results, assay_type, target_protein):
    """Generate comprehensive assay report"""
    # Calculate summary statistics
    kd_values = [float(r['spr_binding_data']['binding_kd_nm']) for r in results]
    expression_yields = [float(r['expression_data']['yield_mg_per_l']) for r in results]
    
    report = {
        'assay_summary': {
            'assay_type': assay_type,
            'target_protein': target_protein,
            'variants_tested': len(results),
            'success_rate': len([r for r in results if float(r['expression_data']['yield_mg_per_l']) > 20]) / len(results)
        },
        'binding_statistics': {
            'best_kd_nm': round(min(kd_values), 2),
            'median_kd_nm': round(statistics.median(kd_values), 2),
            'kd_range': [round(min(kd_values), 2), round(max(kd_values), 2)]
        },
        'expression_statistics': {
            'mean_yield': round(statistics.mean(expression_yields), 1),
            'yield_range': [round(min(expression_yields), 1), round(max(expression_yields), 1)]
        },
        'assay_conditions': {
            'temperature': '25°C',
            'buffer': 'HBS-EP+ (10mM HEPES, 150mM NaCl, 3mM EDTA, 0.05% P20)',
            'flow_rate': '30 μL/min',
            'contact_time': '120 seconds',
            'dissociation_time': '300 seconds'
        }
    }
    
    return report

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

def convert_floats_to_decimals(obj):
    """Recursively convert float objects to Decimal for DynamoDB storage"""
    if isinstance(obj, list):
        return [convert_floats_to_decimals(item) for item in obj]
    elif isinstance(obj, dict):
        return {key: convert_floats_to_decimals(value) for key, value in obj.items()}
    elif isinstance(obj, float):
        return Decimal(str(obj))
    else:
        return obj
