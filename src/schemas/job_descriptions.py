from typing import Any, Dict, Optional
from datetime import datetime
import uuid
from pydantic import BaseModel, Field, ConfigDict


class JobDescriptionCreate(BaseModel):
    """
    Validation schema for creating a new job description.
    """
    title: str = Field(..., json_schema_extra={"example": "Python Developer"})
    company_name: Optional[str] = Field(default="Implere Technologies", description="Company name posting the job")
    status: Optional[str] = Field(default="open", description="Application status: open or closed")
    work_mode: Optional[str] = Field(default="onsite", description="Mode of work: onsite, remote, or hybrid")
    location: Optional[str] = Field(default="Bangalore", description="Job location")
    experience_range: Optional[str] = Field(default="3 - 5 Years", description="Required experience range")
    salary_range: Optional[str] = Field(default="₹ 15L - 18L / year", description="Salary range")
    raw_text: str = Field(..., description="Complete copy-paste of the Job Description")
    match_threshold: Optional[float] = Field(default=None, description="Optional custom minimum match threshold override")


class JobDescriptionResponse(BaseModel):
    """
    Response schema returning details of a job description, including
    attributes parsed by the LLM (e.g. key skills, required experience).
    """
    id: uuid.UUID
    title: str
    company_name: str = "Implere Technologies"
    status: str = "open"
    work_mode: str = "onsite"
    location: str = "Bangalore"
    experience_range: str = "3 - 5 Years"
    salary_range: str = "₹ 15L - 18L / year"
    raw_text: str
    parsed_attributes: Dict[str, Any] = Field(
        ..., description="Extracted core requirements and nice-to-haves"
    )
    match_threshold: Optional[float] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
