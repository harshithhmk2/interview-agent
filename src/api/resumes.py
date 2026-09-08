from fastapi import APIRouter, Depends, status, UploadFile, File, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List, Union, Any
import uuid
import io

from src.core.database import get_db
from src.core.exceptions import NotFoundException, ValidationException, AuthException
from src.api.auth import get_current_user
from src.db.models import User, Resume, JobDescription
from src.schemas.resumes import ResumeUploadResponse, MatchDetails, CandidateApplicationResponse, ResumeProceedRequest
from src.services.llm import OllamaLLMClient
from src.services.parser import DocumentParser
from src.services.vector_store import SemanticMatcher
from src.agents.nodes.planner import PlannerNode
import logging
from src.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/resumes", tags=["resumes"])

@router.get("/my-applications", response_model=List[dict])
async def get_my_applications(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    stmt = (
        select(Resume)
        .options(selectinload(Resume.interviews))
        .filter((Resume.candidate_email == current_user.email) & (Resume.job_description_id.isnot(None)))
    )
    res = await db.execute(stmt)
    resumes = res.scalars().all()
    
    output = []
    for r in resumes:
        interviews = r.interviews or []
        completed = any(i.status in ["completed", "evaluated"] for i in interviews)
        output.append({
            "job_id": r.job_description_id,
            "resume_id": r.id,
            "screening_completed": completed,
            "interview_count": len(interviews),
            "latest_status": interviews[-1].status if interviews else "applied"
        })
    return output



@router.post("", response_model=Union[ResumeUploadResponse, CandidateApplicationResponse], status_code=status.HTTP_201_CREATED)
async def upload_resume(
    job_id: uuid.UUID = Query(...),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    jd_stmt = select(JobDescription).filter(JobDescription.id == job_id)
    jd_result = await db.execute(jd_stmt)
    jd = jd_result.scalars().first()
    if not jd:
        raise NotFoundException(f"Job Description not found: {job_id}")

    # Prevent duplicate applications from the same candidate for the same job position
    dup_stmt = select(Resume).filter(
        (Resume.job_description_id == job_id) & (Resume.candidate_email == current_user.email)
    )
    dup_res = await db.execute(dup_stmt)
    if dup_res.scalars().first():
        raise ValidationException("You have already applied for this position.")

    filename = file.filename or ""
    ext = filename.split(".")[-1] if "." in filename else "txt"
    
    parser = DocumentParser()
    
    try:
        content_bytes = await file.read()
        raw_text = parser.extract_text(io.BytesIO(content_bytes), ext)
        if raw_text:
            raw_text = raw_text.replace("\x00", "")
    except Exception as e:
        raise ValidationException(f"Failed to extract text: {e}")
        
    parsed_res = await parser.parse_entities(raw_text, doc_type="resume")
    
    if current_user.role == "candidate":
        candidate_name = current_user.full_name or parsed_res.get("candidate_name") or "Unknown Candidate"
        candidate_email = current_user.email
    else:
        candidate_name = parsed_res.get("candidate_name") or "Unknown Candidate"
        candidate_email = parsed_res.get("candidate_email") or current_user.email or f"unknown_{uuid.uuid4().hex[:8]}@example.com"
        
    chk_stmt = select(Resume).filter(
        (Resume.job_description_id == job_id) & (Resume.candidate_email == candidate_email)
    )
    chk_res = await db.execute(chk_stmt)
    existing_resume = chk_res.scalars().first()
    if existing_resume:
        if current_user.role == "candidate":
            raise ValidationException("You have already applied for this position.")
        await db.delete(existing_resume)
        await db.commit()

    threshold = jd.match_threshold if jd.match_threshold is not None else settings.DEFAULT_MATCH_THRESHOLD

    matcher = SemanticMatcher()
    match_details = await matcher.match_resume_to_jd(parsed_res, jd.parsed_attributes)
    
    proceed = match_details.overall_percentage >= threshold
    
    # Pre-generate candidate tailored question plan based on parsed resume & JD attributes
    questions_plan = []
    try:
        planner = PlannerNode()
        plan_state = await planner.execute({
            "job_title": jd.title,
            "parsed_resume": parsed_res,
            "parsed_jd": jd.parsed_attributes
        })
        questions_plan = plan_state.get("questions_plan", [])
    except Exception as e:
        logger.warning(f"Pre-generating questions_plan on upload skipped: {e}")

    resume = Resume(
        candidate_name=candidate_name,
        candidate_email=candidate_email,
        raw_text=raw_text,
        parsed_attributes=parsed_res,
        job_description_id=job_id,
        match_score=match_details.overall_percentage,
        match_details=match_details.model_dump(),
        proceed_to_next_round=proceed,
        questions_plan=questions_plan
    )
    db.add(resume)
    await db.commit()
    await db.refresh(resume)
    
    if current_user.role == "candidate":
        return CandidateApplicationResponse(
            message="Application submitted successfully",
            id=resume.id
        )
        
    return ResumeUploadResponse(
        id=resume.id,
        candidate_name=resume.candidate_name,
        candidate_email=resume.candidate_email,
        parsed_attributes=resume.parsed_attributes,
        match_score=match_details
    )

@router.get("", response_model=List[dict])
async def list_resumes(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role not in ["admin", "interviewer", "recruiter"]:
        raise AuthException("Access denied: Admin, interviewer or recruiter role required")
        
    stmt = select(Resume).order_by(Resume.created_at.desc())
    res = await db.execute(stmt)
    resumes_list = res.scalars().all()
    
    output = []
    for r in resumes_list:
        job_title = None
        if r.job_description_id:
            jd_stmt = select(JobDescription).filter(JobDescription.id == r.job_description_id)
            jd_res = await db.execute(jd_stmt)
            jd = jd_res.scalars().first()
            if jd:
                job_title = jd.title
                
        output.append({
            "id": r.id,
            "candidate_name": r.candidate_name,
            "candidate_email": r.candidate_email,
            "job_id": r.job_description_id,
            "job_title": job_title,
            "match_score": r.match_score,
            "proceed_to_next_round": r.proceed_to_next_round,
            "created_at": r.created_at
        })
    return output

@router.patch("/{resume_id}/proceed", response_model=ResumeUploadResponse)
async def update_proceed_status(
    resume_id: uuid.UUID,
    payload: ResumeProceedRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role not in ["admin", "interviewer", "recruiter"]:
        raise AuthException("Access denied: Admin, interviewer or recruiter role required")
        
    stmt = select(Resume).filter(Resume.id == resume_id)
    res = await db.execute(stmt)
    resume = res.scalars().first()
    if not resume:
        raise NotFoundException("Resume not found")
        
    resume.proceed_to_next_round = payload.proceed_to_next_round
    await db.commit()
    await db.refresh(resume)
    
    match_data = resume.match_details or {}
    match_score = MatchDetails(
        overall_percentage=resume.match_score or 0.0,
        matched_skills=match_data.get("matched_skills", []),
        gaps_identified=match_data.get("gaps_identified", []),
        recommended_topics_to_probe=match_data.get("recommended_topics_to_probe", [])
    )
    return ResumeUploadResponse(
        id=resume.id,
        candidate_name=resume.candidate_name,
        candidate_email=resume.candidate_email,
        parsed_attributes=resume.parsed_attributes,
        match_score=match_score
    )

@router.delete("/{resume_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_resume(
    resume_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role not in ["admin", "interviewer", "recruiter"]:
        raise AuthException("Access denied: Admin, interviewer or recruiter role required")

    stmt = select(Resume).filter(Resume.id == resume_id)
    result = await db.execute(stmt)
    resume = result.scalars().first()
    if not resume:
        raise NotFoundException(f"Resume not found: {resume_id}")
        
    await db.delete(resume)
    await db.commit()
    return
