from typing import Optional, List
from datetime import datetime
import uuid
from pydantic import BaseModel, ConfigDict


class SessionCreateRequest(BaseModel):
    """
    Payload required to schedule or initialize a new interview session.
    """
    job_description_id: uuid.UUID
    resume_id: uuid.UUID


class QuestionSchema(BaseModel):
    id: Optional[str] = None
    topic: str
    question_text: str
    expected_keywords: List[str] = []


class SessionResponse(BaseModel):
    """
    Schema representing basic info of a scheduled interview session.
    """
    id: uuid.UUID
    status: str
    scheduled_at: datetime
    first_question: Optional[str] = None
    questions: List[QuestionSchema] = []

    model_config = ConfigDict(from_attributes=True)


class TurnSubmissionRequest(BaseModel):
    """
    Payload for submitting candidate responses (speech-to-text or raw base64 audio).
    """
    response_text: Optional[str] = None
    response_audio_base64: Optional[str] = None
    latency_seconds: float


class TurnResponse(BaseModel):
    """
    Response returned to candidate with the next question and optional audio data.
    """
    next_question: str
    next_question_audio_base64: Optional[str] = None
    is_last: bool
