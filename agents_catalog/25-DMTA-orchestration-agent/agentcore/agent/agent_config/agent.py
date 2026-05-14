import json
import uuid
import random
import statistics
import logging
from datetime import datetime
from decimal import Decimal
from typing import Optional

from strands import Agent, tool
from strands.models import BedrockModel

logger = logging.getLogger(__name__)

MODEL_ID = "us.anthropic.claude-sonnet-4-5-20250929-v1:0"

SYSTEM_PROMPT = """You are an expert nanobody engineer specializing in DMTA cycle orchestration for Cablivi (Caplacizumab) optimization. Help users plan, execute, and analyze iterative experimental cycles to improve vWF A1 domain binding affinity through active learning approaches.

You have access to the following tools:
- plan_project: Create initial project setup and active learning strategy
- design_variants: Generate nanobody variants using acquisition functions (EI/UCB)
- make_test: Execute expression and SPR binding assays with FactorX simulation
- analyze_results: Analyze results using Gaussian Process modeling and recommend next steps
- project_status: Get project status, progress information, and current phase

DMTA Workflow Process:
1. Begin by understanding the optimization objectives (improve vWF binding affinity for Cablivi)
2. Use plan_project to create initial project setup and active learning strategy
3. For each cycle, execute phases sequentially with user confirmation:
   - Use design_variants to select nanobody variants using acquisition functions
   - Use make_test to simulate expression and SPR binding assays with FactorX data
   - Use analyze_results to update Gaussian Process model and assess progress
4. Ask user permission before starting each phase: "Design phase completed. Would you like to start the Make phase?"
5. Continue cycles until convergence criteria met or optimal nanobody variants found
6. Provide final optimization summary with best candidates

Response Guidelines:
- Execute phases sequentially with user confirmation between each phase
- Provide clear phase completion messages
- Generate realistic FactorX dummy data for Make and Test phases
- Update Gaussian Process models with new experimental data
- Track optimization progress and convergence criteria
- Highlight best nanobody variants and binding improvements achieved
- Recommend next cycle strategies based on active learning principles
"""

# In-memory project store for local execution
_projects = {}
_cycles = {}
_variants = {}


@tool
def plan_project(
    target_nanobody: str,
    optimization_objective: str,
    target_kd: float = 1.0,
    timeline_weeks: int = 8,
) -> str:
    """Create initial Cablivi optimization project plan with active learning strategy.

    Args:
        target_nanobody: Starting nanobody (e.g. Cablivi/Caplacizumab).
        optimization_objective: vWF binding affinity improvement objective.
        target_kd: Target KD value in nM (default: 1.0).
        timeline_weeks: Project timeline in weeks (default: 8).
    """
    project_id = str(uuid.uuid4())

    knowledge_insights = {
        "most_relevant_project": {
            "title": "Caplacizumab Affinity Enhancement Project",
            "final_kd_nm": 0.4,
            "cycles_completed": 5,
            "success_factors": [
                "Multi-point mutations in CDR3 achieved breakthrough",
                "Active learning reduced experimental burden by 40%",
                "Gaussian Process model accuracy improved with each cycle",
            ],
        },
        "recommended_methodology": {
            "acquisition_strategy": "Adaptive EI with increasing exploitation",
            "variants_per_cycle": 8,
            "estimated_cycles": 3,
            "convergence_criteria": "KD < target or model confidence > 0.9",
        },
        "best_practices": [
            "Focus mutations on CDR1 and CDR3 regions",
            "Use Expected Improvement for initial exploration",
            "Monitor expression yield - variants below 30 mg/L may have stability issues",
            "SPR assays: use HBS-EP+ buffer at 25°C for consistent results",
        ],
    }

    project_plan = {
        "project_id": project_id,
        "target_nanobody": target_nanobody,
        "optimization_objective": optimization_objective,
        "target_kd_nm": target_kd,
        "timeline_weeks": timeline_weeks,
        "status": "planned",
        "created_at": datetime.now().isoformat(),
        "active_learning_strategy": "Expected Improvement (EI)",
        "initial_sequence": "QVQLVESGGGLVQPGGSLRLSCAASGFTFSSYAMSWVRQAPGKGLEWVSAISGSGGSTYYADSVKGRFTISRDNSKNTLYLQMNSLRAEDTAVYYCAKVSYLSTASSLDYWGQGTLVTVSS",
        "cycles_planned": 3,
        "variants_per_cycle": 8,
    }

    _projects[project_id] = project_plan

    return json.dumps({
        "message": f"DMTA project planned successfully for {target_nanobody} optimization",
        "project_plan": project_plan,
        "knowledge_insights": knowledge_insights,
        "next_steps": "Ready to start Design phase - generate nanobody variants using active learning",
    })


