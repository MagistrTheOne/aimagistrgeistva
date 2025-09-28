"""Domain models for AI Мага."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class CommandType(str, Enum):
    """Types of commands that AI Мага can handle."""

    VOICE_ACTIVATE = "voice_activate"
    VOICE_DEACTIVATE = "voice_deactivate"
    CHAT_MESSAGE = "chat_message"
    SEARCH_JOBS = "search_jobs"
    CREATE_REMINDER = "create_reminder"
    TRANSLATE_TEXT = "translate_text"
    READ_TEXT = "read_text"
    GENERATE_RESPONSE = "generate_response"


class CommandStatus(str, Enum):
    """Status of command execution."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class User(BaseModel):
    """User model for authentication and preferences."""

    id: UUID = Field(default_factory=uuid4)
    telegram_id: Optional[int] = None
    name: Optional[str] = None
    language: str = Field(default="ru")
    timezone: str = Field(default="Europe/Moscow")
    preferences: Dict[str, Any] = Field(default_factory=dict)
    roles: List[str] = Field(default_factory=lambda: ["user"])
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    last_seen: Optional[datetime] = None

    class Config:
        from_attributes = True


# Backward compatibility
UserProfile = User


class Message(BaseModel):
    """Message model for storing user communications."""

    id: UUID = Field(default_factory=uuid4)
    user_id: UUID
    session_id: Optional[UUID] = None
    source: str  # "voice", "telegram", "http", "api"
    channel: Optional[str] = None  # "telegram", "voice", etc.
    content_type: str = Field(default="text")  # "text", "audio", "image", "file"
    content: str  # Text content or path to file
    metadata: Dict[str, Any] = Field(default_factory=dict)  # Audio duration, file size, etc.
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    processed: bool = Field(default=False)
    intent_id: Optional[UUID] = None  # Link to detected intent

    class Config:
        from_attributes = True


class ConversationContext(BaseModel):
    """Conversation context for maintaining state."""

    session_id: UUID = Field(default_factory=uuid4)
    user_id: UUID
    messages: List[Dict[str, Any]] = Field(default_factory=list)
    context_data: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        from_attributes = True


class Intent(BaseModel):
    """Intent detection result model."""

    id: UUID = Field(default_factory=uuid4)
    user_id: UUID
    session_id: Optional[UUID] = None
    message_id: Optional[UUID] = None  # Link to source message
    intent_type: str  # IntentType enum value
    confidence: float = Field(ge=0.0, le=1.0)
    slots: Dict[str, Any] = Field(default_factory=dict)  # Extracted slots
    raw_text: str
    source: str  # "voice", "telegram", "http"
    language: Optional[str] = None
    explanation: Optional[str] = None
    processed: bool = Field(default=False)
    plan_id: Optional[str] = None  # Link to orchestration plan
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        from_attributes = True


class Task(BaseModel):
    """Task/scheduled job model."""

    id: UUID = Field(default_factory=uuid4)
    user_id: UUID
    type: str  # "reminder", "digest", "followup", etc.
    title: str
    description: Optional[str] = None
    payload: Dict[str, Any] = Field(default_factory=dict)
    status: str = Field(default="pending")  # "pending", "running", "completed", "failed", "cancelled"
    priority: int = Field(default=1, ge=1, le=5)
    cron_spec: Optional[str] = None  # Cron expression for recurring tasks
    next_run: Optional[datetime] = None
    last_run: Optional[datetime] = None
    retry_count: int = Field(default=0)
    max_retries: int = Field(default=3)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        from_attributes = True


class Command(BaseModel):
    """Domain command model."""

    id: UUID = Field(default_factory=uuid4)
    type: CommandType
    user_id: UUID
    session_id: Optional[UUID] = None
    payload: Dict[str, Any] = Field(default_factory=dict)
    status: CommandStatus = CommandStatus.PENDING
    result: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class VoiceSession(BaseModel):
    """Voice processing session."""

    id: UUID = Field(default_factory=uuid4)
    user_id: UUID
    device_id: str
    is_active: bool = False
    last_activity: datetime = Field(default_factory=datetime.utcnow)
    audio_buffer: bytes = b""
    transcription: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        from_attributes = True


class JobSearchResult(BaseModel):
    """Job search result from HH.ru."""

    id: str
    title: str
    company: str
    location: str
    salary: Optional[str] = None
    description: str
    url: str
    published_at: datetime
    tags: List[str] = Field(default_factory=list)

    class Config:
        from_attributes = True


class Reminder(BaseModel):
    """Reminder/task model."""

    id: UUID = Field(default_factory=uuid4)
    user_id: UUID
    title: str
    description: Optional[str] = None
    due_date: datetime
    is_completed: bool = False
    priority: int = 1  # 1-5 scale
    created_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class DomainEvent(BaseModel):
    """Base domain event."""

    event_id: UUID = Field(default_factory=uuid4)
    event_type: str
    aggregate_id: UUID
    event_data: Dict[str, Any]
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    version: int = 1

    class Config:
        from_attributes = True


class VoiceHotwordDetected(DomainEvent):
    """Event when hotword is detected."""

    event_type: str = "voice.hotword.detected"
    device_id: str
    confidence: float


class TranscriptionReady(DomainEvent):
    """Event when speech is transcribed."""

    event_type: str = "voice.transcription.ready"
    text: str
    language: str
    confidence: float


class IntentDetected(DomainEvent):
    """Event when intent is detected."""

    event_type: str = "nlp.intent.detected"
    intent: str
    slots: Dict[str, Any]
    confidence: float


class ActionCompleted(DomainEvent):
    """Event when action is completed."""

    event_type: str = "action.completed"
    action_id: UUID
    status: str
    result: Optional[Dict[str, Any]] = None


class MessageSent(DomainEvent):
    """Event when message is sent."""

    event_type: str = "message.sent"
    channel: str
    message_id: str
    recipient: str
