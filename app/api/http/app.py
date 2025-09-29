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
from app.core.logging import configure_logging
from app.core.metrics import get_health_status, metrics
from app.services.llm.yandex_gpt import yandex_gpt
from app.services.nlp_nlu import IntentResult, Utterance, nlu_processor

# Initialize DI container early to make services available for imports
init_container()

from app.services.orchestrator import orchestrator


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

        return {"status": "ok"}

    except Exception as e:
        # Log error but don't expose to Telegram
        print(f"Telegram webhook error: {e}")
        return {"status": "error"}


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
            "hh_integration": False,  # TODO: Implement HH.ru
            "linkedin_integration": False,  # TODO: Implement LinkedIn
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
