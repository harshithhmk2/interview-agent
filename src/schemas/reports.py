from typing import Dict, Optional, List
from datetime import datetime
import uuid
from pydantic import BaseModel, Field, ConfigDict


class ReportOverrideRequest(BaseModel):
    """
    Schema for updating or overriding AI recommendation outputs by a recruiter.
    """
    recruiter_override_recommendation: str = Field(..., pattern="^(hire|no_hire|follow_up)$")
    recruiter_notes: str = Field(..., min_length=10)


class CategoryScore(BaseModel):
    """
    Schema showing quantitative score and evidence citation for an interview category/topic.
    """
    score: float = Field(..., ge=0, le=10)
    evidence: str = Field(..., description="Specific transcript citations justifying the score")


class ReportResponse(BaseModel):
    """
    Validation schema representing a candidate's complete evaluation report.
    """
    id: uuid.UUID
    interview_id: uuid.UUID
    overall_score: float
    recommendation: str
    primary_summary: str
    details: Dict[str, CategoryScore]
    recruiter_override_recommendation: Optional[str] = None
    recruiter_notes: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    transcript: Optional[List[dict]] = None
    evidence: Optional[dict] = None

    model_config = ConfigDict(from_attributes=True)


class ReportListItem(BaseModel):
    """
    Rubric item detail including candidate context profile parameters.
    """
    id: uuid.UUID
    interview_id: uuid.UUID
    overall_score: float
    recommendation: str
    primary_summary: str
    details: Dict[str, CategoryScore]
    recruiter_override_recommendation: Optional[str] = None
    recruiter_notes: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    candidate_name: str
    candidate_email: str
    job_title: str
    created_at: datetime
    transcript: Optional[List[dict]] = None
    evidence: Optional[dict] = None

    model_config = ConfigDict(from_attributes=True)


class PaginatedReportListResponse(BaseModel):
    """
    Paginated wrapping layout for report metrics list.
    """
    reports: List[ReportListItem]
    total_count: int
    page: int
    limit: int


class MockReportCreate(BaseModel):
    """
    Validation schema for creating a mock voice evaluation report.
    """
    resume_id: uuid.UUID
    job_id: uuid.UUID
