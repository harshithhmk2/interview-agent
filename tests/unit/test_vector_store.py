import pytest
from unittest.mock import MagicMock, patch
from src.services.vector_store import (
    compute_hash_fallback_embedding,
    calculate_cosine_similarity,
    compute_fastembed_embedding,
    SemanticMatcher,
)


def test_compute_hash_fallback_embedding():
    emb1 = compute_hash_fallback_embedding("Python")
    emb2 = compute_hash_fallback_embedding("Python")
    emb3 = compute_hash_fallback_embedding("FastAPI")

    assert len(emb1) == 128
    assert emb1 == emb2  # Deterministic
    assert emb1 != emb3  # Different text gives different hash


def test_calculate_cosine_similarity():
    v1 = [1.0, 0.0, 0.0]
    v2 = [1.0, 0.0, 0.0]
    v3 = [0.0, 1.0, 0.0]

    assert pytest.approx(calculate_cosine_similarity(v1, v2), 0.001) == 1.0
    assert pytest.approx(calculate_cosine_similarity(v1, v3), 0.001) == 0.0


def test_calculate_cosine_similarity_mismatched_dimensions():
    v1 = [1.0, 0.0, 0.0, 1.0]
    v2 = [1.0, 0.0, 0.0]

    # Should truncate/pad and calculate without throwing
    sim = calculate_cosine_similarity(v1, v2)
    assert isinstance(sim, float)


@pytest.mark.asyncio
async def test_semantic_matcher_with_fastembed():
    matcher = SemanticMatcher()
    emb = await matcher.get_embedding("Docker containerization")

    assert isinstance(emb, list)
    assert len(emb) > 0


@pytest.mark.asyncio
async def test_semantic_matcher_match_resume_to_jd():
    matcher = SemanticMatcher(similarity_threshold=0.6)
    parsed_resume = {
        "skills": ["Python", "Docker", "PostgreSQL", "FastAPI"],
        "past_roles": ["Backend Developer"]
    }
    parsed_jd = {
        "tech_stack": ["Python", "FastAPI", "Kubernetes"],
        "core_responsibilities": ["Build backend APIs"]
    }

    match_result = await matcher.match_resume_to_jd(parsed_resume, parsed_jd)

    assert match_result.overall_percentage > 0
    assert any("Python" in s for s in match_result.matched_skills)
    assert any("FastAPI" in s for s in match_result.matched_skills)
