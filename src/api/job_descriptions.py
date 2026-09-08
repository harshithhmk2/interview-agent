from fastapi import APIRouter, Depends, status, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List, Optional
import uuid
import io

from src.core.database import get_db
from src.api.auth import get_current_user, get_current_user_optional
from src.db.models import User, JobDescription
from src.schemas.job_descriptions import JobDescriptionCreate, JobDescriptionResponse
from src.services.llm import OllamaLLMClient
from src.services.parser import DocumentParser
from src.core.exceptions import AuthException, NotFoundException, ValidationException

router = APIRouter(prefix="/jobs", tags=["jobs"])

@router.post("", response_model=JobDescriptionResponse, status_code=status.HTTP_201_CREATED)
async def create_job_description(
    payload: JobDescriptionCreate, 
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role not in ["admin", "interviewer"]:
        raise AuthException("Access denied: Admin or interviewer role required")

    llm_client = OllamaLLMClient()
    parser = DocumentParser(llm_client=llm_client)
    
    parsed_attr = await parser.parse_entities(payload.raw_text, doc_type="jd")
    if isinstance(parsed_attr, dict):
        parsed_attr["role_title"] = payload.title
        if payload.experience_range:
            import re
            m = re.search(r"(\d+(?:\.\d+)?)", payload.experience_range)
            if m:
                parsed_attr["minimum_experience_years"] = float(m.group(1))

    jd = JobDescription(
        recruiter_id=current_user.id,
        title=payload.title,
        company_name=payload.company_name or "Implere Technologies",
        status=payload.status or "open",
        work_mode=payload.work_mode or "onsite",
        location=payload.location or "Bangalore",
        experience_range=payload.experience_range or "3 - 5 Years",
        salary_range=payload.salary_range or "₹ 15L - 18L / year",
        raw_text=payload.raw_text,
        parsed_attributes=parsed_attr,
        match_threshold=payload.match_threshold
    )
    db.add(jd)
    await db.commit()
    await db.refresh(jd)
    return jd

@router.post("/upload", response_model=JobDescriptionResponse, status_code=status.HTTP_201_CREATED)
async def upload_job_description(
    title: str = Form(...),
    file: UploadFile = File(...),
    company_name: Optional[str] = Form("Implere Technologies"),
    status: Optional[str] = Form("open"),
    work_mode: Optional[str] = Form("onsite"),
    location: Optional[str] = Form("Bangalore"),
    experience_range: Optional[str] = Form("3 - 5 Years"),
    salary_range: Optional[str] = Form("₹ 15L - 18L / year"),
    match_threshold: Optional[float] = Form(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role not in ["admin", "interviewer"]:
        raise AuthException("Access denied: Admin or interviewer role required")

    filename = file.filename or ""
    ext = filename.split(".")[-1] if "." in filename else "txt"
    
    parser = DocumentParser()
    
    try:
        content_bytes = await file.read()
        raw_text = parser.extract_text(io.BytesIO(content_bytes), ext)
        if raw_text:
            raw_text = raw_text.replace("\x00", "")
    except Exception as e:
        raise ValidationException(f"Failed to extract text from file: {e}")
        
    parsed_attr = await parser.parse_entities(raw_text, doc_type="jd")
    if isinstance(parsed_attr, dict):
        parsed_attr["role_title"] = title
        if experience_range:
            import re
            m = re.search(r"(\d+(?:\.\d+)?)", experience_range)
            if m:
                parsed_attr["minimum_experience_years"] = float(m.group(1))

    jd = JobDescription(
        recruiter_id=current_user.id,
        title=title,
        company_name=company_name or "Implere Technologies",
        status=status or "open",
        work_mode=work_mode or "onsite",
        location=location or "Bangalore",
        experience_range=experience_range or "3 - 5 Years",
        salary_range=salary_range or "₹ 15L - 18L / year",
        raw_text=raw_text,
        parsed_attributes=parsed_attr,
        match_threshold=match_threshold
    )
    db.add(jd)
    await db.commit()
    await db.refresh(jd)
    return jd

@router.put("/{jd_id}", response_model=JobDescriptionResponse)
async def update_job_description(
    jd_id: uuid.UUID,
    payload: JobDescriptionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role not in ["admin", "interviewer"]:
        raise AuthException("Access denied: Admin or interviewer role required")
        
    stmt = select(JobDescription).filter(JobDescription.id == jd_id)
    res = await db.execute(stmt)
    jd = res.scalars().first()
    if not jd:
        raise NotFoundException("Job Description not found")
        
    llm_client = OllamaLLMClient()
    parser = DocumentParser(llm_client=llm_client)
    parsed_attr = await parser.parse_entities(payload.raw_text, doc_type="jd")
    if isinstance(parsed_attr, dict):
        parsed_attr["role_title"] = payload.title
        if payload.experience_range:
            import re
            m = re.search(r"(\d+(?:\.\d+)?)", payload.experience_range)
            if m:
                parsed_attr["minimum_experience_years"] = float(m.group(1))
    
    jd.title = payload.title
    jd.company_name = payload.company_name or "Implere Technologies"
    jd.status = payload.status or "open"
    jd.work_mode = payload.work_mode or "onsite"
    jd.location = payload.location or "Bangalore"
    jd.experience_range = payload.experience_range or "3 - 5 Years"
    jd.salary_range = payload.salary_range or "₹ 15L - 18L / year"
    jd.raw_text = payload.raw_text
    jd.parsed_attributes = parsed_attr
    jd.match_threshold = payload.match_threshold
    
    await db.commit()
    await db.refresh(jd)
    return jd

@router.delete("/{jd_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_job_description(
    jd_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role not in ["admin", "interviewer"]:
        raise AuthException("Access denied: Admin or interviewer role required")
        
    stmt = select(JobDescription).filter(JobDescription.id == jd_id)
    res = await db.execute(stmt)
    jd = res.scalars().first()
    if not jd:
        raise NotFoundException("Job Description not found")
        
    await db.delete(jd)
    await db.commit()
    return

@router.get("", response_model=List[JobDescriptionResponse])
async def list_job_descriptions(
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    stmt = select(JobDescription)
    result = await db.execute(stmt)
    return result.scalars().all()

