"""Telegram Bot integration."""

import asyncio
import io
import json
from typing import Any, Dict, Optional

from app.adapters.http_client import http_client
from app.core.config import settings
from app.core.errors import IntegrationError
from app.core.metrics import metrics
from app.services.llm.yandex_gpt import yandex_gpt
from app.services.voice.stt import stt
from app.services.voice.tts import tts


class TelegramService:
    """Telegram Bot API integration."""

    def __init__(self):
        self.base_url = f"https://api.telegram.org/bot{settings.tg_bot_token.get_secret_value()}"

    async def send_message(
        self,
        chat_id: int,
        text: str,
        reply_to_message_id: Optional[int] = None,
        parse_mode: Optional[str] = None
    ) -> Dict[str, Any]:
        """Send text message to Telegram chat."""
        url = f"{self.base_url}/sendMessage"
        data = {
            "chat_id": chat_id,
            "text": text,
            "reply_to_message_id": reply_to_message_id,
        }
        if parse_mode:
            data["parse_mode"] = parse_mode

        try:
            response = await http_client.post(url, json=data)
            metrics.increment("telegram_messages_sent", type="text")
            return response
        except Exception as e:
            metrics.increment("telegram_messages_sent", type="text", status="error")
            raise IntegrationError(f"Failed to send Telegram message: {e}")

    async def send_voice(
        self,
        chat_id: int,
        voice_data: bytes,
        duration: Optional[int] = None,
        reply_to_message_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """Send voice message to Telegram chat."""
        url = f"{self.base_url}/sendVoice"

        # Convert audio data to file-like object
        voice_file = io.BytesIO(voice_data)
        voice_file.name = "voice.ogg"

        # Prepare multipart form data
        data = {
            "chat_id": str(chat_id),
            "voice": voice_file,
        }
        if duration:
            data["duration"] = str(duration)
        if reply_to_message_id:
            data["reply_to_message_id"] = str(reply_to_message_id)

        headers = {"Content-Type": "multipart/form-data"}

        try:
            # Note: This is a simplified implementation
            # In production, you might want to use aiohttp directly for file uploads
            response = await http_client.post(url, data=data, headers=headers)
            metrics.increment("telegram_messages_sent", type="voice")
            return response
        except Exception as e:
            metrics.increment("telegram_messages_sent", type="voice", status="error")
            raise IntegrationError(f"Failed to send Telegram voice: {e}")

    async def download_file(self, file_id: str) -> bytes:
        """Download file from Telegram servers."""
        # First get file info
        file_info_url = f"{self.base_url}/getFile"
        file_info = await http_client.post(file_info_url, json={"file_id": file_id})

        if not file_info.get("ok"):
            raise IntegrationError(f"Failed to get file info: {file_info}")

        file_path = file_info["result"]["file_path"]
        download_url = f"https://api.telegram.org/file/bot{settings.tg_bot_token.get_secret_value()}/{file_path}"

        try:
            response = await http_client.get(download_url)
            if isinstance(response, bytes):
                return response
            else:
                raise IntegrationError("Unexpected response type for file download")
        except Exception as e:
            raise IntegrationError(f"Failed to download file: {e}")

    async def process_text_message(self, chat_id: int, text: str, message_id: int) -> None:
        """Process text message and send response."""
        try:
            # Generate response using Yandex GPT
            response_text = await yandex_gpt.chat(
                text,
                session_id=f"telegram_{chat_id}"
            )

            # Send text response
            await self.send_message(
                chat_id=chat_id,
                text=response_text,
                reply_to_message_id=message_id
            )

            # Generate voice response
            voice_data = await tts.synthesize(
                text=response_text,
                language="ru-RU",
                format="oggopus"  # Telegram prefers OGG Opus for voice messages
            )

            # Send voice response
            await self.send_voice(
                chat_id=chat_id,
                voice_data=voice_data,
                reply_to_message_id=message_id
            )

        except Exception as e:
            error_msg = "Извините, произошла ошибка при обработке сообщения."
            await self.send_message(chat_id=chat_id, text=error_msg)
            raise

    async def process_voice_message(self, chat_id: int, voice_file_id: str, message_id: int) -> None:
        """Process voice message and send response."""
        try:
            # Download voice file
            voice_data = await self.download_file(voice_file_id)

            # Transcribe speech to text
            transcription_result = await stt.transcribe(voice_data)

            if not transcription_result.get("text"):
                await self.send_message(
                    chat_id=chat_id,
                    text="Не удалось распознать речь. Попробуйте еще раз.",
                    reply_to_message_id=message_id
                )
                return

            user_text = transcription_result["text"]

            # Confirm transcription
            await self.send_message(
                chat_id=chat_id,
                text=f"🎤 Распознано: {user_text}",
                reply_to_message_id=message_id
            )

            # Generate response using Yandex GPT
            response_text = await yandex_gpt.chat(
                user_text,
                session_id=f"telegram_{chat_id}"
            )

            # Send text response
            await self.send_message(
                chat_id=chat_id,
                text=f"💬 {response_text}",
                reply_to_message_id=message_id
            )

            # Generate voice response
            voice_data = await tts.synthesize(
                text=response_text,
                language="ru-RU",
                format="oggopus"
            )

            # Send voice response
            await self.send_voice(
                chat_id=chat_id,
                voice_data=voice_data,
                reply_to_message_id=message_id
            )

        except Exception as e:
            error_msg = "Извините, произошла ошибка при обработке голосового сообщения."
            await self.send_message(chat_id=chat_id, text=error_msg)
            raise


# Global Telegram service instance
telegram_service = TelegramService()
