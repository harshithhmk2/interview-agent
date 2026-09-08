import uuid
from datetime import datetime
from typing import Optional, List
from sqlalchemy import String, ForeignKey, Float, Integer, Text, DateTime, JSON, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from src.db.base import Base


class User(Base):
    __tablename__ = "users"
    
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(50), default="candidate")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    job_descriptions: Mapped[List["JobDescription"]] = relationship(
        "JobDescription", back_populates="recruiter", cascade="all, delete-orphan"
    )
    audit_logs: Mapped[List["AuditLog"]] = relationship(
        "AuditLog", back_populates="user"
    )


class JobDescription(Base):
    __tablename__ = "job_descriptions"
    
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    recruiter_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    company_name: Mapped[str] = mapped_column(String(255), default="Implere Technologies")
    status: Mapped[str] = mapped_column(String(50), default="open")  # open, closed
    work_mode: Mapped[str] = mapped_column(String(50), default="onsite")  # onsite, remote, hybrid
    location: Mapped[str] = mapped_column(String(255), default="Bangalore")
    experience_range: Mapped[str] = mapped_column(String(100), default="3 - 5 Years")
    salary_range: Mapped[str] = mapped_column(String(100), default="₹ 15L - 18L / year")
    raw_text: Mapped[str] = mapped_column(Text, nullable=False)
    parsed_attributes: Mapped[dict] = mapped_column(JSON, nullable=False)  # Skills, requirements
    match_threshold: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    recruiter: Mapped["User"] = relationship("User", back_populates="job_descriptions")
    interviews: Mapped[List["Interview"]] = relationship(
        "Interview", back_populates="job_description", cascade="all, delete-orphan"
    )


class Resume(Base):
    __tablename__ = "resumes"
    
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    candidate_name: Mapped[str] = mapped_column(String(255), nullable=False)
    candidate_email: Mapped[str] = mapped_column(String(255), nullable=False)
    raw_text: Mapped[str] = mapped_column(Text, nullable=False)
    parsed_attributes: Mapped[dict] = mapped_column(JSON, nullable=False)  # Skills, experience
    job_description_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("job_descriptions.id", ondelete="CASCADE"), nullable=True
    )
    match_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    match_details: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    proceed_to_next_round: Mapped[Optional[bool]] = mapped_column(Boolean, default=False, nullable=True)
    questions_plan: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)  # Tailored pre-generated questions plan
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    interviews: Mapped[List["Interview"]] = relationship(
        "Interview", back_populates="resume", cascade="all, delete-orphan"
    )


class Interview(Base):
    __tablename__ = "interviews"
    
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    job_description_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("job_descriptions.id"), nullable=False)
    resume_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("resumes.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="scheduled")  # scheduled, active, completed, evaluated
    scheduled_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    job_description: Mapped["JobDescription"] = relationship("JobDescription", back_populates="interviews")
    resume: Mapped["Resume"] = relationship("Resume", back_populates="interviews")
    questions: Mapped[List["InterviewQuestion"]] = relationship(
        "InterviewQuestion", back_populates="interview", cascade="all, delete-orphan"
    )
    turns: Mapped[List["InterviewTurn"]] = relationship(
        "InterviewTurn", back_populates="interview", cascade="all, delete-orphan"
    )
    evaluation_report: Mapped[Optional["EvaluationReport"]] = relationship(
        "EvaluationReport", uselist=False, back_populates="interview", cascade="all, delete-orphan"
    )


class InterviewQuestion(Base):
    __tablename__ = "interview_questions"
    
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    interview_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("interviews.id"), nullable=False)
    sequence_order: Mapped[int] = mapped_column(Integer, nullable=False)
    topic: Mapped[str] = mapped_column(String(100), nullable=False)
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    expected_keywords: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    interview: Mapped["Interview"] = relationship("Interview", back_populates="questions")
    turns: Mapped[List["InterviewTurn"]] = relationship("InterviewTurn", back_populates="question")


class InterviewTurn(Base):
    __tablename__ = "interview_turns"
    
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    interview_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("interviews.id"), nullable=False)
    question_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("interview_questions.id"), nullable=False)
    turn_index: Mapped[int] = mapped_column(Integer, nullable=False)
    question_asked: Mapped[str] = mapped_column(Text, nullable=False)
    question_audio_path: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    response_transcript: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    response_audio_path: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    latency_seconds: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    turn_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    score_evidence: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    interview: Mapped["Interview"] = relationship("Interview", back_populates="turns")
    question: Mapped["InterviewQuestion"] = relationship("InterviewQuestion", back_populates="turns")


class EvaluationReport(Base):
    __tablename__ = "evaluation_reports"
    
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    interview_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("interviews.id"), unique=True, nullable=False)
    overall_score: Mapped[float] = mapped_column(Float, nullable=False)
    recommendation: Mapped[str] = mapped_column(String(50), nullable=False)  # hire, no_hire, follow_up
    primary_summary: Mapped[str] = mapped_column(Text, nullable=False)
    details: Mapped[dict] = mapped_column(JSON, nullable=False)  # Rubric score breakdown
    
    # Recruiter override / Human-in-the-Loop fields
    recruiter_override_recommendation: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    recruiter_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    reviewer_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("users.id"), nullable=True)
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    interview: Mapped["Interview"] = relationship("Interview", back_populates="evaluation_report")


class AuditLog(Base):
    __tablename__ = "audit_logs"
    
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("users.id"), nullable=True)
    action_type: Mapped[str] = mapped_column(String(100), nullable=False)  # DELETE_DATA, OVERRIDE_SCORE, LOGIN
    target_resource_type: Mapped[str] = mapped_column(String(100), nullable=False)
    target_resource_id: Mapped[Optional[uuid.UUID]] = mapped_column(nullable=True)
    action_metadata: Mapped[dict] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    user: Mapped["User"] = relationship("User", back_populates="audit_logs")
