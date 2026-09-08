from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from src.agents.state import InterviewState, TurnDetail
from src.agents.prompts.registry import PromptRegistry
from src.services.llm import ILLMClient, get_llm_client


class FollowUpQuestionResponse(BaseModel):
    """
    Structured response schema for generating conversational follow-ups.
    """
    followup_question: str = Field(
        ..., description="A clear, conversational follow-up question to probe deeper on the topic"
    )


class InterviewerNode:
    """
    LangGraph action node responsible for selecting the next planned question
    or formulating an adaptive follow-up.
    """
    def __init__(self, llm_client: Optional[ILLMClient] = None) -> None:
        self.llm_client = llm_client

    def _get_client(self) -> ILLMClient:
        return self.llm_client or get_llm_client("interviewer")

    async def execute(self, state: InterviewState) -> Dict[str, Any]:
        """
        Executes the Interviewer node. Inspects the last turn's score:
        - If score < 6.0 and follow-ups asked < 2, generate an adaptive follow-up.
        - Otherwise, proceed to the next question in the planned question queue.
        """
        questions_plan = state.get("questions_plan", [])
        current_idx = state.get("current_question_index", 0)
        turns_history = state.get("turns_history", [])
        candidate_name = state.get("candidate_name", "Candidate")
        job_title = state.get("job_title", "Target Role")

        # If no plan exists, close out the session
        if not questions_plan:
            return {"is_completed": True}

        # Check score of last turn to determine if follow-up is needed
        ask_followup = False
        last_turn = None
        if turns_history:
            last_turn = turns_history[-1]
            last_score = last_turn.get("score")
            last_followups = last_turn.get("follow_ups_asked", 0)
            
            # If the score was shallow and we have follow-up budget, ask follow-up
            if last_score is not None and last_score < 6.0 and last_followups < 2:
                ask_followup = True

        if ask_followup and last_turn:
            # Format recent turn history details for the LLM
            history_snippets = []
            for idx, turn in enumerate(turns_history[-2:]):
                history_snippets.append(
                    f"Turn {turn['turn_index']}: Asked: '{turn['question']}' | Answered: '{turn['answer']}' | "
                    f"Score: {turn['score']}/10 | Evidence: {turn['evidence']}"
                )
            history_details = "\n".join(history_snippets)

            # Compile interviewer follow-up instructions
            user_prompt = (
                f"We are interviewing {candidate_name} for the position of '{job_title}'.\n"
                f"The candidate's response to the topic was evaluated as shallow.\n"
                f"Last Question Asked: \"{last_turn['question']}\"\n"
                f"Candidate's Answer: \"{last_turn['answer']}\"\n"
                f"Evaluation Score: {last_turn['score']}/10\n"
                f"Evidence of gap: {last_turn['evidence']}\n\n"
                f"Recent Turn Context:\n{history_details}\n\n"
                f"Generate a professional, natural voice-synthesizable follow-up question. "
                f"Drill down on the details they missed, encouraging them to demonstrate their actual capability."
            )
            
            system_instruction = PromptRegistry.get_system_prompt("interviewer")
            try:
                import asyncio
                res = await asyncio.wait_for(
                    self._get_client().generate_structured_json(
                        prompt=user_prompt,
                        response_schema=FollowUpQuestionResponse,
                        system_instruction=system_instruction
                    ),
                    timeout=15.0
                )

                return {
                    # Save the formulated question to be accessed by the session
                    "next_question_to_ask": res.followup_question,
                    "is_followup_turn": True
                }
            except Exception:
                if current_idx < len(questions_plan):
                    planned_q = questions_plan[current_idx]["question_text"]
                    questions_plan[current_idx]["status"] = "asked"
                    return {
                        "next_question_to_ask": planned_q,
                        "is_followup_turn": False,
                        "questions_plan": questions_plan
                    }
                else:
                    return {"is_completed": True}
        else:
            # Move on to the next planned question if available
            if current_idx < len(questions_plan):
                planned_q = questions_plan[current_idx]["question_text"]
                questions_plan[current_idx]["status"] = "asked"
                return {
                    "next_question_to_ask": planned_q,
                    "is_followup_turn": False,
                    "questions_plan": questions_plan
                }
            else:
                return {
                    "is_completed": True
                }
