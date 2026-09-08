import httpx
import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from pydantic import BaseModel, Field
from typing import List

from src.services.llm import OllamaLLMClient
from src.core.exceptions import LLMServiceException


class DummySchema(BaseModel):
    name: str = Field(..., description="The name")
    age: int = Field(..., description="The age")
    tags: List[str] = Field(default_factory=list, description="Tags list")


@pytest.fixture
def client_post_mock():
    """
    Fixture to mock httpx.AsyncClient.post and return the post mock and the client mock.
    """
    from src.config import settings
    with patch.object(settings, "MOCK_LLM", False):
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client_instance = MagicMock()
            mock_post = MagicMock()
            mock_client_instance.post = mock_post
            
            # Mock async context manager
            mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
            mock_client_instance.__aexit__ = AsyncMock(return_value=None)
            
            mock_client_class.return_value = mock_client_instance
            yield mock_post


@pytest.mark.asyncio
async def test_generate_completion_success(client_post_mock):
    # Setup mock response
    mock_response = httpx.Response(
        status_code=200,
        json={"response": " Hello World! "},
        request=httpx.Request("POST", "http://localhost")
    )
    # Since it's inside an async client method, we await post.
    # MagicMock's return value for post can be an awaitable (AsyncMock).
    # We patch it so that the awaited post call returns mock_response.
    async def mock_post_call(*args, **kwargs):
        return mock_response
    client_post_mock.side_effect = mock_post_call

    client = OllamaLLMClient(base_url="http://localhost:11434", model="llama3")
    result = await client.generate_completion(
        prompt="Test Prompt",
        system_instruction="Test System",
        temperature=0.5
    )

    assert result == "Hello World!"
    # Verify the post parameters
    client_post_mock.assert_called_once()
    called_args, called_kwargs = client_post_mock.call_args
    assert called_args[0] == "http://localhost:11434/api/generate"
    
    payload = called_kwargs["json"]
    assert payload["model"] == "llama3"
    assert payload["prompt"] == "Test Prompt"
    assert payload["system"] == "Test System"
    assert payload["options"]["temperature"] == 0.5
    assert payload["stream"] is False


@pytest.mark.asyncio
async def test_generate_completion_http_error(client_post_mock):
    # Setup mock response indicating error
    mock_response = httpx.Response(
        status_code=500,
        content="Internal Server Error",
        request=httpx.Request("POST", "http://localhost")
    )
    async def mock_post_call(*args, **kwargs):
        return mock_response
    client_post_mock.side_effect = mock_post_call

    client = OllamaLLMClient(base_url="http://localhost:11434", model="llama3")
    
    with pytest.raises(LLMServiceException) as exc_info:
        await client.generate_completion(prompt="Test Prompt")
    
    assert "Ollama client connection error" in exc_info.value.message


@pytest.mark.asyncio
async def test_generate_completion_connection_error(client_post_mock):
    # Setup mock to raise connection error
    async def mock_post_call(*args, **kwargs):
        raise httpx.ConnectError("Connection refused")
    client_post_mock.side_effect = mock_post_call

    client = OllamaLLMClient(base_url="http://localhost:11434", model="llama3")
    
    with pytest.raises(LLMServiceException) as exc_info:
        await client.generate_completion(prompt="Test Prompt")
        
    assert "Ollama client connection error" in exc_info.value.message


