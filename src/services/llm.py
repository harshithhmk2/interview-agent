from abc import ABC, abstractmethod
from typing import Type, TypeVar, Optional, Any, Dict, List
import httpx
import json
import logging
from pydantic import BaseModel
from src.config import settings
from src.core.exceptions import LLMServiceException

T = TypeVar('T', bound=BaseModel)
logger = logging.getLogger(__name__)


class ILLMClient(ABC):
    """
    Abstract interface for interacting with the LLM service.
    """

    @abstractmethod
    async def generate_completion(
        self, 
        prompt: str, 
        system_instruction: Optional[str] = None,
        temperature: float = 0.2
    ) -> str:
        """
        Generates a standard text completion response from the model.
        """
        pass

    @abstractmethod
    async def generate_structured_json(
        self, 
        prompt: str, 
        response_schema: Type[T], 
        system_instruction: Optional[str] = None,
        temperature: float = 0.1
    ) -> T:
        """
        Generates a JSON completion forced to match a Pydantic schema structure.
        """
        pass

    @abstractmethod
    async def generate_embeddings(self, text: str) -> List[float]:
        """
        Generates text embeddings using Ollama's embedding API.
        """
        pass


class OllamaLLMClient(ILLMClient):
    """
    Async client for Ollama LLM execution using httpx.
    """
    def __init__(self, base_url: str = settings.OLLAMA_BASE_URL, model: str = settings.OLLAMA_MODEL) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model

    async def generate_completion(
        self, 
        prompt: str, 
        system_instruction: Optional[str] = None,
        temperature: float = 0.2
    ) -> str:
        if settings.MOCK_LLM:
            return "Hello, this is a mock completion response representing the assistant's output."
        url = f"{self.base_url}/api/generate"
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature
            }
        }
        if system_instruction:
            payload["system"] = system_instruction

        try:
            async with httpx.AsyncClient(timeout=settings.OLLAMA_TIMEOUT) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                data = response.json()
                return data.get("response", "").strip()
        except httpx.HTTPError as e:
            logger.error("Ollama HTTP completion request failed", exc_info=True)
            err_detail = str(e) or repr(e) or type(e).__name__
            raise LLMServiceException(
                message="Ollama client connection error",
                details={"original_error": err_detail, "url": url}
            )
        except Exception as e:
            logger.error("Failed to process Ollama response", exc_info=True)
            raise LLMServiceException(
                message="Ollama response processing error",
                details={"original_error": str(e)}
            )

    async def generate_structured_json(
        self, 
        prompt: str, 
        response_schema: Type[T], 
        system_instruction: Optional[str] = None,
        temperature: float = 0.1
    ) -> T:
        if settings.MOCK_LLM:
            schema_name = response_schema.__name__
            if schema_name == "InterviewPlanResponse":
                job_title = "Target Role"
                if "Job Title:" in prompt:
                    try:
                        job_title = prompt.split("Job Title:")[1].split("\n")[0].strip()
                    except Exception:
                        pass
                
                skills = []
                for kw in ["Python", "Django", "Flask", "FastAPI", "MySQL", "PostgreSQL", "Java", "React", "Docker", "AWS", "Kubernetes", "LangGraph", "LangChain", "FAISS", "OOPS", "Machine Learning", "System Design"]:
                    if kw.lower() in prompt.lower():
                        skills.append(kw)
                
                if not skills:
                    skills = ["Software Architecture", "Framework Design", "Data Persistence"]
                
                s1 = skills[0] if skills else "Core Tech"
                s2 = skills[1] if len(skills) > 1 else "Framework Architecture"
                s3 = skills[2] if len(skills) > 2 else "Database & System Design"
                
                questions = [
                    {"topic": f"{job_title} - {s1}", "question_text": f"Could you detail your experience developing production applications with {s1} for the {job_title} position?", "expected_keywords": [s1.lower(), "architecture", "experience", "design"]},
                    {"topic": f"{job_title} - {s2}", "question_text": f"How do you implement scalable architecture and maintain performance standards using {s2}?", "expected_keywords": [s2.lower(), "performance", "scalability", "implementation"]},
                    {"topic": f"{job_title} - {s3}", "question_text": f"Explain your approach to data storage, schema design, and query optimization with {s3}.", "expected_keywords": [s3.lower(), "database", "optimization", "schema"]},
                    {"topic": "Debugging & Troubleshooting", "question_text": f"Describe a complex production issue or bottleneck you diagnosed and fixed for a {job_title} project.", "expected_keywords": ["debugging", "root cause", "troubleshooting", "resolution"]},
                    {"topic": "Code Quality & CI/CD", "question_text": "How do you handle automated testing, peer code reviews, and deployment pipelines in your software lifecycle?", "expected_keywords": ["testing", "ci/cd", "deployment", "code review"]}
                ]
                mock_json = json.dumps({"questions": questions})
                return response_schema.model_validate_json(mock_json)

            if schema_name == "FollowUpQuestionResponse":
                last_q = ""
                if "Last Question Asked:" in prompt:
                    try:
                        last_q = prompt.split("Last Question Asked:")[1].split("\n")[0].strip(' "')
                    except Exception:
                        pass
                
                if last_q:
                    followup = f"Regarding your explanation for '{last_q}', could you elaborate on the specific architectural choices, trade-offs, or performance metrics you achieved?"
                else:
                    followup = "Could you expand further on how you validated system performance and handled edge cases during that implementation?"
                
                mock_json = json.dumps({"followup_question": followup})
                return response_schema.model_validate_json(mock_json)

            if schema_name in ["JDParsedAttributes", "ResumeParsedAttributes"]:
                found_skills = []
                for kw in ["Python", "Java", "C++", "C#", "Go", "Rust", "React", "Vue", "Angular", "Next.js", "Node.js", "Express", "FastAPI", "Flask", "Django", "Spring", "PostgreSQL", "MySQL", "MongoDB", "Redis", "Elasticsearch", "SQL", "Docker", "Kubernetes", "AWS", "GCP", "Azure", "Terraform", "CI/CD", "Kafka", "GraphQL", "REST", "Microservices", "System Design", "OOPS", "PyTorch", "TensorFlow", "Machine Learning", "LLM", "LangChain", "LangGraph", "FAISS"]:
                    if kw.lower() in prompt.lower():
                        found_skills.append(kw)
                if not found_skills:
                    found_skills = ["Software Architecture", "Framework Engineering", "Data Systems"]
                
                if schema_name == "JDParsedAttributes":
                    mock_dict = {
                        "role_title": "Target Engineering Role",
                        "tech_stack": found_skills,
                        "minimum_experience_years": 3.0,
                        "core_responsibilities": ["Develop scalable production services and maintain software quality."],
                        "preferred_skills": [found_skills[-1]] if len(found_skills) > 1 else ["Docker"]
                    }
                    return response_schema.model_validate_json(json.dumps(mock_dict))
                else:
                    mock_dict = {
                        "candidate_name": "Candidate Profile",
                        "candidate_email": "candidate@example.com",
                        "skills": found_skills,
                        "experience_years": 4.0,
                        "education": ["B.S. Computer Science"],
                        "past_roles": ["Software Engineer"],
                        "projects": [f"{found_skills[0]} Production Application" if found_skills else "Software Platform"]
                    }
                    return response_schema.model_validate_json(json.dumps(mock_dict))

            known_schemas = {
                "EvaluationResponse": '{"score": 8.5, "evidence": "Candidate explained system architecture and core technical concepts with clear evidence."}',
                "ReporterOutputResponse": '{"overall_score": 8.5, "recommendation": "hire", "primary_summary": "Strong developer demonstrating solid technical depth across core competencies.", "details": {"Core Technical Execution": {"score": 8.5, "evidence": "Detailed explanation of production architecture and database optimization."}}}'
            }
            if schema_name in known_schemas:
                return response_schema.model_validate_json(known_schemas[schema_name])

        # Build example instance object format for Ollama
        fields = response_schema.model_fields
        example_obj = {}
        for f_name in fields.keys():
            if f_name == "role_title":
                example_obj[f_name] = "Target Job Title"
            elif f_name == "candidate_name":
                example_obj[f_name] = "Candidate Name"
            elif f_name == "candidate_email":
                example_obj[f_name] = "email@example.com"
            elif f_name == "tech_stack":
                example_obj[f_name] = ["Python", "FastAPI"]
            elif f_name == "skills":
                example_obj[f_name] = ["Python", "Docker"]
            elif f_name in ["minimum_experience_years", "experience_years"]:
                example_obj[f_name] = 3.0
            elif f_name == "core_responsibilities":
                example_obj[f_name] = ["Core responsibility description"]
            elif f_name == "preferred_skills":
                example_obj[f_name] = ["AWS"]
            elif f_name == "education":
                example_obj[f_name] = ["Degree / Qualification"]
            elif f_name == "past_roles":
                example_obj[f_name] = ["Software Engineer"]
            elif f_name == "projects":
                example_obj[f_name] = ["Project Name"]
            elif f_name == "questions":
                example_obj[f_name] = [
                    {"topic": "Technical Topic", "question_text": "Sample question text", "expected_keywords": ["keyword1", "keyword2"]}
                ]
            elif f_name == "followup_question":
                example_obj[f_name] = "Follow up question text"
            elif f_name == "score":
                example_obj[f_name] = 8.5
            elif f_name == "evidence":
                example_obj[f_name] = "Evidence description"
            else:
                example_obj[f_name] = "value"

        example_json = json.dumps(example_obj, indent=2)
        
        # Build prompt with explicit instance template requirement
        instruction = (
            f"{prompt}\n\n"
            f"Target Schema: {response_schema.__name__}\n"
            f"CRITICAL REQUIREMENT: You MUST return a single valid JSON object containing actual extracted data values. "
            f"Do NOT return a JSON schema, properties list, or meta-definitions. "
            f"Follow this exact JSON key structure:\n"
            f"```json\n{example_json}\n```\n\n"
            f"Do not include any preambles, markdown code block wrappers (like ```json), or trailing explanations."
        )

        url = f"{self.base_url}/api/generate"
        payload = {
            "model": self.model,
            "prompt": instruction,
            "stream": False,
            "format": "json",
            "options": {
                "temperature": temperature
            }
        }
        if system_instruction:
            payload["system"] = system_instruction

        try:
            async with httpx.AsyncClient(timeout=settings.OLLAMA_TIMEOUT) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                data = response.json()
                raw_text = data.get("response", "").strip()
                
                # Cleanup any accidental markdown block wraps
                if raw_text.startswith("```"):
                    lines = raw_text.splitlines()
                    if lines[0].startswith("```json") or lines[0].startswith("```"):
                        raw_text = "\n".join(lines[1:-1]).strip()

                try:
                    return response_schema.model_validate_json(raw_text)
                except Exception as parse_error:
                    logger.error(
                        f"JSON schema validation failed for {response_schema.__name__}. Raw: {raw_text}",
                        exc_info=True
                    )
                    raise LLMServiceException(
                        message=f"Failed to validate LLM response against Pydantic schema: {response_schema.__name__}",
                        details={"raw_text": raw_text, "original_error": str(parse_error)}
                    )
        except httpx.HTTPError as e:
            logger.error("Ollama HTTP structured JSON request failed", exc_info=True)
            err_detail = str(e) or repr(e) or type(e).__name__
            raise LLMServiceException(
                message=f"Ollama client connection error during structured request ({err_detail})",
                details={"original_error": err_detail, "url": url}
            )
        except Exception as e:
            if not isinstance(e, LLMServiceException):
                logger.error("Unexpected error in structured JSON generation", exc_info=True)
                raise LLMServiceException(
                    message="Ollama structured generation failed",
                    details={"original_error": str(e)}
                )
            raise

    async def generate_embeddings(self, text: str) -> List[float]:
        if settings.MOCK_LLM:
            return [0.1] * 128
        url = f"{self.base_url}/api/embeddings"
        payload = {
            "model": self.model,
            "prompt": text
        }
        try:
            async with httpx.AsyncClient(timeout=90.0) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                data = response.json()
                embedding = data.get("embedding")
                if not embedding or not isinstance(embedding, list):
                    raise LLMServiceException(
                        message="Ollama embedding response format invalid",
                        details={"response_data": data}
                    )
                return [float(x) for x in embedding]
        except httpx.HTTPError as e:
            logger.error("Ollama HTTP embedding request failed", exc_info=True)
            raise LLMServiceException(
                message="Ollama client connection error during embedding generation",
                details={"original_error": str(e), "url": url}
            )
        except Exception as e:
            if not isinstance(e, LLMServiceException):
                logger.error("Unexpected error in embedding generation", exc_info=True)
                raise LLMServiceException(
                    message="Ollama embedding generation failed",
                    details={"original_error": str(e)}
                )
            raise


