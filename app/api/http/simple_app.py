"""Simple FastAPI app for testing."""

from fastapi import FastAPI, Request

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
async def telegram_webhook(request: Request):
    """Telegram webhook endpoint."""
    # Get JSON data
    data = await request.json()

    # Basic message processing
    message = data.get("message", {})
    text = message.get("text", "")

    if text.startswith("/start"):
        return {"status": "start command received"}
    elif text.startswith("/help"):
        return {"status": "help command received"}
    else:
        return {"status": "message received"}
