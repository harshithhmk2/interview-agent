from fastapi import APIRouter, Depends, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func
from sqlalchemy.orm import selectinload
import uuid
from datetime import datetime
from typing import List

from src.core.database import get_db
from src.core.exceptions import NotFoundException, AuthException
from src.api.auth import get_current_user
from src.db.models import User, EvaluationReport, Interview, Resume, JobDescription, InterviewQuestion, InterviewTurn
from src.schemas.reports import ReportResponse, ReportOverrideRequest, PaginatedReportListResponse, ReportListItem, MockReportCreate

router = APIRouter(prefix="/reports", tags=["reports"])

@router.get("", response_model=PaginatedReportListResponse)
async def list_evaluation_reports(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role not in ["admin", "interviewer", "recruiter"]:
        raise AuthException("Access denied: Admin, interviewer or recruiter role required")
        
    count_stmt = select(func.count(EvaluationReport.id))
    count_res = await db.execute(count_stmt)
    total_count = count_res.scalar() or 0
    
    stmt = (
        select(EvaluationReport)
        .options(
            selectinload(EvaluationReport.interview).selectinload(Interview.resume),
            selectinload(EvaluationReport.interview).selectinload(Interview.job_description),
            selectinload(EvaluationReport.interview).selectinload(Interview.turns)
        )
        .order_by(EvaluationReport.created_at.desc())
        .offset((page - 1) * limit)
        .limit(limit)
    )
    result = await db.execute(stmt)
    reports = result.scalars().all()
    
    list_items = []
    for r in reports:
        candidate_name = r.interview.resume.candidate_name if r.interview and r.interview.resume else "Unknown"
        candidate_email = r.interview.resume.candidate_email if r.interview and r.interview.resume else "Unknown"
        job_title = r.interview.job_description.title if r.interview and r.interview.job_description else "Unknown"
        
        # Build transcript snippets from interview turns
        transcript = []
        if r.interview and r.interview.turns:
            sorted_turns = sorted(r.interview.turns, key=lambda t: t.turn_index)
            for t in sorted_turns:
                if t.question_asked:
                    transcript.append({
                        "speaker": "AI",
                        "text": t.question_asked,
                        "time": f"Turn {t.turn_index + 1}"
                    })
                if t.response_transcript:
                    transcript.append({
                        "speaker": "Candidate",
                        "text": t.response_transcript,
                        "time": f"Score: {t.turn_score or 0}/10",
                        "score": t.turn_score,
                        "evidence": t.score_evidence
                    })

        # Build evidence highlights and gaps from details
        highlights = []
        gaps = []
        if r.details and isinstance(r.details, dict):
            for cat, info in r.details.items():
                if isinstance(info, dict):
                    score = info.get("score", 0.0)
                    ev = info.get("evidence", "")
                    if score >= 7.0:
                        highlights.append(f"{cat}: {ev}")
                    else:
                        gaps.append(f"{cat}: {ev}")
        if not highlights:
            highlights = [r.primary_summary]
        if not gaps:
            gaps = ["No critical competency gaps identified during voice screening."]

        evidence_dict = {
            "highlights": highlights,
            "gaps": gaps
        }

        list_items.append(ReportListItem(
            id=r.id,
            interview_id=r.interview_id,
            overall_score=r.overall_score,
            recommendation=r.recommendation,
            primary_summary=r.primary_summary,
            details=r.details,
            recruiter_override_recommendation=r.recruiter_override_recommendation,
            recruiter_notes=r.recruiter_notes,
            reviewed_at=r.reviewed_at,
            candidate_name=candidate_name,
            candidate_email=candidate_email,
            job_title=job_title,
            created_at=r.created_at,
            transcript=transcript,
            evidence=evidence_dict
        ))
        
    return PaginatedReportListResponse(
        reports=list_items,
        total_count=total_count,
        page=page,
        limit=limit
    )

@router.get("/{interview_id}", response_model=ReportResponse)
async def get_evaluation_report(
    interview_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    stmt = (
        select(EvaluationReport)
        .options(
            selectinload(EvaluationReport.interview).selectinload(Interview.turns)
        )
        .filter(EvaluationReport.interview_id == interview_id)
    )
    result = await db.execute(stmt)
    report = result.scalars().first()
    if not report:
        raise NotFoundException("Evaluation Report not found")
        
    transcript = []
    if report.interview and report.interview.turns:
        sorted_turns = sorted(report.interview.turns, key=lambda t: t.turn_index)
        for t in sorted_turns:
            if t.question_asked:
                transcript.append({
                    "speaker": "AI",
                    "text": t.question_asked,
                    "time": f"Turn {t.turn_index + 1}"
                })
            if t.response_transcript:
                transcript.append({
                    "speaker": "Candidate",
                    "text": t.response_transcript,
                    "time": f"Score: {t.turn_score or 0}/10",
                    "score": t.turn_score,
                    "evidence": t.score_evidence
                })

    highlights = []
    gaps = []
    if report.details and isinstance(report.details, dict):
        for cat, info in report.details.items():
            if isinstance(info, dict):
                score = info.get("score", 0.0)
                ev = info.get("evidence", "")
                if score >= 7.0:
                    highlights.append(f"{cat}: {ev}")
                else:
                    gaps.append(f"{cat}: {ev}")
    if not highlights:
        highlights = [report.primary_summary]
    if not gaps:
        gaps = ["No critical competency gaps identified during voice screening."]

    evidence_dict = {
        "highlights": highlights,
        "gaps": gaps
    }

    resp = ReportResponse.model_validate(report)
    resp.transcript = transcript
    resp.evidence = evidence_dict
    return resp

@router.patch("/{interview_id}/override", response_model=ReportResponse)
async def override_report(
    interview_id: uuid.UUID,
    payload: ReportOverrideRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    stmt = select(EvaluationReport).filter(EvaluationReport.interview_id == interview_id)
    result = await db.execute(stmt)
    report = result.scalars().first()
    if not report:
        raise NotFoundException("Evaluation Report not found")

    report.recruiter_override_recommendation = payload.recruiter_override_recommendation
    report.recruiter_notes = payload.recruiter_notes
    report.reviewer_id = current_user.id
    report.reviewed_at = datetime.utcnow()

    await db.commit()
    await db.refresh(report)
    return report

@router.post("/mock", response_model=ReportResponse, status_code=status.HTTP_201_CREATED)
async def create_mock_report(
    payload: MockReportCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Verify resume exists
    res_stmt = select(Resume).filter(Resume.id == payload.resume_id)
    res_res = await db.execute(res_stmt)
    resume = res_res.scalars().first()
    if not resume:
        raise NotFoundException("Resume not found")
        
    # Verify job description exists
    jd_stmt = select(JobDescription).filter(JobDescription.id == payload.job_id)
    jd_res = await db.execute(jd_stmt)
    jd = jd_res.scalars().first()
    if not jd:
        raise NotFoundException("Job Description not found")
        
    # Create Interview
    interview = Interview(
        resume_id=resume.id,
        job_description_id=jd.id,
        status="completed"
    )
    db.add(interview)
    await db.flush() # get interview.id
    
    # Create mock questions & turns
    q1 = InterviewQuestion(
        interview_id=interview.id,
        question_text="Can you explain how decorators work in Python?",
        topic="Python",
        expected_keywords=["wrap", "function", "decorator"]
    )
    q2 = InterviewQuestion(
        interview_id=interview.id,
        question_text="What is dependency injection in FastAPI?",
        topic="FastAPI",
        expected_keywords=["Depends", "inject", "parameter"]
    )
    db.add_all([q1, q2])
    await db.flush()
    
    t1 = InterviewTurn(
        interview_id=interview.id,
        question_id=q1.id,
        candidate_response="A decorator takes another function and extends its behavior without modifying it.",
        transcription_confidence=0.95,
        evaluation_score=8.5,
        evaluation_feedback="Correct explanation of function wrapping."
    )
    t2 = InterviewTurn(
        interview_id=interview.id,
        question_id=q2.id,
        candidate_response="FastAPI uses the Depends keyword to declare dependencies that are injected automatically.",
        transcription_confidence=0.98,
        evaluation_score=9.0,
        evaluation_feedback="Excellent explanation of dependency injection."
    )
    db.add_all([t1, t2])
    
    # Create EvaluationReport
    report = EvaluationReport(
        interview_id=interview.id,
        overall_score=8.75,
        recommendation="hire",
        primary_summary=f"Candidate {resume.candidate_name} demonstrated strong capability in Python and FastAPI during the voice screening session.",
        details={
            "Python": {"score": 8.5, "evidence": "Understands wrapping and decorator syntax."},
            "FastAPI": {"score": 9.0, "evidence": "Clearly understands dependency injection with Depends."}
        }
    )
    db.add(report)
    await db.commit()
    await db.refresh(report)
    return report
