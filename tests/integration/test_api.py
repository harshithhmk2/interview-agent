import pytest
import uuid
import base64
from io import BytesIO
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from src.db.models import Resume, Interview, InterviewQuestion, InterviewTurn, EvaluationReport
from src.services.parser import ResumeParsedAttributes, JDParsedAttributes
from src.agents.nodes.planner import InterviewPlanResponse, PlannedQuestion
from src.agents.nodes.evaluator import EvaluationResponse
from src.agents.nodes.interviewer import FollowUpQuestionResponse
from src.agents.nodes.reporter import ReporterOutputResponse, CategoryScoreDetail


@pytest.fixture
async def auth_headers(client):
    """
    Helper fixture to register a recruiter and retrieve authorization headers.
    """
    signup_data = {
        "email": "recruiter_test@example.com",
        "password": "SecurePassword123!",
        "full_name": "Test Recruiter",
        "role": "admin"
    }
    await client.post("/api/v1/auth/signup", json=signup_data)
    
    login_data = {
        "username": "recruiter_test@example.com",
        "password": "SecurePassword123!"
    }
    response = await client.post("/api/v1/auth/token", data=login_data)
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_auth_workflow(client):
    # Test Signup
    signup_data = {
        "email": "new_recruiter@example.com",
        "password": "SecurePassword123!",
        "full_name": "New Recruiter",
        "role": "admin"
    }
    response = await client.post("/api/v1/auth/signup", json=signup_data)
    assert response.status_code == 201
    assert "id" in response.json()

    # Test Signup Duplicate email error
    response_dup = await client.post("/api/v1/auth/signup", json=signup_data)
    assert response_dup.status_code == 401

    # Test Token Login
    login_data = {
        "username": "new_recruiter@example.com",
        "password": "SecurePassword123!"
    }
    response_token = await client.post("/api/v1/auth/token", data=login_data)
    assert response_token.status_code == 200
    token_json = response_token.json()
    assert "access_token" in token_json
    assert token_json["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_job_descriptions_workflow(client, auth_headers):
    # Create JD, mocking Ollama structured JSON extraction for JDParsedAttributes
    expected_jd_attr = JDParsedAttributes(
        role_title="Senior Python Backend Developer",
        tech_stack=["Python", "FastAPI", "PostgreSQL"],
        minimum_experience_years=4.5,
        core_responsibilities=["Write clean code", "Write integration tests"],
        preferred_skills=["Docker", "AWS"]
    )

    with patch("src.services.llm.OllamaLLMClient.generate_structured_json", AsyncMock(return_value=expected_jd_attr)):
        jd_data = {
            "title": "Senior Python Backend Developer",
            "raw_text": "We need a Senior Python developer with FastAPI and PostgreSQL expertise and 4+ years experience."
        }
        response = await client.post("/api/v1/jobs", json=jd_data, headers=auth_headers)
        assert response.status_code == 201
        res_data = response.json()
        assert res_data["title"] == "Senior Python Backend Developer"
        assert res_data["parsed_attributes"]["tech_stack"] == ["Python", "FastAPI", "PostgreSQL"]
        assert "id" in res_data

        # List jobs
        list_response = await client.get("/api/v1/jobs", headers=auth_headers)
        assert list_response.status_code == 200
        assert len(list_response.json()) >= 1
        assert list_response.json()[0]["id"] == res_data["id"]


@pytest.mark.asyncio
async def test_resume_upload_and_cascade_delete(client, auth_headers, db_session):
    # 1. Setup Job Description first
    expected_jd_attr = JDParsedAttributes(
        role_title="QA Engineer",
        tech_stack=["Python", "Pytest"],
        minimum_experience_years=3.0,
        core_responsibilities=[],
        preferred_skills=[]
    )
    with patch("src.services.llm.OllamaLLMClient.generate_structured_json", AsyncMock(return_value=expected_jd_attr)):
        jd_res = await client.post("/api/v1/jobs", json={
            "title": "QA Engineer",
            "raw_text": "Require QA Engineer with Pytest experience."
        }, headers=auth_headers)
        job_id = jd_res.json()["id"]

    # 2. Upload resume, mocking extraction and matching
    expected_resume_attr = ResumeParsedAttributes(
        candidate_name="Bob Tester",
        candidate_email="bob.tester@example.com",
        skills=["Python", "Pytest", "Selenium"],
        experience_years=3.5,
        education=[],
        past_roles=[]
    )
    
    mock_embeddings = [0.1] * 128
    
    with patch("src.services.llm.OllamaLLMClient.generate_structured_json", AsyncMock(return_value=expected_resume_attr)), \
         patch("src.services.llm.OllamaLLMClient.generate_embeddings", AsyncMock(return_value=mock_embeddings)), \
         patch("src.services.parser.pypdf.PdfReader") as mock_pdf:
         
        mock_pdf_instance = MagicMock()
        mock_page = MagicMock()
        mock_page.extract_text.return_value = "Bob Tester QA resume details..."
        mock_pdf_instance.pages = [mock_page]
        mock_pdf.return_value = mock_pdf_instance

        resume_file = ("bob_resume.pdf", BytesIO(b"dummy pdf content"), "application/pdf")
        response = await client.post(
            f"/api/v1/resumes?job_id={job_id}",
            files={"file": resume_file},
            headers=auth_headers
        )
        assert response.status_code == 201
        res_data = response.json()
        assert res_data["candidate_name"] == "Bob Tester"
        assert res_data["candidate_email"] == "bob.tester@example.com"
        assert res_data["match_score"]["overall_percentage"] == 100.0
        resume_id = res_data["id"]

    # 3. Schedule an Interview Session to create child entities
    expected_plan = InterviewPlanResponse(
        questions=[
            PlannedQuestion(topic="Python", question_text="What is PEP-8?", expected_keywords=["formatting"]),
            PlannedQuestion(topic="Pytest", question_text="What is a fixture?", expected_keywords=["decorator"])
        ]
    )
    with patch("src.services.llm.OllamaLLMClient.generate_structured_json", AsyncMock(return_value=expected_plan)):
        sess_payload = {
            "job_description_id": job_id,
            "resume_id": resume_id
        }
        sess_res = await client.post("/api/v1/interviews/sessions", json=sess_payload, headers=auth_headers)
        assert sess_res.status_code == 201
        interview_id = sess_res.json()["id"]

    # 4. Insert dummy turn and evaluation report to verify deep cascade delete
    # Fetch interview using db_session
    db_stmt = select(Interview).filter(Interview.id == uuid.UUID(interview_id))
    db_res = await db_session.execute(db_stmt)
    db_interview = db_res.scalars().first()
    
    # Add an EvaluationReport
    report = EvaluationReport(
        interview_id=db_interview.id,
        overall_score=8.0,
        recommendation="hire",
        primary_summary="Great candidate",
        details={}
    )
    db_session.add(report)
    await db_session.commit()

    # Verify entities exist in database
    assert (await db_session.execute(select(Resume).filter(Resume.id == uuid.UUID(resume_id)))).scalars().first() is not None
    assert (await db_session.execute(select(Interview).filter(Interview.id == uuid.UUID(interview_id)))).scalars().first() is not None
    assert (await db_session.execute(select(EvaluationReport).filter(EvaluationReport.interview_id == uuid.UUID(interview_id)))).scalars().first() is not None
    assert len((await db_session.execute(select(InterviewQuestion).filter(InterviewQuestion.interview_id == uuid.UUID(interview_id)))).scalars().all()) == 2

    # 5. Delete Resume
    delete_res = await client.delete(f"/api/v1/resumes/{resume_id}", headers=auth_headers)
    assert delete_res.status_code == 204

    # 6. Verify Cascade Deletions (Privacy by Default)
    db_session.expire_all()
    assert (await db_session.execute(select(Resume).filter(Resume.id == uuid.UUID(resume_id)))).scalars().first() is None
    assert (await db_session.execute(select(Interview).filter(Interview.id == uuid.UUID(interview_id)))).scalars().first() is None
    assert (await db_session.execute(select(InterviewQuestion).filter(InterviewQuestion.interview_id == uuid.UUID(interview_id)))).scalars().first() is None
    assert (await db_session.execute(select(InterviewTurn).filter(InterviewTurn.interview_id == uuid.UUID(interview_id)))).scalars().first() is None
    assert (await db_session.execute(select(EvaluationReport).filter(EvaluationReport.interview_id == uuid.UUID(interview_id)))).scalars().first() is None


@pytest.mark.asyncio
async def test_full_interview_and_reports_workflow(client, auth_headers, db_session):
    # 1. Setup Job Description
    expected_jd_attr = JDParsedAttributes(
        role_title="FastAPI Specialist",
        tech_stack=["FastAPI", "SQLAlchemy"],
        minimum_experience_years=2.0,
        core_responsibilities=[],
        preferred_skills=[]
    )
    with patch("src.services.llm.OllamaLLMClient.generate_structured_json", AsyncMock(return_value=expected_jd_attr)):
        jd_res = await client.post("/api/v1/jobs", json={
            "title": "FastAPI Specialist",
            "raw_text": "Need someone who knows FastAPI and SQLAlchemy."
        }, headers=auth_headers)
        job_id = jd_res.json()["id"]

    # 2. Setup Resume
    expected_resume_attr = ResumeParsedAttributes(
        candidate_name="Jane Dev",
        candidate_email="jane.dev@example.com",
        skills=["FastAPI", "SQLAlchemy"],
        experience_years=2.5,
        education=[],
        past_roles=[]
    )
    mock_embeddings = [0.2] * 128
    with patch("src.services.llm.OllamaLLMClient.generate_structured_json", AsyncMock(return_value=expected_resume_attr)), \
         patch("src.services.llm.OllamaLLMClient.generate_embeddings", AsyncMock(return_value=mock_embeddings)), \
         patch("src.services.parser.pypdf.PdfReader") as mock_pdf:
         
        mock_pdf_instance = MagicMock()
        mock_page = MagicMock()
        mock_page.extract_text.return_value = "Jane Dev resume content..."
        mock_pdf_instance.pages = [mock_page]
        mock_pdf.return_value = mock_pdf_instance

        resume_file = ("jane_resume.pdf", BytesIO(b"dummy pdf content"), "application/pdf")
        res_res = await client.post(
            f"/api/v1/resumes?job_id={job_id}",
            files={"file": resume_file},
            headers=auth_headers
        )
        resume_id = res_res.json()["id"]

    # 3. Schedule Interview (which compiles questions plan: topic 1: FastAPI, topic 2: SQLAlchemy)
    expected_plan = InterviewPlanResponse(
        questions=[
            PlannedQuestion(topic="FastAPI", question_text="What is a Dependency?", expected_keywords=["Depends"]),
            PlannedQuestion(topic="SQLAlchemy", question_text="What is AsyncSession?", expected_keywords=["async"])
        ]
    )
    with patch("src.services.llm.OllamaLLMClient.generate_structured_json", AsyncMock(return_value=expected_plan)):
        sess_res = await client.post("/api/v1/interviews/sessions", json={
            "job_description_id": job_id,
            "resume_id": resume_id
        }, headers=auth_headers)
        interview_id = sess_res.json()["id"]

    # 4. REST Turn 1 (FastAPI topic, answering well >= 6.0 score, routing to next planned question)
    expected_eval_1 = EvaluationResponse(
        score=8.5,
        evidence="Candidate details dependency injection concepts accurately."
    )
    expected_interviewer_next = FollowUpQuestionResponse(
        followup_question=""  # Not needed since score is high, code will fetch next question from planned queue
    )
    
    mock_audio_file = Path("./tts_output/dummy.wav")
    
    with patch("src.services.llm.OllamaLLMClient.generate_structured_json", AsyncMock(return_value=expected_eval_1)), \
         patch("src.services.speech.LocalSpeechService.synthesize_speech", AsyncMock(return_value=mock_audio_file)), \
         patch("pathlib.Path.exists", return_value=True), \
         patch("pathlib.Path.read_bytes", return_value=b"RIFF synthesized audio"):
         
        turn_res_1 = await client.post(
            f"/api/v1/interviews/{interview_id}/turns",
            json={
                "response_text": "Dependency injection is handled using Depends.",
                "latency_seconds": 1.2
            },
            headers=auth_headers
        )
        assert turn_res_1.status_code == 200
        json_1 = turn_res_1.json()
        assert json_1["next_question"] == "What is AsyncSession?"
        assert json_1["next_question_audio_base64"] == base64.b64encode(b"RIFF synthesized audio").decode("utf-8")
        assert json_1["is_last"] is False

    # 5. REST Turn 2 (SQLAlchemy topic, answering well, this is the last planned question -> compile report)
    expected_eval_2 = EvaluationResponse(
        score=9.0,
        evidence="Candidate correctly described AsyncSession usage."
    )
    expected_report = ReporterOutputResponse(
        overall_score=8.75,
        recommendation="hire",
        primary_summary="Strong backend developer with excellent FastAPI and SQLAlchemy skills.",
        details={
            "FastAPI": CategoryScoreDetail(score=8.5, evidence="Correct injection explanation"),
            "SQLAlchemy": CategoryScoreDetail(score=9.0, evidence="AsyncSession explained")
        }
    )

    with patch("src.services.llm.OllamaLLMClient.generate_structured_json") as mock_json_generator:
        # Mock structured JSON returns for evaluator and then reporter
        mock_json_generator.side_effect = [expected_eval_2, expected_report]

        turn_res_2 = await client.post(
            f"/api/v1/interviews/{interview_id}/turns",
            json={
                "response_text": "AsyncSession manages async database connections.",
                "latency_seconds": 0.8
            },
            headers=auth_headers
        )
        assert turn_res_2.status_code == 200
        json_2 = turn_res_2.json()
        assert json_2["is_last"] is True
        assert json_2["next_question"] == ""

    # 6. Retrieve Report
    report_res = await client.get(f"/api/v1/reports/{interview_id}", headers=auth_headers)
    assert report_res.status_code == 200
    report_json = report_res.json()
    assert report_json["overall_score"] == 8.75
    assert report_json["recommendation"] == "hire"
    assert "SQLAlchemy" in report_json["details"]
    assert report_json["recruiter_notes"] is None

    # 7. Recruiter Override
    override_res = await client.patch(
        f"/api/v1/reports/{interview_id}/override",
        json={
            "recruiter_override_recommendation": "hire",
            "recruiter_notes": "Recruiter notes: Candidate passed all checks with flying colors."
        },
        headers=auth_headers
    )
    assert override_res.status_code == 200
    override_json = override_res.json()
    assert override_json["recruiter_override_recommendation"] == "hire"
    assert "flying colors" in override_json["recruiter_notes"]
    assert override_json["reviewed_at"] is not None
