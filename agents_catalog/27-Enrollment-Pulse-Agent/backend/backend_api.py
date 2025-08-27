#!/usr/bin/env python3
"""
FastAPI Backend for Enrollment Pulse Agent
"""
from fastapi import FastAPI, HTTPException, Header, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, List, Optional
import sys
import os
from pathlib import Path
import logging

# Add src to path
sys.path.append(str(Path(__file__).parent / 'src'))

from src.agent.enrollment_agent import query_agent
from src.data.processors import CTMSDataProcessor
from src.analysis.enrollment_metrics import EnrollmentAnalyzer

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# API Key for security
API_KEY = os.getenv('ENROLLMENT_API_KEY', 'enrollment-pulse-secure-key-2025')

def verify_api_key(x_api_key: str = Header(None)):
    """Verify API key from header"""
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return x_api_key

# FastAPI app
app = FastAPI(
    title="Enrollment Pulse API",
    description="Clinical Trial Enrollment Optimization Agent API",
    version="1.0.0"
)

# CORS middleware for Streamlit frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your Streamlit URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global data cache
_data_cache = {}
_analyzer_cache = None

def get_data():
    """Get processed CTMS data, using cache if available"""
    global _data_cache, _analyzer_cache
    
    if not _data_cache:
        logger.info("Loading CTMS data...")
        processor = CTMSDataProcessor()
        _data_cache = processor.process_all()
        
        # Create analyzer
        _analyzer_cache = EnrollmentAnalyzer(
            summaries=_data_cache['enrollment_summaries'],
            subjects=_data_cache['subjects'],
            sites=_data_cache['sites'],
            metrics=_data_cache.get('enrollment_metrics', [])
        )
        logger.info("Data loaded successfully")
    
    return _data_cache, _analyzer_cache

# Pydantic models for API requests/responses
class QueryRequest(BaseModel):
    question: str
    context: Optional[str] = None

class QueryResponse(BaseModel):
    answer: str
    success: bool
    error: Optional[str] = None

class OverallStatusResponse(BaseModel):
    total_target: int
    total_enrolled: int
    overall_percentage: float
    randomized_subjects: int
    screen_failed_subjects: int
    total_screened: int
    screen_failure_rate: float

class SitePerformance(BaseModel):
    site_number: str
    site_name: str
    enrollment_percentage: float
    current_enrollment: int
    target_enrollment: int
    risk_level: str
    avg_monthly_enrollment: float

class UnderperformingSite(BaseModel):
    site_number: str
    site_name: str
    current_percentage: float
    current_enrollment: int
    target_enrollment: int
    projected_final_enrollment: int
    shortfall: int
    risk_level: str
    days_remaining: int

class CRAPerformance(BaseModel):
    thomas_nguyen_sites: Dict
    amanda_garcia_sites: Dict
    performance_gap: float
    recommendation: str

# API Endpoints

@app.get("/")
async def root():
    """Health check endpoint"""
    return {"message": "Enrollment Pulse API is running", "status": "healthy"}

import uuid
import asyncio
from concurrent.futures import ThreadPoolExecutor

# Job storage (in production, use Redis/DynamoDB)
job_results = {}
executor = ThreadPoolExecutor(max_workers=3)

class AsyncQueryResponse(BaseModel):
    job_id: str
    status: str  # "processing", "completed", "failed"
    answer: Optional[str] = None
    error: Optional[str] = None

def process_query_sync(job_id: str, question: str):
    """Process query synchronously in background"""
    try:
        logger.info(f"Processing query {job_id}: {question}")
        response = query_agent(question)
        job_results[job_id] = {
            "status": "completed",
            "answer": str(response),
            "error": None
        }
    except Exception as e:
        logger.warning(f"Error processing query {job_id}: {str(e)}")
        job_results[job_id] = {
            "status": "failed",
            "answer": None,
            "error": str(e)
        }

@app.post("/query/async", response_model=AsyncQueryResponse)
async def query_agent_async(request: QueryRequest):
    """Start async query processing"""
    job_id = str(uuid.uuid4())
    job_results[job_id] = {"status": "processing", "answer": None, "error": None}
    
    # Start background processing
    executor.submit(process_query_sync, job_id, request.question)
    
    return AsyncQueryResponse(
        job_id=job_id,
        status="processing"
    )

