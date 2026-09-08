from typing import Dict, Any
from src.agents.prompts import templates


class PromptRegistry:
    """
    Central repository for version-controlled prompts. Enforces consistency 
    and auditing compliance for AI prompts utilized in agent workflows.
    """
    
    _registry: Dict[str, Dict[str, str]] = {
        "planner": {
            "version": "1.0.0",
            "system": templates.PLANNER_SYSTEM,
            "user": templates.PLANNER_USER_TEMPLATE
        },
        "interviewer": {
            "version": "1.0.0",
            "system": templates.INTERVIEWER_SYSTEM,
            "user": templates.INTERVIEWER_USER_TEMPLATE
        },
        "evaluator": {
            "version": "1.0.0",
            "system": templates.EVALUATOR_SYSTEM,
            "user": templates.EVALUATOR_USER_TEMPLATE
        },
        "reporter": {
            "version": "1.0.0",
            "system": templates.REPORTER_SYSTEM,
            "user": templates.REPORTER_USER_TEMPLATE
        }
    }

    @classmethod
    def get_metadata(cls, prompt_key: str) -> Dict[str, str]:
        """
        Retrieves registration specifications including prompt template version tags.
        """
        if prompt_key not in cls._registry:
            raise KeyError(f"Prompt template key '{prompt_key}' is not registered.")
        return {
            "key": prompt_key,
            "version": cls._registry[prompt_key]["version"]
        }

    @classmethod
    def get_system_prompt(cls, prompt_key: str) -> str:
        """
        Retrieves the system instruction prompt for a given key.
        """
        if prompt_key not in cls._registry:
            raise KeyError(f"Prompt template key '{prompt_key}' is not registered.")
        return cls._registry[prompt_key]["system"]

    @classmethod
    def compile_user_prompt(cls, prompt_key: str, **variables: Any) -> str:
        """
        Fills out a user prompt template using variable replacements.
        """
        if prompt_key not in cls._registry:
            raise KeyError(f"Prompt template key '{prompt_key}' is not registered.")
        
        user_template = cls._registry[prompt_key]["user"]
        try:
            return user_template.format(**variables)
        except KeyError as e:
            raise ValueError(
                f"Missing prompt compilation parameter '{e.args[0]}' for template '{prompt_key}'"
            )
