# Plan Project Enhancement - Document Generation and S3 Storage

## Enhanced Plan Project Action Group

### Purpose
Initial project setup with knowledge base consultation and structured project plan document generation

### Input Parameters
- `target_nanobody`: Starting nanobody (Cablivi/Caplacizumab)
- `optimization_objective`: vWF binding affinity improvement
- `target_value`: Target KD value (e.g., < 1 nM)
- `timeline_weeks`: Project timeline
- `knowledge_base_query`: Query for similar project plan templates

### Core Algorithm Enhancement

```python
def create_project_plan(nanobody, objective, target, timeline, kb_query):
    """
    Generate Cablivi optimization project plan with document generation
    """
    # 1. Query knowledge base for similar project plans
    kb_results = query_knowledge_base_documents(kb_query, "project_plan")
    similar_plans = extract_project_plan_templates(kb_results)
    
    # 2. Analyze current Cablivi performance
    baseline_analysis = analyze_baseline_performance(nanobody)
    
    # 3. Extract insights from similar project plans
    plan_insights = extract_plan_structure_insights(similar_plans)
    
    # 4. Generate project plan document
    project_plan_doc = generate_project_plan_document(
        nanobody, objective, target, timeline, plan_insights, baseline_analysis
    )
    
    # 5. Save project plan to S3
    project_id = generate_project_id()
    s3_key = f"projects/{project_id}/plans/project_plan.md"
    s3_url = save_document_to_s3(project_plan_doc, s3_key)
    
    # 6. Create project record in DynamoDB
    project_record = create_project_record(
        project_id, nanobody, objective, target, timeline, s3_url
    )
    
    return {
        'project_id': project_id,
        'project_plan_document': project_plan_doc,
        'project_plan_s3_url': s3_url,
        'knowledge_base_insights': kb_results,
        'baseline': baseline_analysis,
        'project_record': project_record
    }

def generate_project_plan_document(nanobody, objective, target, timeline, insights, baseline):
    """
    Generate structured project plan document based on KB templates
    """
    template = select_best_template(insights)
    
    plan_document = f"""
# DMTA Optimization Project Plan

## Project Overview
- **Target**: {nanobody} (Caplacizumab)
- **Objective**: {objective}
- **Target KD**: < {target} nM
- **Baseline KD**: {baseline['current_kd']} nM
- **Timeline**: {timeline} weeks

## Knowledge Base Insights
{format_kb_insights(insights)}

## Optimization Strategy
{generate_strategy_section(template, objective)}

## DMTA Cycle Plan
{generate_cycle_plan_section(template, timeline)}

## Resource Requirements
{generate_resource_section(template, timeline)}

## Risk Assessment
{generate_risk_section(template, insights)}

## Success Criteria
{generate_success_criteria(target, baseline)}
    """
    
    return plan_document
```

### Knowledge Base Integration
- Search for similar nanobody optimization project plans
- Extract project plan templates and structures
- Identify successful planning approaches
- Reference best practices from historical plans

### S3 Document Storage
- Generate structured project plan document
- Save to S3 with organized folder structure
- Return S3 URL for document access
- Link document to project record in DynamoDB

### Enhanced S3 Structure

```
dmta-experimental-data/
├── projects/
│   └── {project_id}/
│       ├── plans/
│       │   ├── project_plan.md          # Generated project plan document
│       │   ├── project_plan.pdf         # PDF version (optional)
│       │   └── knowledge_base_refs.json # KB references used
│       └── cycles/...
├── knowledge_base/
│   ├── project_plans/
│   │   ├── nanobody_opt_template_001.md
│   │   ├── nanobody_opt_template_002.md
│   │   └── cablivi_precedent_001.md
│   └── best_practices/
└── templates/
    └── project_plan_templates/
```

### Output Format
- Generated project plan document (Markdown format)
- S3 URL for document access
- Knowledge base insights and template references
- Project record created in DynamoDB
- Structured planning framework for DMTA cycles

### Updated Requirements
- Generate structured project plan documents based on historical precedents
- Save project plan documents to S3 with organized folder structure
- Query knowledge base for similar nanobody optimization project plan templates