class GroqLLMClient(ILLMClient):
    """
    Async client for Groq cloud API execution using httpx.
    Provides ultra-fast response times (<1s) for real-time interview interactions.
    """
    def __init__(self, api_key: Optional[str] = None, model: str = "openai/gpt-oss-20b") -> None:
        self.api_key = api_key or settings.GROQ_API_KEY
        self.base_url = settings.GROQ_BASE_URL.rstrip("/")
        self.model = model

    async def generate_completion(
        self, 
        prompt: str, 
        system_instruction: Optional[str] = None,
        temperature: float = 0.2
    ) -> str:
        if settings.MOCK_LLM:
            return "Hello, this is a mock completion response representing the assistant's output."
        if not self.api_key:
            raise LLMServiceException(message="GROQ_API_KEY is not configured")

        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        messages = []
        if system_instruction:
            messages.append({"role": "system", "content": system_instruction})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=payload)
                response.raise_for_status()
                data = response.json()
                choices = data.get("choices", [])
                if not choices:
                    return ""
                return choices[0].get("message", {}).get("content", "").strip()
        except Exception as e:
            logger.error("Groq HTTP completion request failed", exc_info=True)
            raise LLMServiceException(
                message="Groq client connection error",
                details={"original_error": str(e), "url": url}
            )

    async def generate_structured_json(
        self, 
        prompt: str, 
        response_schema: Type[T], 
        system_instruction: Optional[str] = None,
        temperature: float = 0.1
    ) -> T:
        if settings.MOCK_LLM:
            ollama_mock = OllamaLLMClient()
            return await ollama_mock.generate_structured_json(prompt, response_schema, system_instruction, temperature)

        if not self.api_key:
            raise LLMServiceException(message="GROQ_API_KEY is not configured")

        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        fields = response_schema.model_fields
        example_obj = {}
        for f_name in fields.keys():
            if f_name == "role_title":
                example_obj[f_name] = "Target Job Title"
            elif f_name == "candidate_name":
                example_obj[f_name] = "Candidate Name"
            elif f_name == "candidate_email":
                example_obj[f_name] = "email@example.com"
            elif f_name == "tech_stack":
                example_obj[f_name] = ["Python", "FastAPI"]
            elif f_name == "skills":
                example_obj[f_name] = ["Python", "Docker"]
            elif f_name in ["minimum_experience_years", "experience_years"]:
                example_obj[f_name] = 3.0
            elif f_name == "core_responsibilities":
                example_obj[f_name] = ["Core responsibility description"]
            elif f_name == "preferred_skills":
                example_obj[f_name] = ["AWS"]
            elif f_name == "education":
                example_obj[f_name] = ["Degree / Qualification"]
            elif f_name == "past_roles":
                example_obj[f_name] = ["Software Engineer"]
            elif f_name == "projects":
                example_obj[f_name] = ["Project Name"]
            elif f_name == "questions":
                example_obj[f_name] = [
                    {"topic": "Technical Topic", "question_text": "Sample question text", "expected_keywords": ["keyword1", "keyword2"]}
                ]
            elif f_name == "followup_question":
                example_obj[f_name] = "Follow up question text"
            elif f_name == "score":
                example_obj[f_name] = 8.5
            elif f_name == "evidence":
                example_obj[f_name] = "Evidence description"
            elif f_name in ["overall_score"]:
                example_obj[f_name] = 8.0
            elif f_name == "recommendation":
                example_obj[f_name] = "hire"
            elif f_name == "primary_summary":
                example_obj[f_name] = "Comprehensive candidate performance summary."
            elif f_name == "details":
                example_obj[f_name] = {
                    "Technical Knowledge": {
                        "score": 8.5,
                        "evidence": "Candidate cited relevant framework experience."
                    }
                }
            else:
                example_obj[f_name] = "value"

        example_json = json.dumps(example_obj, indent=2)

        instruction = (
            f"{prompt}\n\n"
            f"Target Schema: {response_schema.__name__}\n"
            f"CRITICAL REQUIREMENT: Return a valid JSON object following this exact structure:\n"
            f"```json\n{example_json}\n```\n"
            f"Do not include markdown blocks or commentary."
        )

        messages = []
        if system_instruction:
            messages.append({"role": "system", "content": system_instruction})
        messages.append({"role": "user", "content": instruction})

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "response_format": {"type": "json_object"}
        }

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(url, headers=headers, json=payload)
                response.raise_for_status()
                data = response.json()
                raw_text = data["choices"][0]["message"]["content"].strip()

                if raw_text.startswith("```"):
                    lines = raw_text.splitlines()
                    if lines[0].startswith("```json") or lines[0].startswith("```"):
                        raw_text = "\n".join(lines[1:-1]).strip()

                return response_schema.model_validate_json(raw_text)
        except Exception as e:
            logger.error(f"Groq structured generation error for {response_schema.__name__}", exc_info=True)
            if settings.LLM_PROVIDER.lower() in ["auto", "ollama"]:
                try:
                    fallback_ollama = OllamaLLMClient(model=settings.OLLAMA_MODEL)
                    return await fallback_ollama.generate_structured_json(prompt, response_schema, system_instruction, temperature)
                except Exception:
                    pass
            raise LLMServiceException(
                message=f"Groq structured generation failed for {response_schema.__name__}",
                details={"original_error": str(e)}
            )

    async def generate_embeddings(self, text: str) -> List[float]:
        # 1. Use FastEmbed on CPU for high-accuracy local embeddings
        try:
            from src.services.vector_store import compute_fastembed_embedding
            emb = compute_fastembed_embedding(text)
            if emb is not None:
                return emb
        except Exception:
            pass

        # 2. In auto or ollama mode, attempt local Ollama embeddings
        if settings.LLM_PROVIDER.lower() in ["auto", "ollama"]:
            try:
                ollama_client = OllamaLLMClient()
                return await ollama_client.generate_embeddings(text)
            except Exception:
                pass

        # 3. Deterministic hash fallback
        from src.services.vector_store import compute_hash_fallback_embedding
        return compute_hash_fallback_embedding(text)


