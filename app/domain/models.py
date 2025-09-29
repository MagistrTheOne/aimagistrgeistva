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


# ===== AUTOMATION MODELS =====

class Document(BaseModel):
    """Document storage model for OCR and processing."""

    id: UUID = Field(default_factory=uuid4)
    user_id: UUID
    filename: str
    original_name: str
    content_type: str  # "image", "pdf", "text", etc.
    file_size: int
    extracted_text: Optional[str] = None
    summary: Optional[str] = None
    categories: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)
    ocr_confidence: Optional[float] = None
    processed: bool = Field(default=False)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    processed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class Expense(BaseModel):
    """Expense/financial record model."""

    id: UUID = Field(default_factory=uuid4)
    user_id: UUID
    amount: float
    currency: str = Field(default="RUB")
    category: str
    description: str
    merchant: Optional[str] = None
    date: datetime = Field(default_factory=datetime.utcnow)
    receipt_id: Optional[UUID] = None  # Link to Document if from receipt
    payment_method: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    is_recurring: bool = Field(default=False)
    recurring_pattern: Optional[str] = None  # "monthly", "weekly", etc.
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        from_attributes = True


class Budget(BaseModel):
    """Budget planning model."""

    id: UUID = Field(default_factory=uuid4)
    user_id: UUID
    name: str
    period: str = Field(default="monthly")  # "weekly", "monthly", "yearly"
    start_date: datetime = Field(default_factory=datetime.utcnow)
    end_date: Optional[datetime] = None
    categories: Dict[str, float] = Field(default_factory=dict)  # category -> limit
    total_limit: Optional[float] = None
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        from_attributes = True


class RSSFeed(BaseModel):
    """RSS feed configuration model."""

    id: UUID = Field(default_factory=uuid4)
    user_id: UUID
    url: str
    title: Optional[str] = None
    description: Optional[str] = None
    categories: List[str] = Field(default_factory=list)
    keywords: List[str] = Field(default_factory=list)
    last_checked: Optional[datetime] = None
    last_item_date: Optional[datetime] = None
    is_active: bool = Field(default=True)
    check_interval: int = Field(default=3600)  # seconds
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        from_attributes = True


class FeedItem(BaseModel):
    """RSS feed item model."""

    id: str  # Use feed item GUID as ID
    feed_id: UUID
    title: str
    description: Optional[str] = None
    content: Optional[str] = None
    url: str
    author: Optional[str] = None
    published_at: datetime
    tags: List[str] = Field(default_factory=list)
    read: bool = Field(default=False)
    bookmarked: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        from_attributes = True


class EmailAccount(BaseModel):
    """Email account configuration for monitoring."""

    id: UUID = Field(default_factory=uuid4)
    user_id: UUID
    email_address: str
    provider: str  # "gmail", "outlook", "imap", etc.
    imap_server: str
    imap_port: int = Field(default=993)
    use_ssl: bool = Field(default=True)
    username: str  # Usually same as email_address
    password: str  # Encrypted password
    last_checked: Optional[datetime] = None
    is_active: bool = Field(default=True)
    check_interval: int = Field(default=300)  # 5 minutes
    folders_to_monitor: List[str] = Field(default_factory=lambda: ["INBOX"])
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        from_attributes = True


class EmailMessage(BaseModel):
    """Email message model."""

    id: str  # Use email Message-ID header
    account_id: UUID
    subject: str
    sender: str
    recipients: List[str] = Field(default_factory=list)
    content: str
    html_content: Optional[str] = None
    received_at: datetime
    priority: str = Field(default="normal")  # "low", "normal", "high"
    has_attachments: bool = Field(default=False)
    attachments: List[Dict[str, Any]] = Field(default_factory=list)
    read: bool = Field(default=False)
    flagged: bool = Field(default=False)
    labels: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        from_attributes = True


class Notification(BaseModel):
    """Notification model for scheduling and delivery."""

    id: UUID = Field(default_factory=uuid4)
    user_id: UUID
    type: str  # "task_reminder", "feed_update", "email_alert", etc.
    title: str
    message: str
    channel: str = Field(default="telegram")  # "telegram", "email", "voice"
    priority: str = Field(default="normal")  # "low", "normal", "high", "urgent"
    scheduled_for: datetime
    delivered: bool = Field(default=False)
    delivered_at: Optional[datetime] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        from_attributes = True


