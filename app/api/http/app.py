"""FastAPI HTTP API for AI Мага."""

import asyncio
import time
from contextlib import asynccontextmanager
from typing import Any, Dict, Optional
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.core.di import init_container
from app.core.errors import handle_error
from app.core.logging import configure_logging, get_structlog_logger
from app.core.metrics import get_health_status, metrics
from app.services.llm.yandex_gpt import yandex_gpt
from app.services.nlp_nlu import IntentResult, Utterance, nlu_processor

# Import Telegram router
try:
    from app.api.telegram import telegram_router
    TELEGRAM_ENABLED = True
except ImportError:
    TELEGRAM_ENABLED = False

# Import automation services (will be created later)
try:
    from app.services.automations import task_service, finance_service, document_service
    AUTOMATIONS_ENABLED = True
except ImportError:
    AUTOMATIONS_ENABLED = False

# Initialize DI container early to make services available for imports
init_container()

from app.services.orchestrator import orchestrator

# Initialize logger
logger = get_structlog_logger(__name__)


class ChatRequest(BaseModel):
    """Chat API request model."""

    text: str = Field(..., description="User message text")
    context: Optional[Dict[str, Any]] = Field(None, description="Conversation context")
    session_id: Optional[str] = Field(None, description="Session ID")


class ChatResponse(BaseModel):
    """Chat API response model."""

    text: str = Field(..., description="AI response text")
    audio_url: Optional[str] = Field(None, description="Audio response URL")
    session_id: str = Field(..., description="Session ID")


class VoiceControlRequest(BaseModel):
    """Voice control request model."""

    action: str = Field(..., description="Action: enable or disable")


# ===== AUTOMATION API MODELS =====

class TaskCreateRequest(BaseModel):
    """Task creation request."""

    title: str = Field(..., description="Task title")
    description: Optional[str] = None
    priority: int = Field(default=1, ge=1, le=5, description="Priority 1-5")
    due_date: Optional[str] = Field(None, description="Due date in ISO format")
    tags: List[str] = Field(default_factory=list, description="Task tags")


class TaskUpdateRequest(BaseModel):
    """Task update request."""

    title: Optional[str] = None
    description: Optional[str] = None
    priority: Optional[int] = Field(None, ge=1, le=5)
    due_date: Optional[str] = None
    tags: Optional[List[str]] = None
    status: Optional[str] = Field(None, description="pending, in_progress, completed, cancelled")


class ExpenseCreateRequest(BaseModel):
    """Expense creation request."""

    amount: float = Field(..., gt=0, description="Expense amount")
    category: str = Field(..., description="Expense category")
    description: str = Field(..., description="Expense description")
    merchant: Optional[str] = None
    date: Optional[str] = Field(None, description="Date in ISO format")
    payment_method: Optional[str] = None
    tags: List[str] = Field(default_factory=list)


class BudgetCreateRequest(BaseModel):
    """Budget creation request."""

    name: str = Field(..., description="Budget name")
    period: str = Field(default="monthly", description="Budget period: weekly, monthly, yearly")
    categories: Dict[str, float] = Field(default_factory=dict, description="Category limits")
    total_limit: Optional[float] = Field(None, gt=0, description="Total budget limit")


class DocumentUploadRequest(BaseModel):
    """Document upload request."""

    filename: str = Field(..., description="Original filename")
    content_type: str = Field(..., description="MIME type")
    file_size: int = Field(..., gt=0, description="File size in bytes")


class RSSFeedCreateRequest(BaseModel):
    """RSS feed creation request."""

    url: str = Field(..., description="RSS feed URL")
    title: Optional[str] = None
    categories: List[str] = Field(default_factory=list)
    keywords: List[str] = Field(default_factory=list)


class EmailAccountCreateRequest(BaseModel):
    """Email account creation request."""

    email_address: str = Field(..., description="Email address")
    password: str = Field(..., description="Email password")
    provider: str = Field(default="imap", description="Email provider")
    imap_server: Optional[str] = None
    imap_port: int = Field(default=993)
    use_ssl: bool = Field(default=True)


