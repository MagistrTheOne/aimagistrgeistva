"""Domain policies and business rules."""

from typing import Dict, List, Optional
from uuid import UUID

from app.core.config import settings
from app.domain.models import CommandType, UserProfile


class AuthorizationPolicy:
    """Authorization policies for commands and actions."""

    @staticmethod
    def can_execute_command(user_id: UUID, command_type: CommandType) -> bool:
        """Check if user can execute a command."""
        # For now, allow all commands for authenticated users
        # In production, implement proper authorization logic
        return True

    @staticmethod
    def can_access_telegram(user_id: Optional[int]) -> bool:
        """Check if Telegram user is allowed."""
        if not user_id:
            return False

        if not settings.tg_allowed_user_ids:
            return False

        return user_id in settings.tg_allowed_user_ids

    @staticmethod
    def can_use_voice_features(user_profile: UserProfile) -> bool:
        """Check if user can use voice features."""
        # Check user preferences or subscription status
        return user_profile.preferences.get("voice_enabled", True)


class RateLimitPolicy:
    """Rate limiting policies."""

    # Rate limits per user per time window
    VOICE_COMMANDS_PER_MINUTE = 30
    CHAT_MESSAGES_PER_MINUTE = 60
    JOB_SEARCHES_PER_HOUR = 20
    TRANSLATIONS_PER_MINUTE = 10

    @staticmethod
    def get_limit_for_command(command_type: CommandType) -> Dict[str, int]:
        """Get rate limit for command type."""
        limits = {
            CommandType.VOICE_ACTIVATE: {"requests": 10, "window_seconds": 60},
            CommandType.VOICE_DEACTIVATE: {"requests": 10, "window_seconds": 60},
            CommandType.CHAT_MESSAGE: {"requests": 60, "window_seconds": 60},
            CommandType.SEARCH_JOBS: {"requests": 20, "window_seconds": 3600},
            CommandType.CREATE_REMINDER: {"requests": 10, "window_seconds": 3600},
            CommandType.TRANSLATE_TEXT: {"requests": 10, "window_seconds": 60},
            CommandType.READ_TEXT: {"requests": 30, "window_seconds": 60},
            CommandType.GENERATE_RESPONSE: {"requests": 30, "window_seconds": 60},
        }
        return limits.get(command_type, {"requests": 10, "window_seconds": 60})


class ContentPolicy:
    """Content filtering and safety policies."""

    # Blocked keywords (simplified example)
    BLOCKED_KEYWORDS = [
        "hack", "exploit", "password", "secret",
        # Add more as needed
    ]

    @staticmethod
    def is_content_safe(text: str) -> bool:
        """Check if content is safe to process."""
        text_lower = text.lower()
        return not any(keyword in text_lower for keyword in ContentPolicy.BLOCKED_KEYWORDS)

    @staticmethod
    def filter_pii(text: str) -> str:
        """Filter personally identifiable information from logs."""
        # Simple PII filtering - in production use more sophisticated methods
        import re

        # Remove email addresses
        text = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[EMAIL]', text)
        # Remove phone numbers (simple pattern)
        text = re.sub(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b', '[PHONE]', text)
        # Remove potential credit card numbers
        text = re.sub(r'\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b', '[CARD]', text)

        return text


class PrivacyPolicy:
    """Privacy and data retention policies."""

    # Data retention periods (in days)
    VOICE_SESSIONS_RETENTION = 7
    CONVERSATIONS_RETENTION = 30
    COMMANDS_RETENTION = 90
    METRICS_RETENTION = 365

    @staticmethod
    def should_retain_voice_data(user_profile: UserProfile) -> bool:
        """Check if voice data should be retained for user."""
        return user_profile.preferences.get("voice_data_retention", False)

    @staticmethod
    def should_log_interactions(user_profile: UserProfile) -> bool:
        """Check if interactions should be logged."""
        return user_profile.preferences.get("interaction_logging", True)


class NotificationPolicy:
    """Notification and alerting policies."""

    @staticmethod
    def should_notify_on_error(error_type: str, severity: str) -> bool:
        """Check if error should trigger notification."""
        critical_errors = ["database_connection", "external_service_down"]
        return error_type in critical_errors or severity == "critical"

    @staticmethod
    def get_notification_channels(user_profile: UserProfile) -> List[str]:
        """Get notification channels for user."""
        channels = []
        if user_profile.telegram_id:
            channels.append("telegram")
        # Add email, push notifications, etc.
        return channels
