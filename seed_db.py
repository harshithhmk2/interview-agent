#!/usr/bin/env python3
"""
Seed script to populate the AI Voice Interview Agent database with rich sample data:
- Recruiter & Candidate User Accounts
- Job Descriptions with parsed technical attributes
- Candidate Resumes with AI match scores
- Completed Interview Sessions with transcripts, turns, and structured evaluation reports.
"""

import asyncio
import uuid
from datetime import datetime
from sqlalchemy.future import select

from src.core.database import SessionLocal, engine
from src.db.base import Base
from src.db.models import (
    User,
    JobDescription,
    Resume,
    Interview,
    InterviewQuestion,
    InterviewTurn,
    EvaluationReport,
    AuditLog
)
from src.core.security import get_password_hash


async def seed_data():
    print("==========================================")
    print("  Seeding AI Voice Interview Agent Data   ")
    print("==========================================")

    # 1. Ensure all database tables exist and role column is present with retries
    for attempt in range(15):
        try:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
                try:
                    from sqlalchemy import text
                    await conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS role VARCHAR(50) DEFAULT 'candidate';"))
                    await conn.execute(text("ALTER TABLE job_descriptions ADD COLUMN IF NOT EXISTS company_name VARCHAR(255) DEFAULT 'Implere Technologies';"))
                    await conn.execute(text("ALTER TABLE job_descriptions ADD COLUMN IF NOT EXISTS status VARCHAR(50) DEFAULT 'open';"))
                    await conn.execute(text("ALTER TABLE job_descriptions ADD COLUMN IF NOT EXISTS work_mode VARCHAR(50) DEFAULT 'onsite';"))
                    await conn.execute(text("ALTER TABLE job_descriptions ADD COLUMN IF NOT EXISTS location VARCHAR(255) DEFAULT 'Bangalore';"))
                    await conn.execute(text("ALTER TABLE job_descriptions ADD COLUMN IF NOT EXISTS experience_range VARCHAR(100) DEFAULT '3 - 5 Years';"))
                    await conn.execute(text("ALTER TABLE job_descriptions ADD COLUMN IF NOT EXISTS salary_range VARCHAR(100) DEFAULT '₹ 15L - 18L / year';"))
                    await conn.execute(text("ALTER TABLE resumes DROP CONSTRAINT IF EXISTS resumes_candidate_email_key;"))
                    await conn.execute(text("DROP INDEX IF EXISTS resumes_candidate_email_key;"))
                except Exception:
                    pass
            break
        except Exception as e:
            if attempt < 14:
                print(f"[RETRY] Waiting for database (attempt {attempt+1}/15): {e}")
                await asyncio.sleep(2)
            else:
                raise e

    async with SessionLocal() as session:
        # Check if sample data is already seeded
        result = await session.execute(select(User).filter(User.email == "recruiter@example.com"))
        existing_user = result.scalars().first()

        if existing_user:
            print("[INFO] Sample data is already seeded in the database.")
            return

        # 2. Seed Recruiter & Candidate Accounts
        print("\n[1/5] Creating Recruiter & Candidate Accounts...")
        recruiter = User(
            id=uuid.uuid4(),
            email="recruiter@example.com",
            hashed_password=get_password_hash("SecurePassword123!"),
            full_name="Sarah TAG Lead",
            role="interviewer"
        )

        admin = User(
            id=uuid.uuid4(),
            email="admin@example.com",
            hashed_password=get_password_hash("SecurePassword123!"),
            full_name="System Admin",
            role="admin"
        )

        candidate = User(
            id=uuid.uuid4(),
            email="john.doe@example.com",
            hashed_password=get_password_hash("SecurePassword123!"),
            full_name="John Doe",
            role="candidate"
        )

        session.add_all([recruiter, admin, candidate])
        await session.commit()
        print(f"  [OK] Recruiter Created: {recruiter.email} (role: interviewer)")
        print(f"  [OK] Admin Created: {admin.email} (role: admin)")
        print(f"  [OK] Candidate Created: {candidate.email} (role: candidate)")

        # 3. Seed Job Descriptions
        print("\n[2/5] Seeding Job Descriptions (JDs)...")
        jd1 = JobDescription(
            id=uuid.uuid4(),
            recruiter_id=recruiter.id,
            title="Python Developer",
            company_name="Implere Technologies",
            status="open",
            work_mode="onsite",
            location="Bangalore",
            experience_range="3 - 5 Years",
            salary_range="₹ 15L - 18L / year",
            raw_text=(
                "We are seeking a Python Developer with 3-5 years experience in Python, Django, Flask/FastAPI, OOPS, and MySQL. "
                "Good to have Java. Role is Onsite in Bangalore."
            ),
            parsed_attributes={
                "role_title": "Python Developer",
                "tech_stack": ["Python", "Django", "Flask/FastAPI", "OOPS", "MySQL"],
                "minimum_experience_years": 3.0,
                "core_responsibilities": [
                    "Design and implement scalable Python APIs and Django/FastAPI services",
                    "Manage MySQL databases and optimize database queries",
                    "Apply clean Object Oriented Programming (OOPS) design patterns"
                ],
                "preferred_skills": ["Java", "Docker", "AWS"]
            },
            match_threshold=75.0
        )

        jd2 = JobDescription(
            id=uuid.uuid4(),
            recruiter_id=recruiter.id,
            title="AI Systems & LangGraph Engineer",
            company_name="Implere Technologies",
            status="open",
            work_mode="hybrid",
            location="Bangalore",
            experience_range="4 - 7 Years",
            salary_range="₹ 20L - 25L / year",
            raw_text=(
                "Join our AI team to orchestrate adaptive voice state machines using LangGraph, LangChain, "
                "Local Ollama models, and FAISS vector indices for autonomous screening."
            ),
            parsed_attributes={
                "role_title": "AI Systems & LangGraph Engineer",
                "tech_stack": ["Python", "LangGraph", "LangChain", "Ollama", "FAISS", "Pytest"],
                "minimum_experience_years": 4.0,
                "core_responsibilities": [
                    "Construct state machines and graph nodes for voice screening",
                    "Integrate local Whisper STT and Piper TTS engines"
                ],
                "preferred_skills": ["Pytest", "FastAPI"]
            },
            match_threshold=80.0
        )

        session.add_all([jd1, jd2])
        await session.commit()
        print(f"  [OK] Job Description 1: {jd1.title}")
        print(f"  [OK] Job Description 2: {jd2.title}")

        # 4. Seed Candidate Resumes with AI Match Scores
        print("\n[3/5] Seeding Candidate Resumes & AI Match Analysis...")
        resume1 = Resume(
            id=uuid.uuid4(),
            candidate_name="John Doe",
            candidate_email="john.doe@example.com",
            raw_text=(
                "John Doe - Senior Software Engineer\n"
                "Email: john.doe@example.com\n"
                "Summary: 6 years of software engineering experience specializing in Python, FastAPI, PostgreSQL, "
                "Docker, and Async microservices. Built scalable backend systems handling high concurrency.\n"
                "Skills: Python, FastAPI, AsyncIO, PostgreSQL, SQLAlchemy, Docker, Redis, Pytest"
            ),
            parsed_attributes={
                "candidate_name": "John Doe",
                "candidate_email": "john.doe@example.com",
                "skills": ["Python", "FastAPI", "AsyncIO", "PostgreSQL", "SQLAlchemy", "Docker", "Redis", "Pytest"],
                "experience_years": 6.0,
                "education": ["B.S. Computer Science"],
                "past_roles": ["Senior Backend Developer - TechCorp", "Software Engineer - DataSystems"]
            },
            job_description_id=jd1.id,
            match_score=92.5,
            match_details={
                "overall_percentage": 92.5,
                "matching_skills": ["Python", "FastAPI", "PostgreSQL", "SQLAlchemy", "Docker", "AsyncIO"],
                "missing_skills": ["AWS"],
                "experience_match": "Exceeds requirements (6.0 yrs vs 5.0 yrs minimum)",
                "verdict": "STRONG_MATCH"
            },
            proceed_to_next_round=True
        )

        resume2 = Resume(
            id=uuid.uuid4(),
            candidate_name="Alice Smith",
            candidate_email="alice.smith@example.com",
            raw_text=(
                "Alice Smith - AI & ML Engineer\n"
                "Email: alice.smith@example.com\n"
                "Summary: 4 years of experience building LLM pipelines, LangChain applications, and vector search with FAISS."
            ),
            parsed_attributes={
                "candidate_name": "Alice Smith",
                "candidate_email": "alice.smith@example.com",
                "skills": ["Python", "LangChain", "LangGraph", "FAISS", "Ollama", "Pytest"],
                "experience_years": 4.0,
                "education": ["M.S. Artificial Intelligence"],
                "past_roles": ["AI Engineer - FutureAI"]
            },
            job_description_id=jd2.id,
            match_score=88.0,
            match_details={
                "overall_percentage": 88.0,
                "matching_skills": ["Python", "LangGraph", "LangChain", "Ollama", "FAISS"],
                "missing_skills": [],
                "experience_match": "Meets requirements",
                "verdict": "MATCH"
            },
            proceed_to_next_round=True
        )

        session.add_all([resume1, resume2])
        await session.commit()
        print(f"  [OK] Resume 1: {resume1.candidate_name} -> Match Score: {resume1.match_score}%")
        print(f"  [OK] Resume 2: {resume2.candidate_name} -> Match Score: {resume2.match_score}%")

        # 5. Seed Interview Session with Questions, Turns, and Structured Report
        print("\n[4/5] Seeding Completed Voice Interview Session & Transcripts...")
        interview = Interview(
            id=uuid.uuid4(),
            job_description_id=jd1.id,
            resume_id=resume1.id,
            status="completed",
            completed_at=datetime.utcnow()
        )
        session.add(interview)
        await session.flush()

        q1 = InterviewQuestion(
            id=uuid.uuid4(),
            interview_id=interview.id,
            sequence_order=1,
            topic="FastAPI & AsyncIO",
            question_text="How do you handle async dependency injection and database session lifecycles in FastAPI?",
            expected_keywords="Depends, AsyncSession, context manager, yield"
        )
        q2 = InterviewQuestion(
            id=uuid.uuid4(),
            interview_id=interview.id,
            sequence_order=2,
            topic="SQLAlchemy & Performance",
            question_text="What strategies do you use to prevent N+1 query problems in SQLAlchemy ORM?",
            expected_keywords="selectinload, joinedload, eager loading"
        )
        session.add_all([q1, q2])
        await session.flush()

        turn1 = InterviewTurn(
            id=uuid.uuid4(),
            interview_id=interview.id,
            question_id=q1.id,
            turn_index=1,
            question_asked="How do you handle async dependency injection and database session lifecycles in FastAPI?",
            response_transcript="I define database dependency functions using async yield statements with AsyncSessionLocal. In FastAPI routes, I inject them via Depends(get_db) to ensure clean session close per request.",
            latency_seconds=1.1,
            turn_score=9.0,
            score_evidence="Candidate accurately explained yield-based async dependencies and session scoping with Depends."
        )
        turn2 = InterviewTurn(
            id=uuid.uuid4(),
            interview_id=interview.id,
            question_id=q2.id,
            turn_index=2,
            question_asked="What strategies do you use to prevent N+1 query problems in SQLAlchemy ORM?",
            response_transcript="I use selectinload or joinedload option wrappers when querying relationships to perform eager loading in a single optimized SQL statement.",
            latency_seconds=0.9,
            turn_score=9.5,
            score_evidence="Candidate demonstrated precise knowledge of selectinload and joinedload eager loading strategies."
        )
        session.add_all([turn1, turn2])
        await session.flush()

        report = EvaluationReport(
            id=uuid.uuid4(),
            interview_id=interview.id,
            overall_score=9.25,
            recommendation="hire",
            primary_summary="Exceptional candidate with deep expertise in Python, FastAPI, and SQLAlchemy. Clean articulation and fast response latency.",
            details={
                "FastAPI & AsyncIO": {
                    "score": 9.0,
                    "evidence": "Accurately explained yield-based async dependencies and session scoping with Depends."
                },
                "SQLAlchemy & Performance": {
                    "score": 9.5,
                    "evidence": "Demonstrated precise knowledge of selectinload and joinedload eager loading strategies."
                }
            },
            recruiter_override_recommendation="hire",
            recruiter_notes="Verified technical skills. Strongly recommend moving to final round.",
            reviewer_id=recruiter.id,
            reviewed_at=datetime.utcnow()
        )
        session.add(report)

        # 6. Seed Audit Log
        audit = AuditLog(
            id=uuid.uuid4(),
            user_id=recruiter.id,
            action_type="REVIEW_EVALUATION_REPORT",
            target_resource_type="EvaluationReport",
            target_resource_id=report.id,
            action_metadata={"recommendation": "hire", "final_decision": "APPROVED"}
        )
        session.add(audit)

        await session.commit()
        print(f"  [OK] Interview Session Created ID: {interview.id}")
        print(f"  [OK] Structured Evaluation Report Generated -> Score: {report.overall_score}/10.0 ({report.recommendation.upper()})")

    print("\n==========================================")
    print("    Sample Data Seeding Complete!         ")
    print("==========================================")


if __name__ == "__main__":
    asyncio.run(seed_data())
