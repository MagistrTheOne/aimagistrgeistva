"""FastAPI HTTP API for AI Мага."""

from fastapi import FastAPI

# Create FastAPI app
app = FastAPI(
    title="AI Мага API",
    description="AI-powered personal assistant API",
    version="0.1.0",
)

@app.get("/healthz")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}

@app.get("/test")
async def test_endpoint():
    """Test endpoint."""
    return {"status": "test working"}

@app.post("/v1/telegram/webhook")
async def telegram_webhook():
    """Telegram webhook endpoint."""
    return {"status": "webhook received"}