from typing import Any, Dict, Optional
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.base import BaseHTTPMiddleware
import logging

logger = logging.getLogger(__name__)


class BaseAppException(Exception):
    """
    Base exception class for all custom application errors.
    Allows passing error messages and context dictionary logs.
    """
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class DatabaseException(BaseAppException):
    """
    Raised when operations on the database fail, such as session errors,
    integrity constraints, or connection losses.
    """
    pass


class SpeechServiceException(BaseAppException):
    """
    Raised when the speech pipeline (Whisper STT or Piper TTS) fails
    due to missing files, model timeouts, or processing errors.
    """
    pass


class LLMServiceException(BaseAppException):
    """
    Raised when interactions with the local LLM (Ollama) fail,
    such as connection timeouts or unparseable JSON schemas.
    """
    pass


class AuthException(BaseAppException):
    """
    Raised when JWT authentication, validation, or password hashing fails.
    """
    pass


class NotFoundException(BaseAppException):
    """
    Raised when a requested DB resource (e.g. User, Resume, Interview) is missing.
    """
    pass


class ValidationException(BaseAppException):
    """
    Raised when business rules or parameters are violated during processing.
    """
    pass


def create_cors_json_response(status_code: int, content: dict) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content=content,
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "*",
            "Access-Control-Allow-Headers": "*",
        }
    )


async def global_app_exception_handler(request: Request, exc: BaseAppException) -> JSONResponse:
    """
    Catches custom application errors and maps them to corresponding HTTP status codes,
    maintaining structured API error formats.
    """
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR

    if isinstance(exc, NotFoundException):
        status_code = status.HTTP_404_NOT_FOUND
    elif isinstance(exc, AuthException):
        status_code = status.HTTP_401_UNAUTHORIZED
    elif isinstance(exc, ValidationException):
        status_code = status.HTTP_400_BAD_REQUEST
    elif isinstance(exc, SpeechServiceException):
        status_code = status.HTTP_502_BAD_GATEWAY
    elif isinstance(exc, LLMServiceException):
        status_code = status.HTTP_502_BAD_GATEWAY
    elif isinstance(exc, DatabaseException):
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR

    logger.error(
        f"Application Error [{exc.__class__.__name__}]: {exc.message}",
        exc_info=True,
        extra={"extra": {"details": exc.details, "error_type": exc.__class__.__name__}}
    )

    return create_cors_json_response(
        status_code=status_code,
        content={
            "error": exc.__class__.__name__,
            "message": exc.message,
            "details": exc.details
        }
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """
    Catches FastAPI/Pydantic request validation errors and formats them into clean,
    human-readable messages and structured field details.
    """
    error_messages = []
    formatted_errors = []

    for err in exc.errors():
        loc = " -> ".join([str(x) for x in err.get("loc", []) if str(x) != "body"])
        msg = err.get("msg", "Invalid value")
        if loc:
            error_messages.append(f"{loc}: {msg}")
        else:
            error_messages.append(msg)
        formatted_errors.append({
            "field": loc or "request",
            "message": msg,
            "type": err.get("type", "validation_error")
        })

    summary_message = f"Validation Error: {'; '.join(error_messages)}" if error_messages else "Invalid request data"

    logger.warning(
        f"Request Validation Failed on {request.method} {request.url.path}: {summary_message}",
        extra={"extra": {"errors": formatted_errors}}
    )

    return create_cors_json_response(
        status_code=422,
        content={
            "error": "ValidationError",
            "message": summary_message,
            "details": {"errors": formatted_errors}
        }
    )


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """
    Catches standard HTTP exceptions (e.g. 404 Not Found, 405 Method Not Allowed)
    and returns uniform JSON response schema.
    """
    message = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
    logger.warning(f"HTTP Exception [{exc.status_code}] on {request.method} {request.url.path}: {message}")

    return create_cors_json_response(
        status_code=exc.status_code,
        content={
            "error": "HTTPException",
            "message": message,
            "details": {}
        }
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Global catch-all exception handler for any unexpected Python runtime exceptions.
    Prevents 500 HTML or unformatted responses and logs full tracebacks.
    """
    logger.error(
        f"Unhandled Exception on {request.method} {request.url.path}: {str(exc)}",
        exc_info=True
    )

    return create_cors_json_response(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "InternalServerError",
            "message": f"An unexpected server error occurred: {str(exc)}",
            "details": {"type": exc.__class__.__name__}
        }
    )


def register_exception_handlers(app: FastAPI) -> None:
    """
    Binds the global application exception handlers to a FastAPI app instance.
    Handles all custom, validation, HTTP, and unhandled runtime exceptions.
    """
    app.add_exception_handler(BaseAppException, global_app_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)
