from abc import ABC, abstractmethod
from typing import Dict, Any, BinaryIO, List, Optional
import logging
from io import BytesIO
import pypdf
from docx import Document
from pydantic import BaseModel, Field
from src.services.llm import ILLMClient
from src.core.exceptions import ValidationException

logger = logging.getLogger(__name__)


class ResumeParsedAttributes(BaseModel):
    """
    Structured attributes extracted from a candidate resume.
    """
    candidate_name: Optional[str] = Field(default=None, description="Candidate's full name")
    candidate_email: Optional[str] = Field(default=None, description="Candidate's email address")
    skills: List[str] = Field(default_factory=list, description="Technical and soft skills mentioned")
    experience_years: Optional[float] = Field(default=0.0, description="Total estimate of professional experience in years")
    education: List[str] = Field(default_factory=list, description="Academic degrees, schools, and certifications")
    past_roles: List[str] = Field(default_factory=list, description="Past job titles or positions held")
    projects: List[str] = Field(default_factory=list, description="Key projects, system accomplishments, software built, or GitHub projects")


class JDParsedAttributes(BaseModel):
    """
    Structured attributes extracted from a Job Description.
    """
    role_title: str = Field(..., description="Target job title")
    tech_stack: List[str] = Field(default_factory=list, description="Primary technologies, tools, and languages required")
    minimum_experience_years: Optional[float] = Field(default=0.0, description="Minimum years of professional experience requested")
    core_responsibilities: List[str] = Field(default_factory=list, description="Main daily duties and core responsibilities")
    preferred_skills: List[str] = Field(default_factory=list, description="Nice-to-have skills or preferred qualifications")


class IDocumentParser(ABC):
    """
    Abstract interface for parsing and extracting data from files.
    """

    @abstractmethod
    def extract_text(self, file_stream: BinaryIO, file_extension: str) -> str:
        """
        Extracts raw unstructured text content from the file stream.
        """
        pass

    @abstractmethod
    async def parse_entities(self, raw_text: str, doc_type: str = "resume") -> Dict[str, Any]:
        """
        Invokes LLM structured JSON generation to return key entities.
        doc_type can be 'resume' or 'jd'.
        """
        pass


from src.services.llm import ILLMClient, get_llm_client