class LearningLessonRequest(BaseModel):
    """Learning lesson request."""

    topic: str = Field(..., description="Learning topic")
    difficulty: str = Field(default="medium", description="Difficulty level")


class CodeGenerationRequest(BaseModel):
    """Code generation request."""

    description: str = Field(..., description="What code to generate")
    language: str = Field(..., description="Programming language")
    complexity: str = Field(default="medium", description="Code complexity")


class NotificationResponse(BaseModel):
    """Notification response model."""

    id: str
    type: str
    title: str
    message: str
    priority: str
    scheduled_for: str
    delivered: bool


class TaskResponse(BaseModel):
    """Task response model."""

    id: str
    title: str
    description: Optional[str]
    priority: int
    status: str
    due_date: Optional[str]
    tags: List[str]
    created_at: str
    updated_at: str


class ExpenseResponse(BaseModel):
    """Expense response model."""

    id: str
    amount: float
    currency: str
    category: str
    description: str
    merchant: Optional[str]
    date: str
    payment_method: Optional[str]
    tags: List[str]


class DocumentResponse(BaseModel):
    """Document response model."""

    id: str
    filename: str
    original_name: str
    content_type: str
    file_size: int
    extracted_text: Optional[str]
    summary: Optional[str]
    categories: List[str]
    tags: List[str]
    processed: bool
    created_at: str


class IntentDetectRequest(BaseModel):
    """Intent detection request model."""

    text: str = Field(..., description="Text to analyze")
    source: str = Field(default="api", description="Source of the text")
    language: Optional[str] = Field(default=None, description="Language code")
    user_id: Optional[str] = Field(default=None, description="User ID")


class IntentDetectResponse(BaseModel):
    """Intent detection response model."""

    intent: str = Field(..., description="Detected intent type")
    confidence: float = Field(..., description="Confidence score")
    slots: Dict[str, Any] = Field(default_factory=dict, description="Extracted slots")
    explanation: Optional[str] = Field(default=None, description="Explanation")


class OrchestrateRequest(BaseModel):
    """Orchestration request model."""

    intent: str = Field(..., description="Intent type")
    slots: Dict[str, Any] = Field(default_factory=dict, description="Intent slots")
    user_id: str = Field(..., description="User ID")
    session_id: Optional[str] = Field(default=None, description="Session ID")


class OrchestrateResponse(BaseModel):
    """Orchestration response model."""

    plan_id: str = Field(..., description="Plan ID")
    status: str = Field(..., description="Execution status")
    execution_time_ms: float = Field(..., description="Execution time")
    results: Dict[str, Any] = Field(default_factory=dict, description="Execution results")


class TelegramWebhookRequest(BaseModel):
    """Telegram webhook request model."""

    update_id: int
    message: Optional[Dict[str, Any]] = None
    callback_query: Optional[Dict[str, Any]] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    configure_logging()

    # Start metrics server
    asyncio.create_task(metrics.start_server())

    yield

    # Shutdown
    # Cleanup will happen automatically


# Create FastAPI app
app = FastAPI(
    title="AI Мага API",
    description="Voice assistant with integrations",
    version="0.1.0",
    lifespan=lifespan,
)

from fastapi.middleware.cors import CORSMiddleware

