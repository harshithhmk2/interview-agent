import math
import hashlib
import logging
from typing import List, Dict, Any, Tuple, Optional
from src.schemas.resumes import MatchDetails
from src.services.llm import ILLMClient, get_llm_client

logger = logging.getLogger(__name__)


def compute_hash_fallback_embedding(text: str) -> List[float]:
    """
    Generates a deterministic 128-dimensional mock embedding based on SHA-256 hash.
    Used as a fallback if the local Ollama embedding endpoint is unreachable.
    """
    text_clean = text.lower().strip()
    h = hashlib.sha256(text_clean.encode("utf-8")).digest()
    # Convert bytes to floats between -1.0 and 1.0
    base_vector = [float(b) / 127.5 - 1.0 for b in h]
    # Replicate to obtain 128 dimensions (32 bytes * 4)
    return (base_vector * 4)[:128]


def calculate_cosine_similarity(v1: List[float], v2: List[float]) -> float:
    """
    Calculates cosine similarity between two numeric vectors.
    """
    if len(v1) != len(v2):
        # Truncate or pad to match dimensions if mismatched
        min_len = min(len(v1), len(v2))
        v1, v2 = v1[:min_len], v2[:min_len]

    dot_product = sum(a * b for a, b in zip(v1, v2))
    sum_sq_v1 = sum(a * a for a in v1)
    sum_sq_v2 = sum(b * b for b in v2)
    
    if sum_sq_v1 == 0 or sum_sq_v2 == 0:
        return 0.0
        
    return dot_product / (math.sqrt(sum_sq_v1) * math.sqrt(sum_sq_v2))


_fastembed_model = None

def get_fastembed_model():
    """
    Lazy singleton loader for FastEmbed model (BAAI/bge-small-en-v1.5).
    Runs lightweight ONNX embeddings on CPU without PyTorch dependency.
    """
    global _fastembed_model
    if _fastembed_model is None:
        try:
            from fastembed import TextEmbedding
            _fastembed_model = TextEmbedding(model_name="BAAI/bge-small-en-v1.5")
            logger.info("FastEmbed model (BAAI/bge-small-en-v1.5) initialized successfully.")
        except Exception as e:
            logger.warning(f"FastEmbed initialization failed: {e}")
            _fastembed_model = False
    return _fastembed_model if _fastembed_model is not False else None


def compute_fastembed_embedding(text: str) -> Optional[List[float]]:
    """
    Generates high-accuracy 384-dimensional dense semantic embeddings using FastEmbed on CPU.
    Returns None if FastEmbed model is unavailable or encounters an error.
    """
    model = get_fastembed_model()
    if model is not None:
        try:
            embeddings = list(model.embed([text]))
            if embeddings:
                return [float(x) for x in embeddings[0]]
        except Exception as e:
            logger.warning(f"FastEmbed generation failed for '{text[:20]}...': {e}")
    return None


class SemanticMatcher:
    """
    Service responsible for conducting semantic skills gaps analysis between
    extracted Job Description requirements and Candidate Resume skills.
    """
    def __init__(self, llm_client: Optional[ILLMClient] = None, similarity_threshold: float = 0.70) -> None:
        self.llm_client = llm_client or get_llm_client()
        self.similarity_threshold = similarity_threshold

    async def get_embedding(self, text: str) -> List[float]:
        """
        Attempts to generate embeddings using the LLM client (or FastEmbed),
        falling back to a deterministic hash-based vector on failure.
        """
        try:
            return await self.llm_client.generate_embeddings(text)
        except Exception as e:
            logger.warning(
                f"Embedding generation failed for '{text[:20]}...'. Attempting FastEmbed/hash fallback. Reason: {e}"
            )
            fastembed_emb = compute_fastembed_embedding(text)
            if fastembed_emb is not None:
                return fastembed_emb
            return compute_hash_fallback_embedding(text)

    async def match_resume_to_jd(
        self, 
        parsed_resume: Dict[str, Any], 
        parsed_jd: Dict[str, Any]
    ) -> MatchDetails:
        """
        Processes lists of resume skills against JD requirements to evaluate matching details,
        gaps, and recommended evaluation focus areas.
        """
        resume_skills: List[str] = parsed_resume.get("skills", [])
        jd_skills: List[str] = parsed_jd.get("tech_stack", [])
        
        if not jd_skills:
            jd_skills = parsed_jd.get("core_responsibilities", [])[:5]
        if not resume_skills:
            resume_skills = parsed_resume.get("past_roles", [])
            
        if not jd_skills:
            return MatchDetails(
                overall_percentage=50.0,
                matched_skills=[],
                gaps_identified=[],
                recommended_topics_to_probe=["General technical background check"]
            )

        matched_skills: List[str] = []
        gaps_identified: List[str] = []
        recommended_topics_to_probe: List[str] = []

        # Fast string and token set matching pass
        unmatched_jd_skills = []
        r_skills_lower = [s.lower() for s in resume_skills]

        for jd_skill in jd_skills:
            jd_clean = jd_skill.lower().strip()
            found_match = False
            best_r_skill = ""

            for idx, r_skill_clean in enumerate(r_skills_lower):
                if jd_clean == r_skill_clean or jd_clean in r_skill_clean or r_skill_clean in jd_clean:
                    found_match = True
                    best_r_skill = resume_skills[idx]
                    break

            if found_match:
                matched_skills.append(f"{jd_skill} (matched with {best_r_skill})")
            else:
                unmatched_jd_skills.append(jd_skill)

        # Fallback to embedding comparison for any remaining unmatched skills
        if unmatched_jd_skills and resume_skills:
            resume_embeddings: List[Tuple[str, List[float]]] = []
            for r_skill in resume_skills[:10]: # Cap embedding generation for speed
                emb = await self.get_embedding(r_skill)
                resume_embeddings.append((r_skill, emb))

            for jd_skill in unmatched_jd_skills:
                jd_emb = await self.get_embedding(jd_skill)
                best_similarity = 0.0
                best_match = ""

                for r_skill, r_emb in resume_embeddings:
                    similarity = calculate_cosine_similarity(jd_emb, r_emb)
                    if similarity > best_similarity:
                        best_similarity = similarity
                        best_match = r_skill

                if best_similarity >= self.similarity_threshold:
                    matched_skills.append(f"{jd_skill} (matched with {best_match})")
                else:
                    gaps_identified.append(jd_skill)
                    recommended_topics_to_probe.append(
                        f"Probe candidate capability and experience in: {jd_skill}"
                    )
        else:
            for jd_skill in unmatched_jd_skills:
                gaps_identified.append(jd_skill)
                recommended_topics_to_probe.append(
                    f"Probe candidate capability and experience in: {jd_skill}"
                )

        total_jd = len(jd_skills)
        matched_count = len(matched_skills)
        overall_percentage = round((matched_count / total_jd) * 100.0, 2) if total_jd > 0 else 100.0

        if not recommended_topics_to_probe:
            recommended_topics_to_probe = ["Verify deep technical execution limits under previous roles."]

        return MatchDetails(
            overall_percentage=overall_percentage,
            matched_skills=matched_skills,
            gaps_identified=gaps_identified,
            recommended_topics_to_probe=recommended_topics_to_probe
        )
