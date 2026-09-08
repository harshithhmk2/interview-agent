from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from typing import List, Optional
import uuid
import base64
import os
from pathlib import Path

from src.core.database import get_db
from src.core.exceptions import NotFoundException, ValidationException
from src.api.auth import get_current_user
from src.db.models import User, Interview, InterviewQuestion, InterviewTurn, EvaluationReport, Resume, JobDescription
from src.schemas.interviews import SessionCreateRequest, SessionResponse, TurnSubmissionRequest, TurnResponse
from src.services.llm import OllamaLLMClient
from src.services.speech import LocalSpeechService
from src.agents.nodes.planner import PlannerNode
from src.agents.nodes.interviewer import InterviewerNode
from src.agents.nodes.evaluator import EvaluatorNode
from src.agents.nodes.reporter import ReporterNode
from src.agents.graph import route_after_evaluation, route_after_increment

router = APIRouter(prefix="/interviews", tags=["interviews"])

@router.post("/sessions", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
async def create_interview_session(
    payload: SessionCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    res_stmt = select(Resume).filter(Resume.id == payload.resume_id)
    res_result = await db.execute(res_stmt)
    resume = res_result.scalars().first()
    if not resume:
        raise NotFoundException("Resume not found")

    jd_stmt = select(JobDescription).filter(JobDescription.id == payload.job_description_id)
    jd_result = await db.execute(jd_stmt)
    jd = jd_result.scalars().first()
    if not jd:
        raise NotFoundException("Job Description not found")

    interview = Interview(
        job_description_id=payload.job_description_id,
        resume_id=payload.resume_id,
        status="scheduled"
    )
    db.add(interview)
    await db.commit()
    await db.refresh(interview)

    # Execute PlannerNode with candidate parsed resume & JD attributes from DB
    planner = PlannerNode()
    initial_state = {
        "interview_id": str(interview.id),
        "candidate_name": resume.candidate_name,
        "job_title": jd.title,
        "parsed_resume": resume.parsed_attributes,
        "parsed_jd": jd.parsed_attributes,
        "questions_plan": resume.questions_plan or [],
        "current_question_index": 0,
        "turns_history": [],
        "last_turn_latency": 0.0,
        "overall_recommendation": None,
        "is_completed": False
    }
    planned_state = await planner.execute(initial_state)
    questions = planned_state.get("questions_plan", [])
    if not questions and resume.questions_plan:
        questions = resume.questions_plan
    else:
        resume.questions_plan = questions
        db.add(resume)

    for idx, q in enumerate(questions):
        q_id = uuid.UUID(q["id"]) if (isinstance(q.get("id"), str) and len(q["id"]) == 36) else uuid.uuid4()
        db_q = InterviewQuestion(
            id=q_id,
            interview_id=interview.id,
            sequence_order=idx,
            topic=q["topic"],
            question_text=q["question_text"],
            expected_keywords=", ".join(q["expected_keywords"]) if isinstance(q.get("expected_keywords"), list) else str(q.get("expected_keywords", ""))
        )
        db.add(db_q)
    
    if questions:
        first_q = questions[0]
        q_id = uuid.UUID(first_q["id"]) if (isinstance(first_q.get("id"), str) and len(first_q["id"]) == 36) else uuid.uuid4()
        first_turn = InterviewTurn(
            interview_id=interview.id,
            question_id=q_id,
            turn_index=0,
            question_asked=first_q["question_text"],
            response_transcript=None
        )
        db.add(first_turn)
        
    first_question_text = questions[0]["question_text"] if questions else "Tell me about your technical background."
    formatted_questions = [
        {
            "id": str(q.get("id", uuid.uuid4())),
            "topic": q["topic"],
            "question_text": q["question_text"],
            "expected_keywords": q.get("expected_keywords", [])
        }
        for q in questions
    ]

    await db.commit()
    await db.refresh(interview)
    
    return SessionResponse(
        id=interview.id,
        status=interview.status,
        scheduled_at=interview.scheduled_at,
        first_question=first_question_text,
        questions=formatted_questions
    )


@router.post("/{interview_id}/turns", response_model=TurnResponse)
async def submit_turn(
    interview_id: uuid.UUID,
    payload: TurnSubmissionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    stmt = (
        select(Interview)
        .options(
            selectinload(Interview.questions),
            selectinload(Interview.turns),
            selectinload(Interview.resume),
            selectinload(Interview.job_description)
        )
        .filter(Interview.id == interview_id)
    )
    res = await db.execute(stmt)
    interview = res.scalars().first()
    if not interview:
        raise NotFoundException("Interview session not found")

    if interview.status == "completed" or interview.status == "evaluated":
        raise ValidationException("Interview is already completed")

    response_text = payload.response_text
    if payload.response_audio_base64:
        try:
            audio_bytes = base64.b64decode(payload.response_audio_base64)
            temp_dir = Path("./temp_audio")
            temp_dir.mkdir(exist_ok=True)
            temp_file = temp_dir / f"turn_{uuid.uuid4().hex}.wav"
            temp_file.write_bytes(audio_bytes)
            
            speech_service = LocalSpeechService()
            response_text = await speech_service.transcribe_audio(temp_file)
            
            if temp_file.exists():
                os.remove(temp_file)
        except Exception as e:
            raise ValidationException(f"Failed to transcribe audio: {e}")

    if not response_text:
        response_text = ""

    turns = sorted(interview.turns, key=lambda t: t.turn_index)
    if not turns:
        raise ValidationException("No turns found for this interview. Initialize session first.")

    last_turn = turns[-1]
    last_turn.response_transcript = response_text
    last_turn.latency_seconds = payload.latency_seconds

    # Construct state for evaluation
    q_plan = []
    for q in sorted(interview.questions, key=lambda x: x.sequence_order):
        q_plan.append({
            "id": str(q.id),
            "topic": q.topic,
            "question_text": q.question_text,
            "expected_keywords": [k.strip() for k in q.expected_keywords.split(",") if k.strip()],
            "status": "asked" if any(t.question_asked == q.question_text for t in turns) else "pending"
        })

    turns_history = []
    planned_questions_texts = {q.question_text for q in interview.questions}
    for t in turns:
        turns_history.append({
            "turn_index": t.turn_index,
            "question": t.question_asked,
            "answer": t.response_transcript,
            "score": t.turn_score,
            "evidence": t.score_evidence,
            "follow_ups_asked": 0
        })

    # Track follow-up counts
    for idx, turn in enumerate(turns_history):
        if turn["question"] not in planned_questions_texts:
            cnt = 0
            for prev in reversed(turns_history[:idx]):
                if prev["question"] not in planned_questions_texts:
                    cnt += 1
                else:
                    break
            turn["follow_ups_asked"] = cnt

    asked_planned = [t.question_asked for t in turns if t.question_asked in planned_questions_texts]
    current_question_index = len(asked_planned) - 1 if asked_planned else 0
    if current_question_index < 0:
        current_question_index = 0

    state = {
        "interview_id": str(interview.id),
        "candidate_name": interview.resume.candidate_name,
        "job_title": interview.job_description.title,
        "parsed_resume": interview.resume.parsed_attributes,
        "parsed_jd": interview.job_description.parsed_attributes,
        "questions_plan": q_plan,
        "current_question_index": current_question_index,
        "turns_history": turns_history,
        "last_turn_latency": payload.latency_seconds,
        "overall_recommendation": None,
        "is_completed": False
    }

    evaluator = EvaluatorNode()
    state_after_eval = await evaluator.execute(state)
    if "turns_history" in state_after_eval:
        state["turns_history"] = state_after_eval["turns_history"]
    
    updated_turn_data = state["turns_history"][-1]
    last_turn.turn_score = updated_turn_data.get("score")
    last_turn.score_evidence = updated_turn_data.get("evidence")
    
    next_step = route_after_evaluation(state)
    
    next_question_to_ask = ""
    is_followup = False
    is_last = False

    interviewer = InterviewerNode()

    if next_step == "interviewer":
        state["is_followup_turn"] = True
        state["turns_history"] = state_after_eval.get("turns_history", [])
        interviewer_res = await interviewer.execute(state)
        next_question_to_ask = interviewer_res.get("next_question_to_ask", "")
        is_followup = True
    else:
        state["current_question_index"] += 1
        next_route = route_after_increment(state)
        if next_route == "interviewer":
            interviewer_res = await interviewer.execute(state)
            next_question_to_ask = interviewer_res.get("next_question_to_ask", "")
            is_followup = False
        else:
            reporter = ReporterNode()
            state["turns_history"] = state_after_eval.get("turns_history", [])
            report_res = await reporter.execute(state)
            
            final_data = report_res["final_report_data"]
            report = EvaluationReport(
                interview_id=interview.id,
                overall_score=final_data["overall_score"],
                recommendation=final_data["recommendation"],
                primary_summary=final_data["primary_summary"],
                details=final_data["details"]
            )
            db.add(report)
            interview.status = "completed"
            is_last = True

    next_question_audio_base64 = None
    if next_question_to_ask:
        matching_q_id = None
        for q in interview.questions:
            if q.question_text == next_question_to_ask:
                matching_q_id = q.id
                break
        if not matching_q_id:
            current_planned_q = interview.questions[current_question_index] if current_question_index < len(interview.questions) else None
            matching_q_id = current_planned_q.id if current_planned_q else uuid.uuid4()

        next_turn = InterviewTurn(
            interview_id=interview.id,
            question_id=matching_q_id,
            turn_index=len(turns),
            question_asked=next_question_to_ask,
            response_transcript=None
        )
        db.add(next_turn)
        
        try:
            speech_service = LocalSpeechService()
            output_dir = Path("./tts_output")
            wav_path = await speech_service.synthesize_speech(next_question_to_ask, output_dir)
            if wav_path and wav_path.exists():
                audio_data = wav_path.read_bytes()
                next_question_audio_base64 = base64.b64encode(audio_data).decode("utf-8")
                os.remove(wav_path)
        except Exception:
            pass

    await db.commit()
    
    return TurnResponse(
        next_question=next_question_to_ask,
        next_question_audio_base64=next_question_audio_base64,
        is_last=is_last
    )