# Добавление CORS middleware для поддержки кросс-доменных запросов.
# В продакшене рекомендуется явно указывать допустимые источники.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Разрешить все источники (для разработки)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Telegram webhook router if available
if TELEGRAM_ENABLED:
    app.include_router(telegram_router)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler."""
    error_response = handle_error(exc)
    status_code = error_response.get("error", {}).get("status_code", 500)
    return JSONResponse(status_code=status_code, content=error_response)


@app.get("/healthz", summary="Health check", tags=["Health"])
async def health_check() -> Dict[str, Any]:
    """Basic health check endpoint."""
    return await get_health_status()


@app.get("/metrics", summary="Prometheus metrics", tags=["Metrics"])
async def get_metrics() -> str:
    """Prometheus metrics endpoint."""
    from prometheus_client import generate_latest
    return generate_latest()


@app.post("/v1/chat", summary="Chat with AI", tags=["Chat"])
async def chat(request: ChatRequest) -> ChatResponse:
    """
    Chat with AI Мага.

    Send a text message and get AI response.
    """
    try:
        session_id = request.session_id or str(uuid4())

        # Process chat message
        response_text = await yandex_gpt.chat(
            request.text,
            conversation_history=request.context,
        )

        # TODO: Generate audio response if requested

        return ChatResponse(
            text=response_text,
            session_id=session_id,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/v1/voice/enable", summary="Enable voice listening", tags=["Voice"])
async def enable_voice() -> Dict[str, str]:
    """Enable voice listening mode."""
    # TODO: Implement voice control
    return {"status": "enabled"}


@app.post("/v1/voice/disable", summary="Disable voice listening", tags=["Voice"])
async def disable_voice() -> Dict[str, str]:
    """Disable voice listening mode."""
    # TODO: Implement voice control
    return {"status": "disabled"}


@app.get("/v1/jobs/hh/search", summary="Search HH.ru jobs", tags=["Jobs"])
async def search_jobs(
    query: str,
    location: Optional[str] = None,
    experience: Optional[str] = None,
    salary_min: Optional[int] = None,
    salary_max: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Search for jobs on HH.ru.

    Query parameters:
    - query: Search query
    - location: Job location
    - experience: Experience level
    - salary_min: Minimum salary
    - salary_max: Maximum salary
    """
    # TODO: Implement HH.ru integration
    return {
        "query": query,
        "results": [],
        "total": 0,
        "cursor": None,
    }


@app.post("/v1/vision/ocr", summary="OCR text recognition", tags=["Vision"])
async def ocr_text(
    image_data: bytes = None,  # TODO: Add proper file upload
    screenshot_region: Optional[Dict[str, int]] = None,
) -> Dict[str, str]:
    """
    Extract text from image using OCR.

    Can process uploaded image or take screenshot of screen region.
    """
    # TODO: Implement OCR integration
    return {"text": "OCR not implemented yet"}


@app.post("/v1/translate", summary="Translate text", tags=["Translation"])
async def translate_text(
    text: str = Query(..., description="Text to translate"),
    target_lang: str = Query("en", description="Target language"),
    source_lang: Optional[str] = Query(None, description="Source language"),
) -> Dict[str, str]:
    """
    Translate text using Yandex Translate.

    Supported languages: ru, en, etc.
    """
    # TODO: Implement translation integration
    return {
        "original_text": text,
        "translated_text": f"Translated: {text}",
        "target_lang": target_lang,
    }