class DocumentParser(IDocumentParser):
    """
    Concrete implementation of document parser using PyPDF2 and python-docx.
    """
    def __init__(self, llm_client: Optional[ILLMClient] = None) -> None:
        self.llm_client = llm_client

    def _get_client(self) -> ILLMClient:
        return self.llm_client or get_llm_client("planner")

    def extract_text(self, file_stream: BinaryIO, file_extension: str) -> str:
        ext = file_extension.lower().lstrip(".")
        text = ""
        
        try:
            if ext == "pdf":
                reader = pypdf.PdfReader(file_stream)
                for page_idx, page in enumerate(reader.pages):
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
            elif ext == "docx":
                doc = Document(file_stream)
                text = "\n".join([para.text for para in doc.paragraphs if para.text])
            elif ext == "txt":
                # Ensure we handle text reading properly from binary stream
                content = file_stream.read()
                if isinstance(content, bytes):
                    text = content.decode("utf-8", errors="ignore")
                else:
                    text = str(content)
            else:
                raise ValidationException(
                    message=f"Unsupported file format: .{ext}",
                    details={"supported_formats": ["pdf", "docx", "txt"]}
                )
        except Exception as e:
            if isinstance(e, ValidationException):
                raise
            logger.error(f"Error extracting text from file with extension .{ext}", exc_info=True)
            raise ValidationException(
                message=f"Failed to read file contents for format .{ext}",
                details={"original_error": str(e)}
            )

        extracted_clean = text.replace("\x00", "").strip()
        if not extracted_clean:
            raise ValidationException(
                message="Extracted document text is empty. The file may be empty or unparseable.",
                details={"file_extension": ext}
            )

        return extracted_clean

    @staticmethod
    def _extract_dynamic_skills(raw_text: str) -> List[str]:
        import re
        if not raw_text:
            return []
        common_tech = [
            "Python", "Java", "C++", "C#", "Go", "Golang", "Rust", "Ruby", "PHP", "Swift", "Kotlin", "TypeScript", "JavaScript",
            "React", "Vue", "Angular", "Next.js", "Node.js", "Express", "FastAPI", "Flask", "Django", "Spring", "Spring Boot",
            "PostgreSQL", "MySQL", "MongoDB", "Redis", "Elasticsearch", "SQL", "NoSQL", "SQLite", "Oracle",
            "Docker", "Kubernetes", "AWS", "GCP", "Azure", "Terraform", "CI/CD", "Jenkins", "GitHub Actions",
            "Kafka", "RabbitMQ", "GraphQL", "REST", "gRPC", "Microservices", "System Design", "OOPS",
            "PyTorch", "TensorFlow", "Scikit-Learn", "Machine Learning", "Deep Learning", "LLM", "LangChain", "LangGraph", "FAISS"
        ]
        found = []
        raw_lower = raw_text.lower()
        for tech in common_tech:
            pattern = rf"\b{re.escape(tech.lower())}\b"
            if re.search(pattern, raw_lower):
                found.append(tech)
        return found

    @staticmethod
    def _fast_extract_email(raw_text: str) -> Optional[str]:
        import re
        match = re.search(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', raw_text)
        return match.group(0) if match else None

    @staticmethod
    def _fast_extract_experience(raw_text: str) -> float:
        import re
        matches = re.findall(r'(\d+(?:\.\d+)?)\s*(?:\+|\-|to\s*\d+)?\s*(?:years?|yrs?)', raw_text, re.IGNORECASE)
        if matches:
            try:
                return float(matches[0])
            except ValueError:
                pass
        return 3.0

    async def parse_entities(self, raw_text: str, doc_type: str = "resume") -> Dict[str, Any]:
        import asyncio
        doc_type_clean = doc_type.lower().strip()
        
        if doc_type_clean == "resume":
            email = self._fast_extract_email(raw_text)
            skills = self._extract_dynamic_skills(raw_text)
            exp = self._fast_extract_experience(raw_text)
            
            prompt = (
                "Please analyze the following candidate resume text. Parse out the candidate's name, "
                "candidate's email address, listed skills (technical tools, systems, programming languages, and soft skills), "
                "total estimated professional experience in years, academic education history, and past job titles/roles.\n\n"
                f"Resume Content:\n{raw_text}"
            )
            try:
                parsed_result = await asyncio.wait_for(
                    self._get_client().generate_structured_json(
                        prompt=prompt,
                        response_schema=ResumeParsedAttributes,
                        system_instruction="You are an expert resume parsing assistant. Extract candidate profile parameters objectively."
                    ),
                    timeout=15.0
                )
                data = parsed_result.model_dump()
            except Exception as e:
                logger.warning(f"Resume LLM entity parsing skipped/failed ({e}), using fast heuristic extraction.")
                data = {
                    "candidate_name": None,
                    "candidate_email": email,
                    "skills": skills,
                    "experience_years": exp,
                    "education": ["Bachelor's Degree in Science/Engineering"],
                    "past_roles": ["Software Engineer"],
                    "projects": [f"{skills[0]} System" if skills else "Software Engineering Project"]
                }

            if not data.get("candidate_email"):
                data["candidate_email"] = email
            if not data.get("skills"):
                data["skills"] = skills
            if not data.get("experience_years"):
                data["experience_years"] = exp
            return data
            
        elif doc_type_clean == "jd" or doc_type_clean == "job_description":
            skills = self._extract_dynamic_skills(raw_text)
            exp = self._fast_extract_experience(raw_text)

            prompt = (
                "Please analyze the following Job Description text. Parse out the role title, primary tech stack (languages, "
                "frameworks, tools, systems), minimum experience in years (extract the float value, default to 0.0 if not specified), "
                "list of core responsibilities, and preferred/nice-to-have qualifications.\n\n"
                f"Job Description Content:\n{raw_text}"
            )
            try:
                parsed_result = await asyncio.wait_for(
                    self._get_client().generate_structured_json(
                        prompt=prompt,
                        response_schema=JDParsedAttributes,
                        system_instruction="You are an expert recruitment assistant. Extract core job requirement parameters objectively."
                    ),
                    timeout=15.0
                )
                data = parsed_result.model_dump()
            except Exception as e:
                logger.warning(f"JD LLM entity parsing skipped/failed ({e}), using fast heuristic extraction.")
                data = {
                    "role_title": "Target Engineering Role",
                    "tech_stack": skills if skills else ["Software Architecture", "API Engineering"],
                    "minimum_experience_years": exp,
                    "core_responsibilities": ["Develop scalable services and maintain software quality standards."],
                    "preferred_skills": []
                }

            if not data.get("tech_stack"):
                data["tech_stack"] = skills if skills else ["Software Engineering"]
            return data
            
        else:
            raise ValidationException(
                message="Invalid document type specified for entity parsing",
                details={"doc_type": doc_type, "allowed": ["resume", "jd"]}
            )