@app.get("/query/{job_id}", response_model=AsyncQueryResponse)
async def get_query_result(job_id: str):
    """Get query result by job ID"""
    if job_id not in job_results:
        raise HTTPException(status_code=404, detail="Job not found")
    
    result = job_results[job_id]
    return AsyncQueryResponse(
        job_id=job_id,
        status=result["status"],
        answer=result["answer"],
        error=result["error"]
    )

@app.post("/query", response_model=QueryResponse)
async def query_agent_endpoint(request: QueryRequest):
    """Quick sync query with timeout handling"""
    try:
        # Try with 120-second timeout (Lambda has 15-minute max)
        response = await asyncio.wait_for(
            asyncio.get_event_loop().run_in_executor(
                executor, query_agent, request.question
            ),
            timeout=120.0
        )
        return QueryResponse(answer=str(response), success=True)
    
    except asyncio.TimeoutError:
        # Start async job for complex queries
        job_id = str(uuid.uuid4())
        job_results[job_id] = {"status": "processing", "answer": None, "error": None}
        executor.submit(process_query_sync, job_id, request.question)
        
        return QueryResponse(
            answer=f"Query is taking longer than expected. Check status at /query/{job_id}",
            success=True
        )
    
    except Exception as e:
        logger.warning(f"Error processing query: {str(e)}")
        return QueryResponse(answer="", success=False, error=str(e))

@app.get("/status/overall", response_model=OverallStatusResponse)
async def get_overall_status():
    """
    Get overall enrollment status for the trial
    """
    try:
        data, analyzer = get_data()
        status = analyzer.get_overall_enrollment_status()
        
        return OverallStatusResponse(**status)
    
    except Exception as e:
        logger.warning(f"Error getting overall status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/sites/performance", response_model=List[SitePerformance])
async def get_site_performance():
    """
    Get site performance rankings
    """
    try:
        data, analyzer = get_data()
        rankings = analyzer.get_site_performance_ranking()
        
        return [SitePerformance(**site) for site in rankings]
    
    except Exception as e:
        logger.warning(f"Error getting site performance: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/sites/underperforming", response_model=List[UnderperformingSite])
async def get_underperforming_sites(threshold: float = 60.0):
    """
    Get sites that are underperforming based on enrollment threshold
    """
    try:
        data, analyzer = get_data()
        underperforming = analyzer.identify_underperforming_sites(threshold)
        
        return [UnderperformingSite(**site) for site in underperforming]
    
    except Exception as e:
        logger.warning(f"Error getting underperforming sites: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/cra/performance", response_model=CRAPerformance)
async def get_cra_performance():
    """
    Get CRA performance analysis
    """
    try:
        data, analyzer = get_data()
        cra_analysis = analyzer.analyze_cra_performance()
        
        return CRAPerformance(**cra_analysis)
    
    except Exception as e:
        logger.warning(f"Error getting CRA performance: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/analytics/trends")
async def get_enrollment_trends():
    """
    Get monthly enrollment trends by region
    """
    try:
        data, analyzer = get_data()
        trends = analyzer.get_monthly_enrollment_trends()
        
        return {"trends": trends}
    
    except Exception as e:
        logger.warning(f"Error getting enrollment trends: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/analytics/screening-efficiency")
async def get_screening_efficiency():
    """
    Get screening efficiency metrics by site
    """
    try:
        data, analyzer = get_data()
        efficiency = analyzer.calculate_screening_efficiency()
        
        return {"screening_efficiency": efficiency}
    
    except Exception as e:
        logger.warning(f"Error getting screening efficiency: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/analytics/projections")
async def get_enrollment_projections():
    """
    Get enrollment projections based on current trends
    """
    try:
        data, analyzer = get_data()
        projections = analyzer.project_enrollment_timeline()
        
        return {"projections": projections}
    
    except Exception as e:
        logger.warning(f"Error getting enrollment projections: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/recommendations")
