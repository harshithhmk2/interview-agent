from typing import Dict, Any, List, Optional, Union
from pydantic import BaseModel, Field
from src.agents.state import InterviewState
from src.agents.prompts.registry import PromptRegistry
from src.services.llm import ILLMClient, get_llm_client

class CategoryScoreDetail(BaseModel):
    """
    Sub-schema representing score details for a specific evaluation category.
    """
    score: float = Field(..., ge=0.0, le=10.0)
    evidence: str = Field(..., description="Transcript justification citing candidate response quotes")


class ReporterOutputResponse(BaseModel):
    """
    Structured model for generated candidate evaluation reports.
    """
    overall_score: float = Field(..., ge=0.0, le=10.0)
    recommendation: str = Field(
        ..., description="Overall hiring recommendation. Must be exactly 'hire', 'no_hire', or 'follow_up'"
    )
    primary_summary: str = Field(
        ..., description="Comprehensive executive summary detailing candidate performance"
    )
    details: Union[Dict[str, CategoryScoreDetail], Dict[str, Any], str] = Field(
        default_factory=dict, description="Topic/category mapping to scores and supporting citations"
    )


class ReporterNode:
    """
    LangGraph action node responsible for synthesizing the candidate transcript
    into a final recruiter-ready evaluation report.
    """
    def __init__(self, llm_client: Optional[ILLMClient] = None) -> None:
        self.llm_client = llm_client

    def _get_client(self) -> ILLMClient:
        return self.llm_client or get_llm_client("reporter")

    async def execute(self, state: InterviewState) -> Dict[str, Any]:
        """
        Gathers turn history transcript records, submits them to the LLM to run
        cross-turn analysis, and returns the final evaluation schema parameters.
        """
        turns_history = state.get("turns_history", [])
        candidate_name = state.get("candidate_name", "Candidate")
        job_title = state.get("job_title", "Target Role")

        # Compile turn details into a structured transcript record
        transcript_snippets = []
        for turn in turns_history:
            transcript_snippets.append(
                f"Turn {turn['turn_index'] + 1}:\n"
                f"- Question Asked: '{turn['question']}'\n"
                f"- Candidate Answer: '{turn['answer'] or '(Empty answer)'}'\n"
                f"- Score: {turn['score']}/10.0\n"
                f"- Evaluator Citations: {turn['evidence']}\n"
            )
        transcript_details = "\n".join(transcript_snippets)

        # Compile prompts
        user_prompt = PromptRegistry.compile_user_prompt(
            prompt_key="reporter",
            candidate_name=candidate_name,
            job_title=job_title,
            transcript_details=transcript_details
        )
        system_instruction = PromptRegistry.get_system_prompt("reporter")

        # Request report compilation
        res = await self._get_client().generate_structured_json(
            prompt=user_prompt,
            response_schema=ReporterOutputResponse,
            system_instruction=system_instruction
        )

        # Normalize recommendation value to ensure DB integrity
        rec_val = res.recommendation.lower().strip().replace(" ", "_")
        if rec_val not in ["hire", "no_hire", "follow_up"]:
            rec_val = "follow_up"

        # Map details to raw dict structures safely
        details_dict = {}
        if isinstance(res.details, dict):
            for category, cat_val in res.details.items():
                if isinstance(cat_val, CategoryScoreDetail):
                    details_dict[category] = {"score": cat_val.score, "evidence": cat_val.evidence}
                elif isinstance(cat_val, dict):
                    details_dict[category] = {
                        "score": float(cat_val.get("score", res.overall_score)),
                        "evidence": str(cat_val.get("evidence", ""))
                    }
                else:
                    details_dict[category] = {"score": res.overall_score, "evidence": str(cat_val)}
        elif isinstance(res.details, str):
            details_dict["General Evaluation"] = {"score": res.overall_score, "evidence": res.details}
        else:
            details_dict["General Evaluation"] = {"score": res.overall_score, "evidence": res.primary_summary}

        return {
            "overall_recommendation": rec_val,
            "is_completed": True,
            "final_report_data": {
                "overall_score": res.overall_score,
                "recommendation": rec_val,
                "primary_summary": res.primary_summary,
                "details": details_dict
            }
        }