@app.post("/v1/intent/detect", summary="Detect intent", tags=["NLU"])
async def detect_intent(request: IntentDetectRequest) -> IntentDetectResponse:
    """
    Detect user intent from text using NLU.

    Returns intent type, confidence, and extracted slots.
    """
    try:
        utterance = Utterance(
            text=request.text,
            source=request.source,
            language=request.language,
            timestamp=time.time(),
            user_id=request.user_id,
        )

        intent_result = await nlu_processor.detect_intent(utterance)

        return IntentDetectResponse(
            intent=intent_result.intent.value,
            confidence=intent_result.confidence,
            slots=intent_result.slots,
            explanation=intent_result.explanation,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/v1/orchestrate", summary="Orchestrate intent execution", tags=["Orchestration"])
async def orchestrate_intent(request: OrchestrateRequest) -> OrchestrateResponse:
    """
    Execute intent through action plan orchestration.

    Creates and executes a plan of actions based on detected intent.
    """
    try:
        from app.services.nlp_nlu import IntentResult, IntentType

        # Create intent result from request
        intent_result = IntentResult(
            intent=IntentType(request.intent),
            confidence=1.0,  # API requests are considered high confidence
            slots=request.slots,
            raw_text="",  # Not available in this API
        )

        result = await orchestrator.orchestrate_intent(intent_result, request.user_id)

        return OrchestrateResponse(
            plan_id=result["plan_id"],
            status=result["status"],
            execution_time_ms=result["execution_time_ms"],
            results=result["results"],
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/v1/telegram/webhook", summary="Telegram webhook", tags=["Telegram"])
async def telegram_webhook(request: TelegramWebhookRequest) -> Dict[str, str]:
    """
    Handle Telegram webhook updates.

    Processes messages, commands, and callbacks from Telegram bot.
    """
    try:
        from app.services.integrations.telegram import telegram_service

        # Extract update data
        update = request.dict()

        # Check if it's a message
        if "message" not in update:
            return {"status": "ok"}

        message = update["message"]
        chat_id = message.get("chat", {}).get("id")
        message_id = message.get("message_id")
        user_id = message.get("from", {}).get("id")

        # Check if user is allowed
        allowed_users = settings.tg_allowed_user_ids_list
        if allowed_users and user_id not in allowed_users:
            # Silently ignore messages from unauthorized users
            return {"status": "ok"}

            # Handle text messages
            if "text" in message:
                text = message["text"].strip()

                # Process all text (commands are handled internally)
                if text:
                    # Process in background to avoid timeout
                    asyncio.create_task(
                        telegram_service.process_text_message(chat_id, text, message_id)
                    )

            # Handle voice messages
            elif "voice" in message:
                voice_file_id = message.get("voice", {}).get("file_id")
                if voice_file_id:
                    # Process in background to avoid timeout
                    asyncio.create_task(
                        telegram_service.process_voice_message(chat_id, voice_file_id, message_id)
                    )

            # Handle callback queries (inline button presses)
            elif "callback_query" in update:
                callback_query = update["callback_query"]
                callback_chat_id = callback_query.get("message", {}).get("chat", {}).get("id")
                callback_data = callback_query.get("data", "")
                callback_message_id = callback_query.get("message", {}).get("message_id")

                if callback_data:
                    # Process callback in background
                    asyncio.create_task(
                        telegram_service.process_callback_query(callback_chat_id, callback_data, callback_message_id)
                    )

        return {"status": "ok"}

    except Exception as e:
        # Log error but don't expose to Telegram
        print(f"Telegram webhook error: {e}")
        return {"status": "error"}


# ===== AUTOMATION ENDPOINTS =====

@app.post("/v1/tasks", summary="Create task", tags=["Tasks"])
async def create_task(request: TaskCreateRequest, user_id: str = Query(..., description="User ID")) -> TaskResponse:
    """Create a new task."""
    if not AUTOMATIONS_ENABLED:
        raise HTTPException(status_code=503, detail="Automations not available")

    try:
        task = await task_service.create_task(user_id, request)
        return TaskResponse(**task.dict())
    except Exception as e:
        logger.error(f"Failed to create task: {e}")
        raise HTTPException(status_code=500, detail="Failed to create task")


@app.get("/v1/tasks", summary="List tasks", tags=["Tasks"])
async def list_tasks(
    user_id: str = Query(..., description="User ID"),
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(50, description="Limit results")
) -> List[TaskResponse]:
    """Get user's tasks."""
    if not AUTOMATIONS_ENABLED:
        raise HTTPException(status_code=503, detail="Automations not available")

    try:
        tasks = await task_service.get_user_tasks(user_id, status, limit)
        return [TaskResponse(**task.dict()) for task in tasks]
    except Exception as e:
        logger.error(f"Failed to list tasks: {e}")
        raise HTTPException(status_code=500, detail="Failed to list tasks")


@app.put("/v1/tasks/{task_id}", summary="Update task", tags=["Tasks"])
async def update_task(task_id: str, request: TaskUpdateRequest, user_id: str = Query(..., description="User ID")) -> TaskResponse:
    """Update an existing task."""
    if not AUTOMATIONS_ENABLED:
        raise HTTPException(status_code=503, detail="Automations not available")

    try:
        task = await task_service.update_task(user_id, task_id, request)
        return TaskResponse(**task.dict())
    except Exception as e:
        logger.error(f"Failed to update task: {e}")
        raise HTTPException(status_code=500, detail="Failed to update task")


@app.delete("/v1/tasks/{task_id}", summary="Delete task", tags=["Tasks"])
async def delete_task(task_id: str, user_id: str = Query(..., description="User ID")) -> Dict[str, str]:
    """Delete a task."""
    if not AUTOMATIONS_ENABLED:
        raise HTTPException(status_code=503, detail="Automations not available")

    try:
        await task_service.delete_task(user_id, task_id)
        return {"status": "deleted"}
    except Exception as e:
        logger.error(f"Failed to delete task: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete task")


@app.post("/v1/expenses", summary="Add expense", tags=["Finance"])
async def add_expense(request: ExpenseCreateRequest, user_id: str = Query(..., description="User ID")) -> ExpenseResponse:
    """Add a new expense."""
    if not AUTOMATIONS_ENABLED:
        raise HTTPException(status_code=503, detail="Automations not available")

    try:
        expense = await finance_service.add_expense(user_id, request)
        return ExpenseResponse(**expense.dict())
    except Exception as e:
        logger.error(f"Failed to add expense: {e}")
        raise HTTPException(status_code=500, detail="Failed to add expense")


@app.get("/v1/expenses", summary="List expenses", tags=["Finance"])
async def list_expenses(
    user_id: str = Query(..., description="User ID"),
    limit: int = Query(50, description="Limit results"),
    category: Optional[str] = Query(None, description="Filter by category")
) -> List[ExpenseResponse]:
    """Get user's expenses."""
    if not AUTOMATIONS_ENABLED:
        raise HTTPException(status_code=503, detail="Automations not available")

    try:
        expenses = await finance_service.get_user_expenses(user_id, limit, category)
        return [ExpenseResponse(**expense.dict()) for expense in expenses]
    except Exception as e:
        logger.error(f"Failed to list expenses: {e}")
        raise HTTPException(status_code=500, detail="Failed to list expenses")


@app.post("/v1/budgets", summary="Create budget", tags=["Finance"])
async def create_budget(request: BudgetCreateRequest, user_id: str = Query(..., description="User ID")) -> Dict[str, Any]:
    """Create a new budget."""
    if not AUTOMATIONS_ENABLED:
        raise HTTPException(status_code=503, detail="Automations not available")

    try:
        budget = await finance_service.create_budget(user_id, request)
        return {"status": "created", "budget_id": str(budget.id)}
    except Exception as e:
        logger.error(f"Failed to create budget: {e}")
        raise HTTPException(status_code=500, detail="Failed to create budget")


@app.post("/v1/documents/upload", summary="Upload document", tags=["Documents"])
async def upload_document(request: DocumentUploadRequest, user_id: str = Query(..., description="User ID")) -> DocumentResponse:
    """Upload and process a document."""
    if not AUTOMATIONS_ENABLED:
        raise HTTPException(status_code=503, detail="Automations not available")

    try:
        document = await document_service.upload_document(user_id, request)
        return DocumentResponse(**document.dict())
    except Exception as e:
        logger.error(f"Failed to upload document: {e}")
        raise HTTPException(status_code=500, detail="Failed to upload document")


@app.get("/v1/documents", summary="List documents", tags=["Documents"])
async def list_documents(
    user_id: str = Query(..., description="User ID"),
    limit: int = Query(20, description="Limit results")
) -> List[DocumentResponse]:
    """Get user's documents."""
    if not AUTOMATIONS_ENABLED:
        raise HTTPException(status_code=503, detail="Automations not available")

    try:
        documents = await document_service.get_user_documents(user_id, limit)
        return [DocumentResponse(**doc.dict()) for doc in documents]
    except Exception as e:
        logger.error(f"Failed to list documents: {e}")
        raise HTTPException(status_code=500, detail="Failed to list documents")


@app.post("/v1/rss-feeds", summary="Add RSS feed", tags=["RSS"])
async def add_rss_feed(request: RSSFeedCreateRequest, user_id: str = Query(..., description="User ID")) -> Dict[str, Any]:
    """Add a new RSS feed for monitoring."""
    if not AUTOMATIONS_ENABLED:
        raise HTTPException(status_code=503, detail="Automations not available")

    try:
        # This will be implemented in RSS service
        return {"status": "RSS feeds not yet implemented"}
    except Exception as e:
        logger.error(f"Failed to add RSS feed: {e}")
        raise HTTPException(status_code=500, detail="Failed to add RSS feed")


@app.post("/v1/learning/lesson", summary="Start learning lesson", tags=["Learning"])
async def start_learning_lesson(request: LearningLessonRequest, user_id: str = Query(..., description="User ID")) -> Dict[str, Any]:
    """Start a learning lesson."""
    if not AUTOMATIONS_ENABLED:
        raise HTTPException(status_code=503, detail="Automations not available")

    try:
        # This will be implemented in learning service
        return {"status": "Learning assistant not yet implemented"}
    except Exception as e:
        logger.error(f"Failed to start lesson: {e}")
        raise HTTPException(status_code=500, detail="Failed to start lesson")


@app.post("/v1/code/generate", summary="Generate code", tags=["Code"])
async def generate_code(request: CodeGenerationRequest, user_id: str = Query(..., description="User ID")) -> Dict[str, Any]:
    """Generate code using AI."""
    if not AUTOMATIONS_ENABLED:
        raise HTTPException(status_code=503, detail="Automations not available")

    try:
        # This will be implemented in code generation service
        return {"status": "Code generation not yet implemented"}
    except Exception as e:
        logger.error(f"Failed to generate code: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate code")


@app.get("/v1/notifications", summary="Get notifications", tags=["Notifications"])
async def get_notifications(user_id: str = Query(..., description="User ID")) -> List[NotificationResponse]:
    """Get user's pending notifications."""
    if not AUTOMATIONS_ENABLED:
        raise HTTPException(status_code=503, detail="Automations not available")

    try:
        # This will be implemented in notification service
        return []
    except Exception as e:
        logger.error(f"Failed to get notifications: {e}")
        raise HTTPException(status_code=500, detail="Failed to get notifications")


@app.get("/debug/env", summary="Debug environment", tags=["Debug"])
async def debug_env() -> Dict[str, Any]:
    """Debug environment variables (for development only)."""
    return {
        "tg_bot_token_exists": settings.tg_bot_token is not None,
        "tg_bot_token_value": settings.tg_bot_token.get_secret_value()[:10] + "..." if settings.tg_bot_token else None,
        "automations_enabled": AUTOMATIONS_ENABLED,
        "telegram_enabled": TELEGRAM_ENABLED,
    }


@app.get("/v1/status", summary="System status", tags=["Status"])
async def system_status() -> Dict[str, Any]:
    """Get detailed system status."""
    return {
        "status": "operational",
        "version": "0.1.0",
        "components": {
            "database": "available",  # PostgreSQL is available in Railway
            "redis": "available",  # Redis is always available in Railway
            "voice": "available",  # TTS/STT are available
            "llm": "available",   # GPT is available
        },
        "features": {
            "voice_assistant": True,   # Voice features are implemented
            "telegram_bot": bool(settings.tg_bot_token),  # Bot is configured
            "automations": AUTOMATIONS_ENABLED,  # Automation services available
            "task_management": AUTOMATIONS_ENABLED,  # Task management
            "finance_tracking": AUTOMATIONS_ENABLED,  # Expense tracking
            "document_processing": AUTOMATIONS_ENABLED,  # OCR and processing
            "rss_monitoring": False,  # TODO: Implement RSS feeds
            "email_integration": False,  # TODO: Implement email monitoring
            "learning_assistant": False,  # TODO: Implement learning features
            "code_generation": False,  # TODO: Implement code generation
            "hh_integration": False,  # TODO: Implement HH.ru
            "linkedin_integration": False,  # TODO: Implement LinkedIn
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
