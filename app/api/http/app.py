"""FastAPI HTTP API for AI Мага."""

import asyncio
from contextlib import asynccontextmanager
from typing import Any, Dict, Optional
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.core.di import init_container
from app.core.errors import handle_error
from app.core.logging import configure_logging
from app.core.metrics import get_health_status, metrics
from app.services.llm.yandex_gpt import yandex_gpt
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


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    configure_logging()
    init_container()

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

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: Configure properly for production
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
    text: str = Field(..., description="Text to translate"),
    target_lang: str = Field("en", description="Target language"),
    source_lang: Optional[str] = Field(None, description="Source language"),
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


@app.get("/v1/status", summary="System status", tags=["Status"])
async def system_status() -> Dict[str, Any]:
    """Get detailed system status."""
    return {
        "status": "operational",
        "version": "0.1.0",
        "components": {
            "database": "unknown",  # TODO: Check DB status
            "redis": "unknown",     # TODO: Check Redis status
            "voice": "unknown",     # TODO: Check voice status
            "llm": "available",     # GPT is available
        },
        "features": {
            "voice_assistant": False,  # TODO: Check voice status
            "telegram_bot": False,     # TODO: Check bot status
            "hh_integration": False,   # TODO: Check HH status
            "linkedin_integration": False,  # TODO: Check LinkedIn status
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
