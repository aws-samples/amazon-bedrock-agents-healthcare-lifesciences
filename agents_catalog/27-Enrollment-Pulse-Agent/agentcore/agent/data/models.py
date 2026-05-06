"""
Data models for Veeva CTMS entities
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class Study(BaseModel):
    """Clinical study information"""
    study_number: str
    study_name: str
    phase: str
    indication: str
    target_enrollment: int
    enrollment_start_date: datetime
    enrollment_end_date: datetime
    status: str


class Site(BaseModel):
    """Clinical site information"""
    site_number: str
    site_name: str
    study_number: str
    target_enrollment: int
    site_activated_date: datetime
    status: str
    region: Optional[str] = None
    country: str = "US"


class Subject(BaseModel):
    """Subject enrollment information"""
    subject_id: str
    site_number: str
    study_number: str
    screen_date: datetime
    enrollment_date: Optional[datetime] = None
    randomization_date: Optional[datetime] = None
    status: str  # Active, Completed, Screen Failed, etc.
    screen_failure_reason: Optional[str] = None


class StudyTeamMember(BaseModel):
    """Study team member information"""
    member_id: str
    name: str
    role: str  # Study Manager, CRA, etc.
    study_number: str


class SiteTeamMember(BaseModel):
    """Site team member assignments"""
    member_id: str
    site_number: str
    study_number: str
    assignment_date: datetime
    role: str


class Milestone(BaseModel):
    """Study milestone tracking"""
    milestone_id: str
    study_number: str
    milestone_name: str
    planned_date: datetime
    actual_date: Optional[datetime] = None
    status: str
    target_value: Optional[int] = None
    actual_value: Optional[int] = None


class EnrollmentMetric(BaseModel):
    """Monthly enrollment metrics by site"""
    site_number: str
    study_number: str
    month: str  # YYYY-MM format
    enrolled_count: int
    screened_count: int
    screen_failed_count: int
    randomized_count: int


class EnrollmentSummary(BaseModel):
    """Calculated enrollment summary for analysis"""
    site_number: str
    site_name: str
    target_enrollment: int
    current_enrollment: int
    enrollment_percentage: float
    screen_failure_rate: float
    avg_monthly_enrollment: float
    days_since_activation: int
    projected_final_enrollment: Optional[int] = None
    risk_level: str = "Low"  # Low, Medium, High


class HistoricalPerformance(BaseModel):
    """Historical performance data for a site"""
    site_number: str
    site_name: str
    month: str  # YYYY-MM format
    enrollment_count: int
    cumulative_enrollment: int
    enrollment_rate: float  # subjects per month
    screen_failure_rate: float
    performance_trend: str  # "Improving", "Declining", "Stable"


class AlternativeSiteRecommendation(BaseModel):
    """Alternative site recommendation"""
    recommended_site_number: str
    recommended_site_name: str
    reason: str
    historical_performance_score: float
    geographic_proximity: str
    capacity_availability: str
    success_probability: float