@pytest.mark.asyncio
async def test_generate_structured_json_success(client_post_mock):
    # Setup mock response returning correct JSON matching DummySchema
    raw_json = '{"name": "Jane Doe", "age": 28, "tags": ["python", "pytest"]}'
    mock_response = httpx.Response(
        status_code=200,
        json={"response": raw_json},
        request=httpx.Request("POST", "http://localhost")
    )
    async def mock_post_call(*args, **kwargs):
        return mock_response
    client_post_mock.side_effect = mock_post_call

    client = OllamaLLMClient(base_url="http://localhost:11434", model="llama3")
    result = await client.generate_structured_json(
        prompt="Give me dummy data",
        response_schema=DummySchema,
        system_instruction="Strict JSON"
    )

    assert isinstance(result, DummySchema)
    assert result.name == "Jane Doe"
    assert result.age == 28
    assert result.tags == ["python", "pytest"]

    # Verify structured prompt generation includes schema instructions
    called_args, called_kwargs = client_post_mock.call_args
    payload = called_kwargs["json"]
    assert "DummySchema" in payload["prompt"]
    assert payload["format"] == "json"


@pytest.mark.asyncio
async def test_generate_structured_json_with_markdown_wrappers(client_post_mock):
    # Test cleanup of accidental markdown wrappers (```json ... ```)
    wrapped_json = "```json\n" '{"name": "Markdown", "age": 10, "tags": []}\n' "```"
    mock_response = httpx.Response(
        status_code=200,
        json={"response": wrapped_json},
        request=httpx.Request("POST", "http://localhost")
    )
    async def mock_post_call(*args, **kwargs):
        return mock_response
    client_post_mock.side_effect = mock_post_call

    client = OllamaLLMClient(base_url="http://localhost:11434", model="llama3")
    result = await client.generate_structured_json(
        prompt="Give me wrapped data",
        response_schema=DummySchema
    )

    assert result.name == "Markdown"
    assert result.age == 10
    assert result.tags == []


@pytest.mark.asyncio
async def test_generate_structured_json_validation_error(client_post_mock):
    # Response has invalid fields (age is a string that cannot be cast to int)
    invalid_json = '{"name": "Jane", "age": "not-an-int", "tags": []}'
    mock_response = httpx.Response(
        status_code=200,
        json={"response": invalid_json},
        request=httpx.Request("POST", "http://localhost")
    )
    async def mock_post_call(*args, **kwargs):
        return mock_response
    client_post_mock.side_effect = mock_post_call

    client = OllamaLLMClient(base_url="http://localhost:11434", model="llama3")
    
    with pytest.raises(LLMServiceException) as exc_info:
        await client.generate_structured_json(
            prompt="Give me invalid data",
            response_schema=DummySchema
        )

    assert "Failed to validate LLM response against Pydantic schema" in exc_info.value.message
    assert "raw_text" in exc_info.value.details


@pytest.mark.asyncio
async def test_generate_embeddings_success(client_post_mock):
    # Setup mock response
    mock_response = httpx.Response(
        status_code=200,
        json={"embedding": [0.25, -0.5, 0.75, 1.0]},
        request=httpx.Request("POST", "http://localhost")
    )
    async def mock_post_call(*args, **kwargs):
        return mock_response
    client_post_mock.side_effect = mock_post_call

    client = OllamaLLMClient(base_url="http://localhost:11434", model="llama3")
    result = await client.generate_embeddings(text="Embed text")

    assert result == [0.25, -0.5, 0.75, 1.0]
    
    called_args, called_kwargs = client_post_mock.call_args
    assert called_args[0] == "http://localhost:11434/api/embeddings"
    payload = called_kwargs["json"]
    assert payload["model"] == "llama3"
    assert payload["prompt"] == "Embed text"


@pytest.mark.asyncio
async def test_generate_embeddings_invalid_response(client_post_mock):
    # Setup mock response with missing embedding
    mock_response = httpx.Response(
        status_code=200,
        json={"error": "Model not loaded"},
        request=httpx.Request("POST", "http://localhost")
    )
    async def mock_post_call(*args, **kwargs):
        return mock_response
    client_post_mock.side_effect = mock_post_call

    client = OllamaLLMClient(base_url="http://localhost:11434", model="llama3")
    
    with pytest.raises(LLMServiceException) as exc_info:
        await client.generate_embeddings(text="Embed text")

    assert "Ollama embedding response format invalid" in exc_info.value.message
