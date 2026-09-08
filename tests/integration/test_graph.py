import pytest
from unittest.mock import MagicMock, AsyncMock, patch

from src.agents.state import InterviewState
from src.agents.nodes.planner import PlannerNode, InterviewPlanResponse, PlannedQuestion
from src.agents.nodes.interviewer import InterviewerNode, FollowUpQuestionResponse
from src.agents.nodes.evaluator import EvaluatorNode, EvaluationResponse
from src.agents.nodes.reporter import ReporterNode, ReporterOutputResponse, CategoryScoreDetail
from src.agents.graph import (
    planner_step,
    interviewer_step,
    evaluator_step,
    increment_index_step,
    reporter_step,
    route_after_evaluation,
    route_after_increment
)


@pytest.fixture
def initial_state() -> InterviewState:
    return {
        "interview_id": "test-session-123",
        "candidate_name": "Developer Candidate",
        "job_title": "Senior Engineer",
        "parsed_resume": {"skills": ["Python", "FastAPI"], "experience_years": 4.0},
        "parsed_jd": {"tech_stack": ["Python", "FastAPI", "SQLAlchemy"]},
        "questions_plan": [],
        "current_question_index": 0,
        "turns_history": [],
        "last_turn_latency": 0.0,
        "overall_recommendation": None,
        "is_completed": False
    }


@pytest.mark.asyncio
async def test_planner_node_execution(initial_state):
    # Setup mock LLM response
    mock_plan = InterviewPlanResponse(
        questions=[
            PlannedQuestion(topic="Python", question_text="What is PEP-8?", expected_keywords=["formatting"]),
            PlannedQuestion(topic="FastAPI", question_text="What are Depends?", expected_keywords=["injection"])
        ]
    )
    mock_llm = MagicMock()
    mock_llm.generate_structured_json = AsyncMock(return_value=mock_plan)

    node = PlannerNode(llm_client=mock_llm)
    result = await node.execute(initial_state)

    assert len(result["questions_plan"]) == 2
    assert result["current_question_index"] == 0
    assert result["is_completed"] is False
    assert result["questions_plan"][0]["topic"] == "Python"
    assert result["questions_plan"][0]["question_text"] == "What is PEP-8?"
    assert result["questions_plan"][0]["status"] == "pending"


@pytest.mark.asyncio
async def test_interviewer_node_selects_planned_question(initial_state):
    # Setup state with a plan
    initial_state["questions_plan"] = [
        {"id": "q1", "topic": "Python", "question_text": "What is PEP-8?", "expected_keywords": [], "status": "pending"},
        {"id": "q2", "topic": "FastAPI", "question_text": "Explain Depends", "expected_keywords": [], "status": "pending"}
    ]
    initial_state["current_question_index"] = 0

    mock_llm = MagicMock()
    node = InterviewerNode(llm_client=mock_llm)
    result = await node.execute(initial_state)

    assert result["next_question_to_ask"] == "What is PEP-8?"
    assert result["is_followup_turn"] is False
    assert result["questions_plan"][0]["status"] == "asked"


@pytest.mark.asyncio
async def test_interviewer_node_generates_adaptive_followup(initial_state):
    # Setup state where last score is shallow
    initial_state["questions_plan"] = [
        {"id": "q1", "topic": "Python", "question_text": "What is PEP-8?", "expected_keywords": [], "status": "asked"}
    ]
    initial_state["current_question_index"] = 0
    initial_state["turns_history"] = [
        {
            "turn_index": 0,
            "question": "What is PEP-8?",
            "answer": "It is just style.",
            "score": 4.5,
            "evidence": "Candidate gave a very shallow definition.",
            "follow_ups_asked": 0
        }
    ]

    mock_followup = FollowUpQuestionResponse(
        followup_question="Could you detail specific rules in PEP-8 like indentation?"
    )
    mock_llm = MagicMock()
    mock_llm.generate_structured_json = AsyncMock(return_value=mock_followup)

    node = InterviewerNode(llm_client=mock_llm)
    result = await node.execute(initial_state)

    assert result["next_question_to_ask"] == "Could you detail specific rules in PEP-8 like indentation?"
    assert result["is_followup_turn"] is True