class BackgroundJob(BaseModel):
    """Background job model for queuing tasks."""

    id: UUID = Field(default_factory=uuid4)
    job_type: str  # "feed_check", "email_sync", "task_reminder", etc.
    user_id: UUID
    payload: Dict[str, Any] = Field(default_factory=dict)
    status: str = Field(default="pending")  # "pending", "running", "completed", "failed"
    priority: int = Field(default=1, ge=1, le=10)
    scheduled_for: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    retry_count: int = Field(default=0)
    max_retries: int = Field(default=3)
    error_message: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        from_attributes = True


class UserPreference(BaseModel):
    """User preferences for automation settings."""

    id: UUID = Field(default_factory=uuid4)
    user_id: UUID
    category: str  # "notifications", "feeds", "tasks", "finance", etc.
    key: str
    value: Any  # Can be string, number, boolean, or complex object
    description: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        from_attributes = True


class LearningProgress(BaseModel):
    """Learning progress tracking for educational assistant."""

    id: UUID = Field(default_factory=uuid4)
    user_id: UUID
    topic: str
    subtopic: Optional[str] = None
    progress: float = Field(default=0.0, ge=0.0, le=1.0)
    total_questions: int = Field(default=0)
    correct_answers: int = Field(default=0)
    study_time: int = Field(default=0)  # minutes
    last_studied: Optional[datetime] = None
    difficulty_level: str = Field(default="beginner")  # "beginner", "intermediate", "advanced"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        from_attributes = True


class QuizQuestion(BaseModel):
    """Quiz question model for learning assistant."""

    id: UUID = Field(default_factory=uuid4)
    topic: str
    question: str
    options: List[str] = Field(default_factory=list)
    correct_answer: int  # Index of correct option
    explanation: Optional[str] = None
    difficulty: str = Field(default="medium")  # "easy", "medium", "hard"
    tags: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        from_attributes = True


class CodeSnippet(BaseModel):
    """Code snippet model for code generation."""

    id: UUID = Field(default_factory=uuid4)
    user_id: UUID
    language: str
    title: str
    description: Optional[str] = None
    code: str
    tags: List[str] = Field(default_factory=list)
    complexity: str = Field(default="medium")  # "simple", "medium", "complex"
    generated_by_ai: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        from_attributes = True


# ===== NEW COMMAND TYPES FOR AUTOMATIONS =====

class AutomationCommandType(str, Enum):
    """Command types for automation features."""

    # Task Management
    CREATE_TASK = "create_task"
    LIST_TASKS = "list_tasks"
    UPDATE_TASK = "update_task"
    DELETE_TASK = "delete_task"

    # Document Processing
    UPLOAD_DOCUMENT = "upload_document"
    PROCESS_DOCUMENT = "process_document"
    SEARCH_DOCUMENTS = "search_documents"

    # Financial Tracking
    ADD_EXPENSE = "add_expense"
    LIST_EXPENSES = "list_expenses"
    CREATE_BUDGET = "create_budget"
    ANALYZE_FINANCES = "analyze_finances"

    # Feed Monitoring
    ADD_FEED = "add_feed"
    REMOVE_FEED = "remove_feed"
    LIST_FEEDS = "list_feeds"
    GET_FEED_UPDATES = "get_feed_updates"

    # Email Integration
    CONNECT_EMAIL = "connect_email"
    DISCONNECT_EMAIL = "disconnect_email"
    CHECK_EMAIL = "check_email"

    # Learning Assistant
    START_LESSON = "start_lesson"
    TAKE_QUIZ = "take_quiz"
    GET_PROGRESS = "get_progress"

    # Code Generation
    GENERATE_CODE = "generate_code"
    EXPLAIN_CODE = "explain_code"

    # Voice Commands
    VOICE_TASK_CREATE = "voice_task_create"
    VOICE_EXPENSE_ADD = "voice_expense_add"
    VOICE_REMINDER_SET = "voice_reminder_set"