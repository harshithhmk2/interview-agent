from typing import Any, Dict, List
import uuid
from pydantic import BaseModel, ConfigDict


class MatchDetails(BaseModel):
    """
    Sub-schema for candidate resume to job description matching results.
    """
    overall_percentage: float
    matched_skills: List[str]
    gaps_identified: List[str]
    recommended_topics_to_probe: List[str]


class ResumeUploadResponse(BaseModel):
    """
    Response validation schema returned after candidate resume parsing and alignment.
    """
    id: uuid.UUID
    candidate_name: str
    candidate_email: str
    parsed_attributes: Dict[str, Any]
    match_score: MatchDetails

    model_config = ConfigDict(from_attributes=True)


class CandidateApplicationResponse(BaseModel):
    """
    Validation schema returned to candidate applicants (isolating match details).
    """
    message: str
    id: uuid.UUID


class ResumeProceedRequest(BaseModel):
    """
    Validation schema for manually updating proceed recommendation status.
    """
    proceed_to_next_round: bool
