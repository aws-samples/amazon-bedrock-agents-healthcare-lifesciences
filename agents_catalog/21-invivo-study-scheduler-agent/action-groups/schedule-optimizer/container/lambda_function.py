"""
Lambda function handler for the In Vivo Study Scheduler agent.
"""

import json
import os
from typing import Dict, Any, Optional

from aws_lambda_powertools import Logger
from aws_lambda_powertools.event_handler import BedrockAgentFunctionResolver
from aws_lambda_powertools.utilities.typing import LambdaContext

from optimizer import optimize_schedule

# Configure logging
log_level = os.environ.get("LOG_LEVEL", "INFO")
logger = Logger(service="invivo-study-scheduler", level=log_level)
app = BedrockAgentFunctionResolver()


@app.tool(
    name="optimizeSchedule",
    description="Optimize the schedule of in vivo studies over a 30-day period using constraint programming"
)
def optimize_schedule_tool(
    studies: str,
    max_animals_per_day: Optional[int] = 1000,
    optimization_objective: Optional[str] = "balance_animals"
) -> Dict[str, Any]:
    """
    Optimize the schedule of in vivo studies over a 30-day period.
    
    Args:
        studies: JSON string representing a list of studies to schedule
        max_animals_per_day: Maximum number of animals available per day
        optimization_objective: Primary optimization objective ('balance_animals' or 'balance_studies')
        
    Returns:
        Dictionary containing optimization results
    """
    try:
        logger.info("Optimizing schedule", extra={
            "studies": studies,
            "max_animals_per_day": max_animals_per_day,
            "optimization_objective": optimization_objective
        })
        
        # Parse studies JSON
        try:
            studies_list = json.loads(studies)
        except json.JSONDecodeError as e:
            logger.error("Invalid JSON format for studies parameter", extra={"error": str(e)})
            raise ValueError("Invalid JSON format for studies parameter")
        
        # Optimize the schedule
        optimization_result = optimize_schedule(
            studies=studies_list,
            max_animals_per_day=max_animals_per_day,
            optimization_objective=optimization_objective
        )
        
        # Prepare response
        response = {
            "status": "success",
            "optimization_result": optimization_result,
            "summary": f"Successfully optimized schedule for {len(studies_list)} studies with {optimization_objective} objective."
        }
        
        logger.info("Schedule optimization completed successfully", extra={
            "num_studies": len(studies_list)
        })
        
        return response
        
    except Exception as e:
        logger.error("Error in optimize_schedule_tool", extra={"error": str(e)})
        raise


@logger.inject_lambda_context
def lambda_handler(event: dict, context: LambdaContext):
    """
    Main Lambda handler using AWS Lambda Powertools BedrockAgentFunctionResolver.
    
    Args:
        event: Lambda event containing agent request
        context: Lambda context
        
    Returns:
        Response formatted for Bedrock
    """
    return app.resolve(event, context)
