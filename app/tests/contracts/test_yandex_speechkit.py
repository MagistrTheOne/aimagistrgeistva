"""Contract tests for Yandex SpeechKit services."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from app.services.voice.stt import YandexSTT
from app.services.voice.tts import YandexTTS


@pytest.mark.contract
class TestYandexSTTContract:
    """Contract tests for Yandex STT."""

    @pytest.fixture
    def stt_service(self):
        """Create STT service instance."""
        return YandexSTT()

    @pytest.mark.skipif(
        not pytest.env.get("YANDEX_OAUTH_TOKEN"),
        reason="Yandex credentials not available"
    )
    def test_stt_transcribe_real_audio(self, stt_service):
        """Test STT with real Yandex API."""
        # Generate test audio (1 second silence)
        sample_rate = 16000
        duration = 1.0
        samples = int(sample_rate * duration)

        # Create simple audio data (silence)
        import struct
        audio_data = b""
        for _ in range(samples):
            # 16-bit PCM silence
            audio_data += struct.pack('<h', 0)

        result = stt_service.transcribe(audio_data)

        # Verify response structure
        assert "text" in result
        assert "confidence" in result
        assert "alternatives" in result
        assert isinstance(result["alternatives"], list)

        # For silence, text should be empty or very short
        assert len(result["text"]) < 100

    def test_stt_transcribe_mock(self, stt_service, monkeypatch):
        """Test STT with mocked responses."""
        mock_response = {
            "result": {
                "alternatives": [
                    {
                        "text": "тестовый текст",
                        "confidence": 0.95
                    }
                ]
            }
        }

        # Mock HTTP client
        mock_post = AsyncMock(return_value=mock_response)
        monkeypatch.setattr(stt_service._http_client, "post", mock_post)

        # Test audio data
        audio_data = b"test_audio_data"
        result = stt_service.transcribe(audio_data)

        assert result["text"] == "тестовый текст"
        assert result["confidence"] == 0.95
        assert len(result["alternatives"]) == 1

        # Verify HTTP call was made
        mock_post.assert_called_once()


@pytest.mark.contract
class TestYandexTTSContract:
    """Contract tests for Yandex TTS."""

    @pytest.fixture
    def tts_service(self):
        """Create TTS service instance."""
        return YandexTTS()

    @pytest.mark.skipif(
        not pytest.env.get("YANDEX_OAUTH_TOKEN"),
        reason="Yandex credentials not available"
    )
    def test_tts_synthesize_real(self, tts_service):
        """Test TTS with real Yandex API."""
        text = "Привет, мир!"
        audio_data = tts_service.synthesize(text)

        # Verify audio data
        assert isinstance(audio_data, bytes)
        assert len(audio_data) > 0

        # Basic audio format check (should be PCM or other format)
        # For PCM, length should be reasonable for 1-2 second audio
        assert len(audio_data) > 1000

    def test_tts_synthesize_mock(self, tts_service, monkeypatch):
        """Test TTS with mocked responses."""
        mock_audio = b"mock_audio_data_12345"

        # Mock HTTP client to return raw audio
        mock_post = AsyncMock(return_value=mock_audio)
        monkeypatch.setattr(tts_service._http_client, "post", mock_post)

        text = "Тестовый текст"
        result = tts_service.synthesize(text)

        assert result == mock_audio

        # Verify HTTP call was made with correct parameters
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert call_args[1]["data"]["text"] == text
        assert "voice" in call_args[1]["data"]
