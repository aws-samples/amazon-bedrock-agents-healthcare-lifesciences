import json
import uuid
import boto3
import os
import traceback
from datetime import datetime
from decimal import Decimal

# Initialize AWS clients
s3 = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')

def validate_environment():
    """Validate required environment variables"""
    required_vars = ['PROJECT_TABLE', 'S3_BUCKET']
    missing_vars = [var for var in required_vars if not os.environ.get(var)]
    if missing_vars:
        raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")

def lambda_handler(event, context):
    """Handle plan_project function"""
    try:
        print(f"Received event: {json.dumps(event)}")
        
        # Validate environment variables
        validate_environment()
        
        # Extract parameters from the event
        parameters = event.get('parameters', [])
        param_dict = {param['name']: param['value'] for param in parameters}
        
        target_nanobody = param_dict.get('target_nanobody', 'Cablivi')
        optimization_objective = param_dict.get('optimization_objective', 'Improve vWF binding affinity')
        target_kd = float(param_dict.get('target_kd', 1.0))
        timeline_weeks = int(param_dict.get('timeline_weeks', 8))
        knowledge_base_query = param_dict.get('knowledge_base_query', '')
        
        project_id = str(uuid.uuid4())
        
        # Query knowledge base for similar experiments
        knowledge_insights = query_knowledge_base(knowledge_base_query, target_nanobody, timeline_weeks)
        
        # Create project plan
        project_plan = {
            'project_id': project_id,
            'target_nanobody': target_nanobody,
            'optimization_objective': optimization_objective,
            'target_kd_nm': Decimal(str(target_kd)),
            'timeline_weeks': timeline_weeks,
            'status': 'planned',
            'created_at': datetime.now().isoformat(),
            'active_learning_strategy': 'Expected Improvement (EI)',
            'initial_sequence': 'QVQLVESGGGLVQPGGSLRLSCAASGFTFSSYAMSWVRQAPGKGLEWVSAISGSGGSTYYADSVKGRFTISRDNSKNTLYLQMNSLRAEDTAVYYCAKVSYLSTASSLDYWGQGTLVTVSS',
            'cycles_planned': 3,
            'variants_per_cycle': 8,
            'knowledge_insights': knowledge_insights
        }
        
        # Store project in DynamoDB
        try:
            table = dynamodb.Table(os.environ['PROJECT_TABLE'])
            table.put_item(Item=project_plan)
            print(f"Project stored in DynamoDB: {project_id}")
        except Exception as e:
            print(f"Error storing project in DynamoDB: {str(e)}")
            print(f"Traceback: {traceback.format_exc()}")
            raise e
        
        # Convert all Decimal values to float for JSON serialization
        project_plan_json = convert_decimals_to_float(project_plan)
        knowledge_insights_json = convert_decimals_to_float(knowledge_insights)
        
        # Store project plan document in S3 as Markdown
        try:
            s3_key = f'projects/{project_id}/project_plan.md'
            project_document = generate_project_markdown(project_plan_json, knowledge_insights_json)
            
            s3.put_object(
                Bucket=os.environ['S3_BUCKET'],
                Key=s3_key,
                Body=project_document,
                ContentType='text/markdown'
            )
            print(f"Project plan document saved to S3: {s3_key}")
        except Exception as e:
            print(f"Error saving project document: {str(e)}")
            print(f"Traceback: {traceback.format_exc()}")
            raise e
        
        response_body = {
            'message': f'DMTA project planned successfully for {target_nanobody} optimization',
            'project_plan': project_plan_json,
            'knowledge_insights': knowledge_insights_json,
            'next_steps': 'Ready to start Design phase - generate nanobody variants using active learning'
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
    except Exception as e:
        print(f"Error in lambda_handler: {str(e)}")
        print(f"Traceback: {traceback.format_exc()}")
        raise e

def query_knowledge_base(query, target_nanobody, timeline_weeks):
    """Query knowledge base for similar nanobody optimization project plans"""
    # Simulate knowledge base search for similar DMTA project plans
    similar_projects = [
        {
            'project_id': 'PROJ_2023_001',
            'title': 'Anti-TNF Nanobody Optimization for Adalimumab Biosimilar',
            'target': 'TNF-α binding',
            'objective': 'Improve binding affinity and reduce immunogenicity',
            'timeline_weeks': 10,
            'cycles_completed': 4,
            'final_kd_nm': Decimal('0.3'),
            'success_factors': [
                'CDR3 loop engineering was most effective',
                'Expected Improvement acquisition function optimal for initial cycles',
                'Framework mutations improved stability without affecting binding'
            ],
            'methodology': {
                'acquisition_strategy': 'EI for exploration, UCB for exploitation',
                'variants_per_cycle': 8,
                'convergence_criteria': 'KD < 0.5 nM or model uncertainty < 0.1'
            }
        },
        {
            'project_id': 'PROJ_2023_015',
            'title': 'vWF A1 Domain Nanobody Development',
            'target': 'von Willebrand Factor A1 domain',
            'objective': 'Develop high-affinity nanobody for thrombotic disorders',
            'timeline_weeks': 8,
            'cycles_completed': 3,
            'final_kd_nm': Decimal('0.8'),
            'success_factors': [
                'Targeted CDR1 and CDR3 mutations most effective',
                'SPR assays with HBS-EP+ buffer provided consistent results',
                'Expression yield monitoring prevented stability issues'
            ],
            'methodology': {
                'acquisition_strategy': 'Balanced EI/UCB approach',
                'variants_per_cycle': 6,
                'convergence_criteria': 'Target KD achieved or 3 consecutive cycles without improvement'
            }
        },
        {
            'project_id': 'PROJ_2022_087',
            'title': 'Caplacizumab Affinity Enhancement Project',
            'target': 'vWF A1 domain binding optimization',
            'objective': 'Enhance Caplacizumab binding affinity for improved efficacy',
            'timeline_weeks': 12,
            'cycles_completed': 5,
            'final_kd_nm': Decimal('0.4'),
            'success_factors': [
                'Multi-point mutations in CDR3 achieved breakthrough',
                'Active learning reduced experimental burden by 40%',
                'Gaussian Process model accuracy improved with each cycle'
            ],
            'methodology': {
                'acquisition_strategy': 'Adaptive EI with increasing exploitation',
                'variants_per_cycle': 10,
                'convergence_criteria': 'KD < 0.5 nM and model confidence > 0.9'
            }
        }
    ]
    
    # Select most relevant project based on target similarity
    most_relevant = similar_projects[2] if 'caplacizumab' in target_nanobody.lower() else similar_projects[1]
    
    # Extract insights from similar projects
    insights = {
        'similar_projects': similar_projects,
        'most_relevant_project': most_relevant,
        'recommended_methodology': {
            'acquisition_strategy': most_relevant['methodology']['acquisition_strategy'],
            'variants_per_cycle': most_relevant['methodology']['variants_per_cycle'],
            'estimated_cycles': max(3, min(5, most_relevant['cycles_completed'])),
            'convergence_criteria': most_relevant['methodology']['convergence_criteria']
        },
        'best_practices': [
            'Focus mutations on CDR1 and CDR3 regions based on successful precedents',
            'Use Expected Improvement acquisition function for initial exploration',
            'Monitor expression yield - variants below 30 mg/L may have stability issues',
            'SPR assays: use HBS-EP+ buffer at 25°C for consistent results',
            'Update Gaussian Process model after each cycle for improved predictions'
        ],
        'risk_mitigation': [
            'Conservative mutation approach in early cycles to avoid expression failures',
            'Parallel expression systems if yield issues encountered',
            'Regular model validation against historical data'
        ],
        'estimated_timeline': f'{timeline_weeks} weeks (based on {most_relevant["project_id"]} precedent)',
        'success_probability': Decimal('0.85'),
        'expected_improvement': f'{((3.2 - float(most_relevant["final_kd_nm"])) / 3.2 * 100):.0f}% binding affinity improvement expected'
    }
    
    return insights

def generate_project_markdown(project_plan, knowledge_insights):
    """Generate comprehensive project plan document"""
    markdown = f"""# DMTA Optimization Project: {project_plan['target_nanobody']}

## Project Overview
- **Project ID**: {project_plan['project_id']}
- **Objective**: {project_plan['optimization_objective']}
- **Target KD**: {project_plan['target_kd_nm']} nM
- **Timeline**: {project_plan['timeline_weeks']} weeks
- **Status**: {project_plan['status']}
- **Created**: {project_plan['created_at']}

## Experimental Design
- **Strategy**: {project_plan['active_learning_strategy']}
- **Planned Cycles**: {project_plan['cycles_planned']}
- **Variants per Cycle**: {project_plan['variants_per_cycle']}
- **Initial Sequence**: `{project_plan['initial_sequence']}`

## Knowledge Base Insights
### Most Relevant Project
- **Project**: {knowledge_insights['most_relevant_project']['title']}
- **Target**: {knowledge_insights['most_relevant_project']['target']}
- **Timeline**: {knowledge_insights['most_relevant_project']['timeline_weeks']} weeks ({knowledge_insights['most_relevant_project']['cycles_completed']} cycles)
- **Final KD**: {knowledge_insights['most_relevant_project']['final_kd_nm']} nM
- **Key Success Factors**:
"""    
    for factor in knowledge_insights['most_relevant_project']['success_factors']:
        markdown += f"  - {factor}\n"
    
    markdown += f"""

### Similar Projects Database
"""    
    for proj in knowledge_insights['similar_projects']:
        markdown += f"""- **{proj['project_id']}**: {proj['title']}
  - Target: {proj['target']}
  - Result: {proj['final_kd_nm']} nM in {proj['cycles_completed']} cycles
"""
    
    markdown += f"""
### Recommended Methodology (Based on Knowledge Base)
- **Acquisition Strategy**: {knowledge_insights['recommended_methodology']['acquisition_strategy']}
- **Variants per Cycle**: {knowledge_insights['recommended_methodology']['variants_per_cycle']}
- **Estimated Cycles**: {knowledge_insights['recommended_methodology']['estimated_cycles']}
- **Convergence Criteria**: {knowledge_insights['recommended_methodology']['convergence_criteria']}

### Best Practices from Similar Projects
"""    
    for practice in knowledge_insights['best_practices']:
        markdown += f"- {practice}\n"
    
    markdown += f"""
### Risk Mitigation Strategies
"""    
    for risk in knowledge_insights['risk_mitigation']:
        markdown += f"- {risk}\n"
    
    markdown += f"""
### Success Metrics
- **Estimated Timeline**: {knowledge_insights['estimated_timeline']}
- **Success Probability**: {knowledge_insights['success_probability']*100:.0f}%
- **Expected Improvement**: {knowledge_insights['expected_improvement']}

## Methodology
### Phase 1: Design
- Generate nanobody variants using acquisition functions
- Target regions: CDR1, CDR3
- Mutation strategy: Targeted mutations in binding regions

### Phase 2: Make
- Expression system: E. coli or mammalian cells
- Purification: Protein A/G affinity chromatography
- Quality control: SDS-PAGE, SEC, dynamic light scattering

### Phase 3: Test
- **Assay**: SPR binding assays against vWF A1 domain
- **Conditions**: 25°C, HBS-EP+ buffer
- **Analysis**: Kinetic analysis using 1:1 Langmuir binding model

### Phase 4: Analyze
- Gaussian Process modeling and next cycle planning
- Convergence criteria: Target KD achieved or model uncertainty < 0.15

## Success Criteria
- **Primary**: Achieve binding affinity KD ≤ {project_plan['target_kd_nm']} nM
- **Secondary**: Maintain expression yield > 30 mg/L, preserve stability

## Timeline
"""    
    for cycle in range(1, project_plan['cycles_planned'] + 1):
        weeks_per_cycle = project_plan['timeline_weeks'] // project_plan['cycles_planned']
        start_week = (cycle - 1) * weeks_per_cycle + 1
        end_week = cycle * weeks_per_cycle
        markdown += f"""### Cycle {cycle} (Weeks {start_week}-{end_week})
- **Design**: Week {start_week}
- **Make**: Week {start_week + 1}
- **Test**: Week {start_week + 2}
- **Analyze**: Week {end_week}

"""
    
    return markdown

def generate_project_timeline(total_weeks, cycles_planned):
    """Generate detailed project timeline"""
    weeks_per_cycle = total_weeks // cycles_planned
    timeline = {
        'total_duration_weeks': total_weeks,
        'cycles': []
    }
    
    for cycle in range(1, cycles_planned + 1):
        start_week = (cycle - 1) * weeks_per_cycle + 1
        end_week = cycle * weeks_per_cycle
        
        cycle_timeline = {
            'cycle_number': cycle,
            'weeks': f'{start_week}-{end_week}',
            'phases': {
                'design': f'Week {start_week}',
                'make': f'Week {start_week + 1}',
                'test': f'Week {start_week + 2}',
                'analyze': f'Week {end_week}'
            },
            'deliverables': [
                f'{8} nanobody variants designed',
                'Expression and purification completed',
                'SPR binding data generated',
                'GP model updated and next cycle planned'
            ]
        }
        timeline['cycles'].append(cycle_timeline)
    
    return timeline

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
