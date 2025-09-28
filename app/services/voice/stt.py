"""Speech-to-Text using Yandex SpeechKit."""

import asyncio
import base64
import json
from typing import Any, Dict, Optional

from app.adapters.http_client import http_client
from app.core.config import settings
from app.core.errors import VoiceProcessingError
from app.core.metrics import metrics


class YandexSTT:
    """Yandex SpeechKit STT integration."""

    def __init__(self):
        self.base_url = "https://stt.api.cloud.yandex.net/speech/v1/stt:recognize"
        self.iam_token = None
        self.token_expires = 0

    async def _get_iam_token(self) -> str:
        """Get IAM token for Yandex Cloud authentication."""
        current_time = asyncio.get_event_loop().time()

        # Check if token is still valid (with 5 minute buffer)
        if self.iam_token and current_time < self.token_expires - 300:
            return self.iam_token

        try:
            # For OAuth token, we can use it directly
            # In production, you might want to exchange OAuth for IAM token
            # For now, we'll use OAuth token directly
            self.iam_token = settings.yc_oauth_token.get_secret_value()
            self.token_expires = current_time + 3600  # Assume 1 hour validity
            return self.iam_token

        except Exception as e:
            raise VoiceProcessingError(f"Failed to get IAM token: {e}")

    async def transcribe(
        self,
        audio_data: bytes,
        language: str = "ru-RU",
        sample_rate: int = 16000,
        model: Optional[str] = None,
        enable_profanity_filter: bool = True,
    ) -> Dict[str, Any]:
        """
        Transcribe audio to text using Yandex SpeechKit.

        Args:
            audio_data: Raw PCM audio data (16-bit)
            language: Language code (ru-RU, en-US, etc.)
            sample_rate: Audio sample rate
            model: STT model to use
            enable_profanity_filter: Whether to filter profanity

        Returns:
            Dict with transcription results
        """
        metrics.histogram("stt_request_duration", 0, stage="start")

        try:
            token = await self._get_iam_token()

            # Prepare request data
            audio_b64 = base64.b64encode(audio_data).decode('utf-8')

            data = {
                "audio": {
                    "content": audio_b64
                },
                "config": {
                    "specification": {
                        "languageCode": language,
                        "model": model or settings.yandex_stt_model,
                        "profanityFilter": enable_profanity_filter,
                        "literatureText": False,
                        "audioEncoding": "LINEAR16",
                        "sampleRateHertz": sample_rate,
                    }
                }
            }

            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            }

            # Make request
            response_data = await http_client.post(
                self.base_url,
                json=data,
                headers=headers,
            )

            # Parse response
            result = self._parse_response(response_data)

            metrics.increment("stt_requests_total", status="success")
            metrics.histogram("stt_request_duration", 1, stage="complete")

            return result

        except Exception as e:
            metrics.increment("stt_requests_total", status="error")
            metrics.histogram("stt_request_duration", 1, stage="error")
            raise VoiceProcessingError(f"STT transcription failed: {e}")

    def _parse_response(self, response_data: Dict[str, Any]) -> Dict[str, Any]:
        """Parse Yandex STT API response."""
        if "result" not in response_data:
            raise VoiceProcessingError("Invalid STT response: missing result")

        result = response_data["result"]

        # Extract alternatives
        alternatives = []
        if "alternatives" in result:
            for alt in result["alternatives"]:
                alternatives.append({
                    "text": alt.get("text", ""),
                    "confidence": alt.get("confidence", 0.0),
                })

        # Get best result
        best_text = ""
        best_confidence = 0.0

        if alternatives:
            best_alt = max(alternatives, key=lambda x: x["confidence"])
            best_text = best_alt["text"]
            best_confidence = best_alt["confidence"]

        return {
            "text": best_text,
            "confidence": best_confidence,
            "alternatives": alternatives,
            "language": result.get("language", "unknown"),
        }

    async def transcribe_streaming(
        self,
        audio_stream,
        language: str = "ru-RU",
        sample_rate: int = 16000,
        model: Optional[str] = None,
    ):
        """
        Streaming transcription (placeholder for future implementation).

        Yandex SpeechKit supports streaming, but this is a simplified version.
        """
        # For now, just collect all audio and transcribe at once
        audio_data = b""
        async for chunk in audio_stream:
            audio_data += chunk

        return await self.transcribe(audio_data, language, sample_rate, model)


class MockSTT:
    """Mock STT for testing and development."""

    async def transcribe(
        self,
        audio_data: bytes,
        language: str = "ru-RU",
        **kwargs
    ) -> Dict[str, Any]:
        """Mock transcription - returns dummy text."""
        # Simulate processing time
        await asyncio.sleep(0.1)

        # Return mock result
        mock_texts = [
            "Мага, какой сегодня день недели?",
            "Мага, включи музыку",
            "Мага, напомни мне о встрече",
            "Мага, переведи этот текст",
            "Мага, что такое искусственный интеллект?",
        ]

        import random
        text = random.choice(mock_texts)

        return {
            "text": text,
            "confidence": 0.95,
            "alternatives": [{"text": text, "confidence": 0.95}],
            "language": language,
        }


# Choose STT implementation
if settings.is_prod or settings.yc_oauth_token:
    stt = YandexSTT()
else:
    print("Using mock STT (no Yandex credentials)")
    stt = MockSTT()