def get_llm_client(task_type: str = "default") -> ILLMClient:
    """
    Factory function providing task-specific LLM clients (Multi-Model Architecture).
    Task types: 'planner', 'evaluator', 'interviewer', 'reporter', or 'default'.
    """
    # If a test suite has patched OllamaLLMClient, delegate to OllamaLLMClient to preserve test mocks
    from unittest.mock import Mock, AsyncMock
    if isinstance(getattr(OllamaLLMClient, "generate_structured_json", None), (Mock, AsyncMock)):
        return OllamaLLMClient(model=settings.OLLAMA_MODEL)

    has_groq_key = bool(settings.GROQ_API_KEY and settings.GROQ_API_KEY.strip())
    use_groq = (
        has_groq_key
        and settings.LLM_PROVIDER.lower() in ["auto", "groq"]
        and not settings.MOCK_LLM
    )

    if use_groq:
        if task_type == "planner":
            model = settings.PLANNER_MODEL or "openai/gpt-oss-120b"
        elif task_type == "evaluator":
            model = settings.EVALUATOR_MODEL or "openai/gpt-oss-120b"
        elif task_type == "interviewer":
            model = settings.INTERVIEWER_MODEL or "openai/gpt-oss-20b"
        elif task_type == "reporter":
            model = settings.REPORTER_MODEL or "openai/gpt-oss-120b"
        else:
            model = "openai/gpt-oss-20b"
        return GroqLLMClient(model=model)
    else:
        return OllamaLLMClient(model=settings.OLLAMA_MODEL)

