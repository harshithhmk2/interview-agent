import pytest
from io import BytesIO
from unittest.mock import MagicMock, patch, AsyncMock
from src.services.parser import (
    DocumentParser,
    ResumeParsedAttributes,
    JDParsedAttributes
)
from src.core.exceptions import ValidationException
from src.services.llm import ILLMClient


@pytest.fixture
def mock_llm_client():
    return MagicMock(spec=ILLMClient)


def test_extract_text_txt_success(mock_llm_client):
    parser = DocumentParser(llm_client=mock_llm_client)
    file_stream = BytesIO(b"Hello, this is a plain text resume content.")
    
    extracted = parser.extract_text(file_stream, "txt")
    
    assert extracted == "Hello, this is a plain text resume content."


def test_extract_text_pdf_success(mock_llm_client):
    parser = DocumentParser(llm_client=mock_llm_client)
    file_stream = BytesIO(b"dummy pdf bytes")

    with patch("src.services.parser.pypdf.PdfReader") as mock_pdf_reader_cls:
        mock_reader = MagicMock()
        mock_page_1 = MagicMock()
        mock_page_1.extract_text.return_value = "John Doe Resume"
        mock_page_2 = MagicMock()
        mock_page_2.extract_text.return_value = "Experience: 5 years"
        
        mock_reader.pages = [mock_page_1, mock_page_2]
        mock_pdf_reader_cls.return_value = mock_reader

        extracted = parser.extract_text(file_stream, ".pdf")
        
        assert "John Doe Resume" in extracted
        assert "Experience: 5 years" in extracted
        mock_pdf_reader_cls.assert_called_once_with(file_stream)


def test_extract_text_docx_success(mock_llm_client):
    parser = DocumentParser(llm_client=mock_llm_client)
    file_stream = BytesIO(b"dummy docx bytes")

    with patch("src.services.parser.Document") as mock_docx_cls:
        mock_doc = MagicMock()
        mock_para_1 = MagicMock()
        mock_para_1.text = "Jane Doe Job Description"
        mock_para_2 = MagicMock()
        mock_para_2.text = "Requirements: Python and SQL"
        
        mock_doc.paragraphs = [mock_para_1, mock_para_2]
        mock_docx_cls.return_value = mock_doc

        extracted = parser.extract_text(file_stream, "docx")
        
        assert extracted == "Jane Doe Job Description\nRequirements: Python and SQL"
        mock_docx_cls.assert_called_once_with(file_stream)


def test_extract_text_unsupported_format(mock_llm_client):
    parser = DocumentParser(llm_client=mock_llm_client)
    file_stream = BytesIO(b"some content")

    with pytest.raises(ValidationException) as exc_info:
        parser.extract_text(file_stream, "png")
        
    assert "Unsupported file format" in exc_info.value.message


def test_extract_text_empty_content(mock_llm_client):
    parser = DocumentParser(llm_client=mock_llm_client)
    file_stream = BytesIO(b"   ")

    with pytest.raises(ValidationException) as exc_info:
        parser.extract_text(file_stream, "txt")
        
    assert "Extracted document text is empty" in exc_info.value.message


def test_extract_text_extraction_failure_wraps_exception(mock_llm_client):
    parser = DocumentParser(llm_client=mock_llm_client)
    file_stream = BytesIO(b"some bad bytes")
    
    with patch("src.services.parser.Document", side_effect=Exception("Read error")):
        with pytest.raises(ValidationException) as exc_info:
            parser.extract_text(file_stream, "docx")
            
        assert "Failed to read file contents for format .docx" in exc_info.value.message
        assert "Read error" in exc_info.value.details["original_error"]


@pytest.mark.asyncio
async def test_parse_entities_resume_success(mock_llm_client):
    parser = DocumentParser(llm_client=mock_llm_client)
    
    # Mock LLM response
    expected_resume_attributes = ResumeParsedAttributes(
        candidate_name="John Doe",
        candidate_email="john.doe@example.com",
        skills=["Python", "FastAPI", "PostgreSQL"],
        experience_years=4.5,
        education=["B.S. Computer Science"],
        past_roles=["Software Engineer", "Junior Backend Dev"]
    )
    
    mock_llm_client.generate_structured_json = AsyncMock(return_value=expected_resume_attributes)

    result = await parser.parse_entities("John Doe Resume text here...", doc_type="resume")

    assert result == expected_resume_attributes.model_dump()
    mock_llm_client.generate_structured_json.assert_called_once()
    called_kwargs = mock_llm_client.generate_structured_json.call_args[1]
    assert called_kwargs["response_schema"] == ResumeParsedAttributes
    assert "Resume Content" in called_kwargs["prompt"]
    assert "resume parsing assistant" in called_kwargs["system_instruction"]


@pytest.mark.asyncio
async def test_parse_entities_jd_success(mock_llm_client):
    parser = DocumentParser(llm_client=mock_llm_client)
    
    # Mock LLM response
    expected_jd_attributes = JDParsedAttributes(
        role_title="Senior Developer",
        tech_stack=["React", "Node.js", "Docker"],
        minimum_experience_years=5.0,
        core_responsibilities=["Maintain core web application", "Mentor juniors"],
        preferred_skills=["Kubernetes", "AWS"]
    )
    
    mock_llm_client.generate_structured_json = AsyncMock(return_value=expected_jd_attributes)

    # Use 'jd' and 'job_description' to verify both match blocks
    result_jd = await parser.parse_entities("Role details...", doc_type="jd")
    result_job_description = await parser.parse_entities("Role details...", doc_type="job_description")

    assert result_jd == expected_jd_attributes.model_dump()
    assert result_job_description == expected_jd_attributes.model_dump()
    
    assert mock_llm_client.generate_structured_json.call_count == 2
    called_kwargs = mock_llm_client.generate_structured_json.call_args[1]
    assert called_kwargs["response_schema"] == JDParsedAttributes
    assert "Job Description Content" in called_kwargs["prompt"]
    assert "recruitment assistant" in called_kwargs["system_instruction"]


@pytest.mark.asyncio
async def test_parse_entities_invalid_doc_type(mock_llm_client):
    parser = DocumentParser(llm_client=mock_llm_client)
    
    with pytest.raises(ValidationException) as exc_info:
        await parser.parse_entities("Some text", doc_type="invoice")
        
    assert "Invalid document type specified for entity parsing" in exc_info.value.message