@pytest.mark.asyncio
async def test_evaluator_node_execution(initial_state):
    # Setup turn history requiring evaluation
    initial_state["questions_plan"] = [
        {"id": "q1", "topic": "Python", "question_text": "What is PEP-8?", "expected_keywords": ["style"], "status": "asked"}
    ]
    initial_state["current_question_index"] = 0
    initial_state["turns_history"] = [
        {
            "turn_index": 0,
            "question": "What is PEP-8?",
            "answer": "PEP-8 is the Python coding style guide.",
            "score": None,
            "evidence": None,
            "follow_ups_asked": 0
        }
    ]

    mock_eval = EvaluationResponse(
        score=9.0,
        evidence="Candidate accurately named the guide."
    )
    mock_llm = MagicMock()
    mock_llm.generate_structured_json = AsyncMock(return_value=mock_eval)

    node = EvaluatorNode(llm_client=mock_llm)
    result = await node.execute(initial_state)

    assert result["turns_history"][0]["score"] == 9.0
    assert result["turns_history"][0]["evidence"] == "Candidate accurately named the guide."


@pytest.mark.asyncio
async def test_reporter_node_execution(initial_state):
    # Setup finished interview turns
    initial_state["turns_history"] = [
        {
            "turn_index": 0,
            "question": "What is PEP-8?",
            "answer": "Python style guide.",
            "score": 8.0,
            "evidence": "Named guide.",
            "follow_ups_asked": 0
        }
    ]
    
    mock_report = ReporterOutputResponse(
        overall_score=8.0,
        recommendation="hire",
        primary_summary="Good candidate.",
        details={
            "Python": CategoryScoreDetail(score=8.0, evidence="Good knowledge")
        }
    )
    mock_llm = MagicMock()
    mock_llm.generate_structured_json = AsyncMock(return_value=mock_report)

    node = ReporterNode(llm_client=mock_llm)
    result = await node.execute(initial_state)

    assert result["overall_recommendation"] == "hire"
    assert result["is_completed"] is True
    assert result["final_report_data"]["overall_score"] == 8.0
    assert result["final_report_data"]["details"]["Python"]["score"] == 8.0


def test_routing_logic_after_evaluation():
    # Low score, follow-ups remaining -> route to interviewer for follow-up
    state_low_score = {
        "turns_history": [
            {"turn_index": 0, "question": "Q1", "answer": "A1", "score": 4.0, "follow_ups_asked": 0}
        ]
    }
    assert route_after_evaluation(state_low_score) == "interviewer"

    # Low score, follow-ups exhausted -> route to increment index
    state_no_budget = {
        "turns_history": [
            {"turn_index": 0, "question": "Q1", "answer": "A1", "score": 4.0, "follow_ups_asked": 2}
        ]
    }
    assert route_after_evaluation(state_no_budget) == "increment_index"

    # High score -> route to increment index
    state_high_score = {
        "turns_history": [
            {"turn_index": 0, "question": "Q1", "answer": "A1", "score": 8.0, "follow_ups_asked": 0}
        ]
    }
    assert route_after_evaluation(state_high_score) == "increment_index"


def test_routing_logic_after_increment():
    # Index within questions plan length -> loop back to interviewer
    state_more_questions = {
        "current_question_index": 1,
        "questions_plan": [{"id": "q1"}, {"id": "q2"}]
    }
    assert route_after_increment(state_more_questions) == "interviewer"

    # Index completed -> route to reporter
    state_done = {
        "current_question_index": 2,
        "questions_plan": [{"id": "q1"}, {"id": "q2"}]
    }
    assert route_after_increment(state_done) == "reporter"


@pytest.mark.asyncio
async def test_increment_index_step():
    state = {"current_question_index": 1}
    result = await increment_index_step(state)
    assert result["current_question_index"] == 2
