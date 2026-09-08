from fastapi import APIRouter
from src.api.auth import router as auth_router
from src.api.job_descriptions import router as jobs_router
from src.api.resumes import router as resumes_router
from src.api.interviews import router as interviews_router
from src.api.reports import router as reports_router

api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(jobs_router)
api_router.include_router(resumes_router)
api_router.include_router(interviews_router)
api_router.include_router(reports_router)