@tool
def design_variants(
    parent_nanobody: str,
    cycle_number: int,
    acquisition_function: str = "Expected Improvement",
    num_variants: int = 8,
    previous_results: str = "{}",
) -> str:
    """Generate nanobody variants using active learning acquisition functions.

    Args:
        parent_nanobody: Base nanobody sequence.
        cycle_number: Current DMTA cycle number.
        acquisition_function: Active learning strategy (Expected Improvement or UCB).
        num_variants: Number of variants to generate (default: 8).
        previous_results: Historical binding data for GP model as JSON string.
    """
    # Update GP model
    model_accuracy = round(0.85 + (cycle_number * 0.02), 3)
    uncertainty = round(max(0.1, 0.3 - (cycle_number * 0.05)), 3)

    gp_model = {
        "cycle": cycle_number,
        "model_accuracy": model_accuracy,
        "uncertainty_estimate": uncertainty,
        "hyperparameters": {
            "length_scale": 1.2,
            "signal_variance": 0.8,
            "noise_variance": 0.1,
        },
    }

    # Generate variants
    mutation_positions = [48, 50, 52, 99, 101, 103]
    amino_acids = ["A", "V", "L", "I", "F", "Y", "W", "S", "T", "N", "Q"]
    variants = []

    for i in range(num_variants):
        mutations = []
        selected_positions = random.sample(mutation_positions, 2)
        for pos in selected_positions:
            original = "A" if pos < 60 else "S"
            new_aa = random.choice([aa for aa in amino_acids if aa != original])
            mutations.append(f"{original}{pos}{new_aa}")

        if acquisition_function == "Expected Improvement":
            score = max(0.1, 0.9 - (i * 0.08) + uncertainty * 0.3 + random.gauss(0, 0.05))
        else:
            score = max(0.1, 0.8 - (i * 0.06) + uncertainty * 1.96 + random.gauss(0, 0.03))

        variant = {
            "variant_id": f"VAR_{cycle_number}_{i+1:02d}",
            "mutations": mutations,
            "predicted_affinity_kd_nm": round(2.5 - (i * 0.15) + random.gauss(0, 0.1), 2),
            "acquisition_score": round(score, 3),
            "acquisition_function": acquisition_function,
        }
        variants.append(variant)

    variants.sort(key=lambda x: x["acquisition_score"], reverse=True)

    # Store variants
    for v in variants:
        _variants[v["variant_id"]] = v

    return json.dumps({
        "message": f"Generated {num_variants} nanobody variants for cycle {cycle_number} using {acquisition_function}",
        "variants": variants,
        "gp_model_stats": gp_model,
        "next_steps": "Ready to start Make-Test phase - express and assay variants",
    })


@tool
def make_test(
    variant_list: str,
    assay_type: str = "SPR binding assay",
    target_protein: str = "vWF A1 domain",
) -> str:
    """Execute nanobody expression and SPR binding assays with FactorX simulation.

    Args:
        variant_list: Comma-separated variant IDs or JSON array of variants to express and test.
        assay_type: SPR binding assay configuration.
        target_protein: Target protein (default: vWF A1 domain).
    """
    # Parse variant list
    try:
        ids = json.loads(variant_list)
    except (json.JSONDecodeError, TypeError):
        ids = [v.strip() for v in variant_list.strip("[]").split(",") if v.strip()]

    results = []
    for i, vid in enumerate(ids):
        variant_id = vid if isinstance(vid, str) else vid.get("variant_id", f"VAR_01_{i+1:02d}")

        expression_yield = max(10, 60 + random.gauss(0, 15) + (i * 5))
        ka = 1.5e5 + random.gauss(0, 2e4)
        kd_off = 3e-4 + random.gauss(0, 5e-5)
        binding_kd_nm = max(0.1, (kd_off / ka) * 1e9 - (i * 0.2))

        quality_score = round(
            statistics.mean([
                1.0 if expression_yield > 30 else 0.7,
                0.9 + random.gauss(0, 0.05),
                0.85 + random.gauss(0, 0.1),
            ]), 2
        )

        results.append({
            "variant_id": variant_id,
            "expression_yield_mg_per_l": round(expression_yield, 1),
            "purity_percent": round(85 + random.gauss(0, 5), 1),
            "binding_kd_nm": round(binding_kd_nm, 2),
            "ka_per_m_per_s": round(ka, 0),
            "kd_per_s": round(kd_off, 6),
            "quality_score": quality_score,
        })

    kd_values = [r["binding_kd_nm"] for r in results]
    yields = [r["expression_yield_mg_per_l"] for r in results]

    report = {
        "assay_type": assay_type,
        "target_protein": target_protein,
        "variants_tested": len(results),
        "best_kd_nm": round(min(kd_values), 2),
        "median_kd_nm": round(statistics.median(kd_values), 2),
        "mean_yield_mg_per_l": round(statistics.mean(yields), 1),
        "conditions": "25°C, HBS-EP+ buffer, 30 μL/min",
    }

    return json.dumps({
        "message": f"Completed {assay_type} for {len(results)} variants against {target_protein}",
        "experimental_results": results,
        "assay_report": report,
        "next_steps": "Ready to start Analyze phase - update GP model and plan next cycle",
    })


