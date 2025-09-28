"""Text-to-Speech using Yandex SpeechKit."""

import asyncio
import base64
from typing import Any, Dict, Optional

from app.adapters.http_client import http_client
from app.core.config import settings
from app.core.errors import VoiceProcessingError
from app.core.metrics import metrics


class YandexTTS:
    """Yandex SpeechKit TTS integration."""

    def __init__(self):
        self.base_url = "https://tts.api.cloud.yandex.net/speech/v1/tts:synthesize"
        self.iam_token = None
        self.token_expires = 0

    async def _get_iam_token(self) -> str:
        """Get IAM token for Yandex Cloud authentication."""
        current_time = asyncio.get_event_loop().time()

        # Check if token is still valid (with 5 minute buffer)
        if self.iam_token and current_time < self.token_expires - 300:
            return self.iam_token

        try:
            # Use OAuth token directly
            self.iam_token = settings.yc_oauth_token.get_secret_value()
            self.token_expires = current_time + 3600  # Assume 1 hour validity
            return self.iam_token

        except Exception as e:
            raise VoiceProcessingError(f"Failed to get IAM token: {e}")

    async def synthesize(
        self,
        text: str,
        language: str = "ru-RU",
        voice: Optional[str] = None,
        speed: float = 1.0,
        emotion: Optional[str] = None,
        format: str = "lpcm",
        sample_rate: int = 16000,
    ) -> bytes:
        """
        Synthesize speech from text using Yandex SpeechKit.

        Args:
            text: Text to synthesize
            language: Language code (ru-RU, en-US, etc.)
            voice: Voice to use
            speed: Speech speed (0.1-3.0)
            emotion: Emotion for speech (if supported)
            format: Audio format (lpcm, oggopus, mp3)
            sample_rate: Sample rate for lpcm format

        Returns:
            Audio data as bytes
        """
        metrics.histogram("tts_request_duration", 0, stage="start")

        try:
            token = await self._get_iam_token()

            # Select voice based on language
            if not voice:
                if language.startswith("ru"):
                    voice = settings.yandex_tts_voice
                elif language.startswith("en"):
                    voice = settings.yandex_tts_voice_en
                else:
                    voice = "ermil"  # Default

            # Prepare request data
            data = {
                "text": text,
                "lang": language,
                "voice": voice,
                "speed": max(0.1, min(3.0, speed)),  # Clamp to valid range
                "format": format,
                "sampleRateHertz": sample_rate if format == "lpcm" else None,
            }

            # Remove None values
            data = {k: v for k, v in data.items() if v is not None}

            headers = {
                "Authorization": f"Bearer {token}",
            }

            # Make request
            response = await http_client.post(
                self.base_url,
                data=data,
                headers=headers,
            )

            # Extract audio data
            if isinstance(response, dict):
                # If JSON response
                audio_b64 = response.get("audio", "")
                audio_data = base64.b64decode(audio_b64)
            else:
                # If raw audio response
                audio_data = response

            if not audio_data:
                raise VoiceProcessingError("No audio data in TTS response")

            metrics.increment("tts_requests_total", status="success")
            metrics.histogram("tts_request_duration", 1, stage="complete")

            return audio_data

        except Exception as e:
            metrics.increment("tts_requests_total", status="error")
            metrics.histogram("tts_request_duration", 1, stage="error")
            raise VoiceProcessingError(f"TTS synthesis failed: {e}")

    async def get_voices(self) -> Dict[str, Any]:
        """Get available voices (placeholder - Yandex doesn't have a list endpoint)."""
        # Yandex SpeechKit doesn't provide a list voices endpoint
        # Return known voices
        return {
            "ru-RU": [
                "ermil", "alena", "filipp", "madirus", "omazh",
                "zahar", "dasha", "julia", "lera", "marina",
                "alexander", "kirill", "anton"
            ],
            "en-US": [
                "john", "jane"
            ],
            "tr-TR": [
                "erkan", "zeynep"
            ]
        }


class MockTTS:
    """Mock TTS for testing and development."""

    async def synthesize(
        self,
        text: str,
        language: str = "ru-RU",
        **kwargs
    ) -> bytes:
        """Mock TTS - returns dummy audio data."""
        # Simulate processing time
        await asyncio.sleep(0.2)

        # Generate dummy PCM audio data (1 second of silence at 16kHz)
        sample_rate = 16000
        duration = 1.0
        samples = int(sample_rate * duration)

        # Create simple tone (sine wave)
        import math
        import struct

        frequency = 440  # A4 note
        audio_data = b""

        for i in range(samples):
            # Generate sine wave sample
            sample = int(32767 * math.sin(2 * math.pi * frequency * i / sample_rate))
            audio_data += struct.pack('<h', sample)

        return audio_data

    async def get_voices(self) -> Dict[str, Any]:
        """Mock voices list."""
        return {
            "ru-RU": ["mock-voice"],
            "en-US": ["mock-voice-en"],
        }


# Choose TTS implementation
if settings.is_prod or settings.yc_oauth_token:
    tts = YandexTTS()
else:
    print("Using mock TTS (no Yandex credentials)")
    tts = MockTTS()
