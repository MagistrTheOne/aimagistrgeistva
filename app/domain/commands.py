"""Domain commands for AI Мага."""

from typing import Any, Dict, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from app.domain.models import CommandType


class BaseCommand(BaseModel):
    """Base command class."""

    user_id: UUID
    session_id: Optional[UUID] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class VoiceActivateCommand(BaseCommand):
    """Command to activate voice listening."""

    device_id: str


class VoiceDeactivateCommand(BaseCommand):
    """Command to deactivate voice listening."""

    device_id: str


class ChatMessageCommand(BaseCommand):
    """Command for chat message processing."""

    text: str
    context: Optional[Dict[str, Any]] = None


class SearchJobsCommand(BaseCommand):
    """Command to search for jobs."""

    query: str
    location: Optional[str] = None
    experience: Optional[str] = None
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None


class CreateReminderCommand(BaseCommand):
    """Command to create a reminder."""

    title: str
    description: Optional[str] = None
    due_date: str  # ISO format
    priority: int = Field(default=1, ge=1, le=5)


class TranslateTextCommand(BaseCommand):
    """Command to translate text."""

    text: str
    target_language: str = "en"
    source_language: Optional[str] = None


class ReadTextCommand(BaseCommand):
    """Command to read text aloud."""

    text: str
    language: str = "ru"


class GenerateResponseCommand(BaseCommand):
    """Command to generate a response."""

    prompt: str
    context: Optional[Dict[str, Any]] = None
    max_tokens: Optional[int] = None


# Command registry for mapping strings to command classes
COMMAND_REGISTRY = {
    CommandType.VOICE_ACTIVATE: VoiceActivateCommand,
    CommandType.VOICE_DEACTIVATE: VoiceDeactivateCommand,
    CommandType.CHAT_MESSAGE: ChatMessageCommand,
    CommandType.SEARCH_JOBS: SearchJobsCommand,
    CommandType.CREATE_REMINDER: CreateReminderCommand,
    CommandType.TRANSLATE_TEXT: TranslateTextCommand,
    CommandType.READ_TEXT: ReadTextCommand,
    CommandType.GENERATE_RESPONSE: GenerateResponseCommand,
}


def create_command(command_type: CommandType, **kwargs) -> BaseCommand:
    """Create a command instance from type and parameters."""
    command_class = COMMAND_REGISTRY.get(command_type)
    if not command_class:
        raise ValueError(f"Unknown command type: {command_type}")
    return command_class(**kwargs)