@tool
def analyze_results(
    binding_data: str,
    cycle_number: int,
    target_kd: float = 1.0,
) -> str:
    """Analyze SPR binding results using Gaussian Process modeling and recommend next cycle strategy.

    Args:
        binding_data: SPR binding results from make-test phase as JSON string.
        cycle_number: Current cycle number.
        target_kd: Target binding affinity KD value in nM.
    """
    try:
        data = json.loads(binding_data)
    except (json.JSONDecodeError, TypeError):
        data = {}

    # Extract KD values
    kd_values = []
    if isinstance(data, list):
        kd_values = [float(r.get("binding_kd_nm", 2.5)) for r in data]
    elif isinstance(data, dict):
        for v in data.values():
            if isinstance(v, dict) and "binding_kd_nm" in v:
                kd_values.append(float(v["binding_kd_nm"]))
            elif isinstance(v, (int, float)):
                kd_values.append(float(v))

    if not kd_values:
        kd_values = [2.5 - i * 0.3 for i in range(8)]

    best_kd = min(kd_values)
    improvement_factor = round(2.8 / best_kd, 2) if best_kd > 0 else 1.0
    target_progress = round(min(100, (target_kd / best_kd) * 100), 1) if best_kd > 0 else 0

    # GP model update
    model_accuracy = round(0.75 + min(0.15, cycle_number * 0.03), 3)
    uncertainty = round(max(0.1, 0.4 - cycle_number * 0.05), 3)

    # Convergence assessment
    target_met = best_kd <= target_kd
    converged = uncertainty < 0.15
    continue_optimization = not target_met and not converged and cycle_number < 6

    if continue_optimization:
        if uncertainty > 0.25:
            next_strategy = "Exploration-focused (UCB with high beta)"
            acq_fn = "UCB"
        elif target_progress > 80:
            next_strategy = "Exploitation-focused (EI with low xi)"
            acq_fn = "Expected Improvement"
        else:
            next_strategy = "Balanced exploration-exploitation (EI)"
            acq_fn = "Expected Improvement"
    else:
        next_strategy = "Optimization complete"
        acq_fn = None

    analysis = {
        "cycle_number": cycle_number,
        "binding_summary": {
            "best_kd_nm": round(best_kd, 2),
            "median_kd_nm": round(statistics.median(kd_values), 2),
            "mean_kd_nm": round(statistics.mean(kd_values), 2),
            "variants_meeting_target": len([k for k in kd_values if k <= target_kd]),
        },
        "improvement_metrics": {
            "improvement_factor": improvement_factor,
            "target_progress_percent": target_progress,
        },
        "gp_model": {
            "accuracy_r2": model_accuracy,
            "uncertainty": uncertainty,
            "feature_importance": {"cdr1": 0.35, "cdr2": 0.15, "cdr3": 0.40, "framework": 0.10},
        },
        "recommendations": {
            "continue_optimization": continue_optimization,
            "termination_reason": "Target achieved" if target_met else ("Converged" if converged else None),
            "next_strategy": next_strategy,
            "acquisition_function": acq_fn,
            "recommended_variants": 8 if uncertainty > 0.2 else 6,
            "focus_regions": ["CDR1", "CDR3"],
        },
    }

    next_steps = (
        f"Ready to start DMTA cycle {cycle_number + 1} - {next_strategy}"
        if continue_optimization
        else "Optimization complete - target achieved or convergence criteria met"
    )

    return json.dumps({
        "message": f"Analysis completed for cycle {cycle_number}",
        "analysis_results": analysis,
        "next_steps": next_steps,
    })


@tool
def project_status(
    query_type: str = "all_projects",
    project_id: str = "",
) -> str:
    """Get project status, progress, and current phase information.

    Args:
        query_type: Type of query: project_count, project_progress, or all_projects.
        project_id: Specific project ID (optional, uses first project if not provided).
    """
    if query_type == "project_count":
        return json.dumps({"total_projects": len(_projects)})

    if query_type == "project_progress":
        pid = project_id or (next(iter(_projects)) if _projects else "")
        project = _projects.get(pid, {})
        project_variants = [v for v in _variants.values() if True]
        cycles_done = len(set(v.get("variant_id", "").split("_")[1] for v in project_variants if "_" in v.get("variant_id", "")))
        return json.dumps({
            "project_id": pid,
            "status": project.get("status", "unknown"),
            "cycles_completed": cycles_done,
            "variants_generated": len(project_variants),
        })

    # all_projects
    projects_summary = []
    for pid, proj in _projects.items():
        projects_summary.append({
            "project_id": pid,
            "target_nanobody": proj.get("target_nanobody"),
            "status": proj.get("status"),
            "created_at": proj.get("created_at"),
        })
    return json.dumps({"total_projects": len(_projects), "projects": projects_summary})


def create_agent() -> Agent:
    """Create and return the DMTA Orchestration agent."""
    model = BedrockModel(model_id=MODEL_ID, streaming=True)
    return Agent(
        model=model,
        system_prompt=SYSTEM_PROMPT,
        tools=[plan_project, design_variants, make_test, analyze_results, project_status],
    )