async def get_recommendations(site_number: Optional[str] = None):
    """
    Get intervention recommendations for underperforming sites
    """
    try:
        if site_number:
            question = f"What are your specific recommendations for improving enrollment at site {site_number}?"
        else:
            question = "What are your recommendations for improving overall enrollment performance?"
        
        response = query_agent(question)
        
        return {"recommendations": response}
    
    except Exception as e:
        logger.warning(f"Error getting recommendations: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Data refresh endpoint
@app.get("/analytics/historical-performance")
async def get_historical_performance():
    """
    Get historical performance trends for all sites
    """
    try:
        data, analyzer = get_data()
        historical_data = analyzer.get_historical_performance()
        
        return {"historical_performance": historical_data}
    
    except Exception as e:
        logger.warning(f"Error getting historical performance: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/sites/{site_number}/alternatives")
async def get_alternative_sites(site_number: str):
    """
    Get alternative site recommendations for an underperforming site
    """
    try:
        data, analyzer = get_data()
        alternatives = analyzer.get_alternative_site_recommendations(site_number)
        
        return {"alternative_sites": alternatives}
    
    except Exception as e:
        logger.warning(f"Error getting alternative sites: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/sites/comprehensive-analysis")
async def get_comprehensive_site_analysis_endpoint(site_number: Optional[str] = None):
    """
    Get comprehensive per-site analysis including performance, historical trends, and recommendations
    """
    try:
        # Import the tool function
        from src.agent.tools import get_comprehensive_site_analysis
        
        comprehensive_analysis = get_comprehensive_site_analysis(site_number)
        
        return {"comprehensive_analysis": comprehensive_analysis}
    
    except Exception as e:
        logger.warning(f"Error getting comprehensive site analysis: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/sites/underperforming-detailed")
async def get_underperforming_sites_detailed_endpoint(threshold: float = 60.0):
    """
    Get detailed analysis of underperforming sites with site-specific recommendations
    """
    try:
        # Import the tool function
        from src.agent.tools import get_underperforming_sites_detailed
        
        detailed_analysis = get_underperforming_sites_detailed(threshold)
        
        return {"underperforming_analysis": detailed_analysis}
    
    except Exception as e:
        logger.warning(f"Error getting detailed underperforming analysis: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/data/refresh")
async def refresh_data():
    """
    Refresh the cached CTMS data
    """
    try:
        global _data_cache, _analyzer_cache
        _data_cache = {}
        _analyzer_cache = None
        
        # Reload data
        get_data()
        
        return {"message": "Data refreshed successfully", "success": True}
    
    except Exception as e:
        logger.warning(f"Error refreshing data: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Live Clinical Trials API Endpoints
@app.get("/clinical-trials/search")
async def search_live_trials(
    condition: Optional[str] = None,
    intervention: Optional[str] = None,
    status: Optional[str] = None,
    phase: Optional[str] = None,
    sponsor_type: Optional[str] = None,
    country: Optional[str] = None,
    max_results: int = 50
):
    """
    Search live clinical trials from ClinicalTrials.gov API
    """
    try:
        from src.agent.live_clinical_trials_tools import search_live_clinical_trials
        
        result = search_live_clinical_trials(
            condition=condition,
            intervention=intervention,
            status=status,
            phase=phase,
            sponsor_type=sponsor_type,
            country=country,
            max_results=max_results
        )
        
        return result
    
    except Exception as e:
        logger.warning(f"Error searching live clinical trials: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/clinical-trials/competitive-landscape/{condition}")
async def get_competitive_landscape_endpoint(condition: str, max_studies: int = 500):
    """
    Analyze competitive landscape for a medical condition
    """
    try:
        from src.agent.live_clinical_trials_tools import analyze_live_competitive_landscape
        
        result = analyze_live_competitive_landscape(condition, max_studies)
        
        return result
    
    except Exception as e:
        logger.warning(f"Error analyzing competitive landscape: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/clinical-trials/recruiting-by-location")
async def find_recruiting_trials_endpoint(
    condition: str,
    country: Optional[str] = None,
    state: Optional[str] = None,
    city: Optional[str] = None
):
    """
    Find recruiting trials by geographic location
    """
    try:
        from src.agent.live_clinical_trials_tools import find_recruiting_trials_by_location
        
        result = find_recruiting_trials_by_location(
            condition=condition,
            country=country,
            state=state,
            city=city
        )
        
        return result
    
    except Exception as e:
        logger.warning(f"Error finding recruiting trials: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/clinical-trials/enrollment-trends/{condition}")
async def track_enrollment_trends_endpoint(condition: str, months_back: int = 12):
    """
    Track enrollment trends over time for a condition
    """
    try:
        from src.agent.live_clinical_trials_tools import track_enrollment_trends
        
        result = track_enrollment_trends(condition, months_back)
        
        return result
    
    except Exception as e:
        logger.warning(f"Error tracking enrollment trends: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/clinical-trials/{nct_id}")
async def get_live_trial_details_endpoint(nct_id: str):
    """
    Get detailed information for a specific clinical trial
    """
    try:
        from src.agent.live_clinical_trials_tools import get_live_trial_details
        
        result = get_live_trial_details(nct_id)
        
        return result
    
    except Exception as e:
        logger.warning(f"Error getting trial details: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)