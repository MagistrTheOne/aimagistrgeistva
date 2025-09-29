"""Telegram webhook handler."""

import json
from typing import Any, Dict

from fastapi import APIRouter, HTTPException, Request

from app.core.logging import get_structlog_logger
from app.services.integrations.telegram import telegram_service

router = APIRouter(prefix="/telegram", tags=["telegram"])
logger = get_structlog_logger(__name__)


@router.post("/webhook")
async def telegram_webhook(request: Request) -> Dict[str, Any]:
    """
    Handle Telegram webhook updates.

    Telegram sends updates via POST requests to this endpoint.
    """
    try:
        # Get raw JSON data
        update_data = await request.json()

        # Write to debug file
        with open("/tmp/webhook_debug.log", "a") as f:
            f.write(f"===== WEBHOOK RECEIVED =====\n")
            f.write(f"Update data: {str(update_data)[:500]}\n")
            f.write(f"Timestamp: {__import__('time').time()}\n\n")

        print(f"DEBUG: ===== WEBHOOK RECEIVED =====")
        print(f"DEBUG: Update data: {str(update_data)[:500]}")

        logger.info(
            "Received Telegram update",
            update_id=update_data.get("update_id"),
            message_text=update_data.get("message", {}).get("text", "unknown"),
            chat_id=update_data.get("message", {}).get("chat", {}).get("id")
        )

        # Extract message data
        message = update_data.get("message", {})
        if not message:
            # Handle callback queries (button clicks)
            callback_query = update_data.get("callback_query", {})
            if callback_query:
                print(f"DEBUG: Handling callback query: {str(callback_query)[:200]}")
            return await _handle_callback_query(callback_query)
            print("DEBUG: No message or callback in update")
            return {"ok": True}

        # Extract message details
        chat_id = message.get("chat", {}).get("id")
        message_id = message.get("message_id")
        text = message.get("text")
        voice = message.get("voice")

        print(f"DEBUG: Extracted data - chat_id: {chat_id}, message_id: {message_id}, text: {text[:100]}")

        if not chat_id or not message_id:
            print(f"DEBUG: Invalid message format")
            return {"ok": True}

        # Handle different message types
        if text:
            print(f"DEBUG: Processing text message: {text[:100]}")

            # For testing - respond to any message
            with open("/tmp/webhook_debug.log", "a") as f:
                f.write(f"===== RECEIVED MESSAGE: {text} =====\n")
            print(f"DEBUG: ===== RECEIVED MESSAGE: {text} =====")

            # Simple test response
            if text and len(text.strip()) > 0:
                print(f"DEBUG: ===== MESSAGE PROCESSED SUCCESSFULLY =====")
                return {"status": "message_processed"}

            try:
                print("DEBUG: Calling process_text_message...")
                # Handle text messages (including commands)
                await telegram_service.process_text_message(chat_id, text, message_id)
                print("DEBUG: Text message processed successfully")
            except Exception as e:
                print(f"DEBUG: Error in process_text_message: {e}")
                raise
        elif voice:
            print("DEBUG: Processing voice message")
            # Handle voice messages
            voice_file_id = voice.get("file_id")
            if voice_file_id:
                await telegram_service.process_voice_message(chat_id, voice_file_id, message_id)
            else:
                print("DEBUG: Voice message without file_id")
        else:
            print("DEBUG: Unknown message type, sending help")
            # Unknown message type - send help
            await telegram_service.send_message(
                chat_id=chat_id,
                text="Извините, я пока умею работать только с текстовыми и голосовыми сообщениями. Используйте /help для справки.",
                reply_to_message_id=message_id
            )

        return {"ok": True}

    except Exception as e:
        print(f"DEBUG: ===== EXCEPTION IN WEBHOOK: {e} =====")
        logger.error(
            "Error processing Telegram webhook",
            error=str(e),
            error_type=type(e).__name__
        )
        raise HTTPException(status_code=500, detail="Internal server error")


async def _handle_callback_query(callback_query: Dict[str, Any]) -> Dict[str, Any]:
    """Handle callback query from inline buttons."""
    try:
        query_id = callback_query.get("id")
        chat_id = callback_query.get("message", {}).get("chat", {}).get("id")
        message_id = callback_query.get("message", {}).get("message_id")
        callback_data = callback_query.get("data")

        if not all([query_id, chat_id, message_id, callback_data]):
            logger.warning("Invalid callback query format", callback_query=callback_query)
            return {"ok": True}

        # Process the callback
        await telegram_service.process_callback_query(chat_id, callback_data, message_id)

        # Answer the callback query (remove loading state from button)
        return {
            "method": "answerCallbackQuery",
            "callback_query_id": query_id
        }

    except Exception as e:
        logger.error(
            "Error processing callback query",
            error=str(e),
            callback_query=callback_query
        )
        return {"ok": True}


@router.get("/health")
async def telegram_health() -> Dict[str, str]:
    """Health check endpoint for Telegram webhook."""
    return {"status": "ok", "service": "telegram-webhook"}


@router.get("/debug")
async def telegram_debug() -> Dict[str, Any]:
    """Debug endpoint to read webhook logs."""
    try:
        with open("/tmp/webhook_debug.log", "r") as f:
            content = f.read()
        return {"debug_log": content[-2000:]}  # Last 2000 chars
    except FileNotFoundError:
        return {"debug_log": "No debug file found"}
    except Exception as e:
        return {"error": str(e)}
