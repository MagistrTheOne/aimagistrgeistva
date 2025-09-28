"""Application error handling."""

from typing import Any, Dict, Optional


class AIError(Exception):
    """Base exception for AI Мага."""

    def __init__(
        self,
        message: str,
        code: str = "INTERNAL_ERROR",
        status_code: int = 500,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or {}


class ConfigurationError(AIError):
    """Configuration related errors."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, "CONFIG_ERROR", 500, details)


class ValidationError(AIError):
    """Input validation errors."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, "VALIDATION_ERROR", 400, details)


class AuthenticationError(AIError):
    """Authentication related errors."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, "AUTH_ERROR", 401, details)


class AuthorizationError(AIError):
    """Authorization related errors."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, "AUTHZ_ERROR", 403, details)


class NotFoundError(AIError):
    """Resource not found errors."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, "NOT_FOUND", 404, details)


class RateLimitError(AIError):
    """Rate limiting errors."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, "RATE_LIMIT", 429, details)


class ExternalServiceError(AIError):
    """External service errors."""

    def __init__(
        self,
        message: str,
        service: str,
        status_code: int = 502,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message, "EXTERNAL_SERVICE_ERROR", status_code, details)
        self.service = service


class VoiceProcessingError(AIError):
    """Voice processing related errors."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, "VOICE_PROCESSING_ERROR", 500, details)


class LLMError(AIError):
    """LLM related errors."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, "LLM_ERROR", 500, details)


class DatabaseError(AIError):
    """Database related errors."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, "DATABASE_ERROR", 500, details)


class RedisError(AIError):
    """Redis related errors."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, "REDIS_ERROR", 500, details)


def error_to_dict(error: AIError) -> Dict[str, Any]:
    """Convert an AIError to a dictionary for API responses."""
    return {
        "error": {
            "code": error.code,
            "message": error.message,
            "details": error.details,
        }
    }


def handle_error(error: Exception) -> Dict[str, Any]:
    """Handle and format any exception."""
    if isinstance(error, AIError):
        return error_to_dict(error)

    # Handle unexpected errors
    return {
        "error": {
            "code": "INTERNAL_ERROR",
            "message": "An unexpected error occurred",
            "details": {"original_error": str(error)} if not isinstance(error, AIError) else {},
        }
    }
