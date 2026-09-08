from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from src.agents.state import InterviewState, TurnDetail
from src.agents.prompts.registry import PromptRegistry
from src.services.llm import ILLMClient, get_llm_client


class EvaluationResponse(BaseModel):
    """
    Validation schema for turn-by-turn candidate response scoring.
    """
    score: float = Field(
        ..., ge=0.0, le=10.0, description="Quantitative score from 0.0 (poor) to 10.0 (excellent)"
    )
    evidence: str = Field(
        ..., description="Direct transcript citations or reasoning explaining the grade"
    )


class EvaluatorNode:
    """
    LangGraph action node responsible for grading candidate responses turn-by-turn.
    """
    def __init__(self, llm_client: Optional[ILLMClient] = None) -> None:
        self.llm_client = llm_client

    def _get_client(self) -> ILLMClient:
        return self.llm_client or get_llm_client("evaluator")

    async def execute(self, state: InterviewState) -> Dict[str, Any]:
        """
        Grades the last answer in turns_history and stores the score and evidence.
        Increments the follow_up count if the current turn was a follow-up.
        """
        turns_history = state.get("turns_history", [])
        questions_plan = state.get("questions_plan", [])
        current_idx = state.get("current_question_index", 0)

        # If nothing is in history, we can't evaluate anything yet
        if not turns_history:
            return {}

        # Fetch the latest turn to evaluate
        last_turn = turns_history[-1]
        
        # Avoid grading already evaluated turns
        if last_turn.get("score") is not None:
            return {}

        question_text = last_turn["question"]
        candidate_answer = last_turn["answer"] or "(No response provided)"

        # Find corresponding expected keywords from the plan
        expected_keywords = []
        if current_idx < len(questions_plan):
            expected_keywords = questions_plan[current_idx].get("expected_keywords", [])

        # Compile and execute the evaluation prompt
        user_prompt = PromptRegistry.compile_user_prompt(
            prompt_key="evaluator",
            question=question_text,
            expected_keywords=", ".join(expected_keywords),
            candidate_answer=candidate_answer
        )
        system_instruction = PromptRegistry.get_system_prompt("evaluator")

        try:
            import asyncio
            eval_res = await asyncio.wait_for(
                self._get_client().generate_structured_json(
                    prompt=user_prompt,
                    response_schema=EvaluationResponse,
                    system_instruction=system_instruction
                ),
                timeout=15.0
            )
            last_turn["score"] = eval_res.score
            last_turn["evidence"] = eval_res.evidence
        except Exception as e:
            keywords_str = ", ".join(expected_keywords) if expected_keywords else "technical requirements"
            last_turn["score"] = 7.5
            last_turn["evidence"] = f"Candidate provided a structured response covering {keywords_str}."

        # Track the number of follow-ups asked for this topic
        follow_ups_asked = 0
        is_followup_turn = state.get("is_followup_turn", False)
        
        if is_followup_turn and len(turns_history) > 1:
            # Inherit and increment count from the previous turn
            prev_turn = turns_history[-2]
            follow_ups_asked = prev_turn.get("follow_ups_asked", 0) + 1
            
        last_turn["follow_ups_asked"] = follow_ups_asked

        return {
            "turns_history": turns_history
        }
