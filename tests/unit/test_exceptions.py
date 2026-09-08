import pytest
from src.core.exceptions import (
    AuthException,
    NotFoundException,
    ValidationException,
    LLMServiceException,
    SpeechServiceException,
    DatabaseException,
)


@pytest.mark.asyncio
async def test_validation_error_formatting(client):
    """
    Test that invalid request payloads (e.g. invalid email / missing fields)
    return a 422 ValidationError with clean formatted message string and details list.
    """
    invalid_payload = {
        "email": "not-an-email",
        "password": "short",
        "full_name": "Test User"
    }
    res = await client.post("/api/v1/auth/signup", json=invalid_payload)
    assert res.status_code == 422
    data = res.json()
    assert data["error"] == "ValidationError"
    assert "Validation Error:" in data["message"]
    assert "details" in data
    assert "errors" in data["details"]
    assert len(data["details"]["errors"]) > 0


@pytest.mark.asyncio
async def test_auth_exception_formatting(client):
    """
    Test that custom application exceptions return clean JSON with error, message, and details.
    """
    invalid_login = {
        "username": "nonexistent@example.com",
        "password": "WrongPassword123!"
    }
    res = await client.post("/api/v1/auth/token", data=invalid_login)
    assert res.status_code == 401
    data = res.json()
    assert data["error"] == "AuthException"
    assert data["message"] == "Incorrect email or password"
    assert "details" in data


@pytest.mark.asyncio
async def test_not_found_exception_formatting(client):
    """
    Test 404 NotFoundException response schema.
    """
    signup_data = {
        "email": "exception_test@example.com",
        "password": "SecurePassword123!",
        "full_name": "Exception Tester",
        "role": "interviewer"
    }
    await client.post("/api/v1/auth/signup", json=signup_data)
    
    login_res = await client.post("/api/v1/auth/token", data={
        "username": "exception_test@example.com",
        "password": "SecurePassword123!"
    })
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    fake_uuid = "00000000-0000-0000-0000-000000000000"
    res = await client.get(f"/api/v1/reports/{fake_uuid}", headers=headers)
    assert res.status_code == 404
    data = res.json()
    assert data["error"] == "NotFoundException"
    assert "details" in data
