from typing import TypedDict, List, Dict, Any, Optional


class QuestionPlan(TypedDict):
    """
    Represents an item in the structured interview question queue.
    """
    id: str
    topic: str
    question_text: str
    expected_keywords: List[str]
    status: str  # "pending", "asked", "passed", "failed"


class TurnDetail(TypedDict):
    """
    Details of a single Q&A turn between the interviewer and candidate.
    """
    turn_index: int
    question: str
    answer: str
    score: Optional[float]
    evidence: Optional[str]
    follow_ups_asked: int


class InterviewState(TypedDict):
    """
    LangGraph state schema maintaining the context of an interview session.
    """
    # Context IDs
    interview_id: str
    candidate_name: str
    job_title: str
    
    # Static parsed profiles
    parsed_resume: Dict[str, Any]
    parsed_jd: Dict[str, Any]
    
    # State Orchestration
    questions_plan: List[QuestionPlan]
    current_question_index: int
    turns_history: List[TurnDetail]
    
    # Performance tracking
    last_turn_latency: float
    
    # Final AI Assessment
    overall_recommendation: Optional[str]
    is_completed: bool
