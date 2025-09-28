"""Hotword detection using Porcupine."""

import struct
from typing import Callable, Optional

import pvporcupine

from app.core.config import settings
from app.core.errors import VoiceProcessingError


class HotwordDetector:
    """Hotword detection using Picovoice Porcupine."""

    def __init__(
        self,
        hotword: str = "Мага",
        sensitivity: float = 0.5,
        access_key: Optional[str] = None
    ):
        """
        Initialize hotword detector.

        Args:
            hotword: Hotword to detect (currently supports built-in words)
            sensitivity: Detection sensitivity (0.0-1.0)
            access_key: Picovoice access key (required for non-built-in words)
        """
        self.hotword = hotword
        self.sensitivity = sensitivity
        self.access_key = access_key or ""  # Empty for built-in keywords

        # Porcupine configuration
        self.sample_rate = 16000
        self.frame_length = 512  # Porcupine frame length

        self.porcupine: Optional[pvporcupine.Porcupine] = None
        self._initialize_porcupine()

    def _initialize_porcupine(self):
        """Initialize Porcupine engine."""
        try:
            # Map Russian hotwords to built-in keywords
            keyword_map = {
                "Мага": "bumblebee",  # Using English keyword as approximation
                "Маша": "bumblebee",
                "Маруся": "bumblebee",
                "Алиса": "bumblebee",
                "Сбер": "bumblebee",
                # Add more mappings as needed
            }

            keyword = keyword_map.get(self.hotword, self.hotword)

            # Try built-in keyword first
            try:
                self.porcupine = pvporcupine.create(
                    keywords=[keyword],
                    sensitivities=[self.sensitivity]
                )
            except pvporcupine.PorcupineInvalidArgumentError:
                # If built-in keyword not found, try custom keyword
                if not self.access_key:
                    raise VoiceProcessingError(
                        f"Hotword '{self.hotword}' requires Picovoice access key for custom keywords"
                    )

                # For custom keywords, would need keyword file
                # This is a simplified implementation
                raise VoiceProcessingError(
                    f"Custom hotword '{self.hotword}' not supported. Use built-in keywords."
                )

        except Exception as e:
            raise VoiceProcessingError(f"Failed to initialize Porcupine: {e}")

    def process_audio(self, audio_data: bytes) -> bool:
        """
        Process audio frame for hotword detection.

        Args:
            audio_data: Raw PCM audio data (16-bit, 16kHz)

        Returns:
            True if hotword detected, False otherwise
        """
        if not self.porcupine:
            raise VoiceProcessingError("Porcupine not initialized")

        # Convert bytes to int16 array
        if len(audio_data) != self.frame_length * 2:  # 2 bytes per sample
            raise VoiceProcessingError(
                f"Invalid audio frame size {len(audio_data)}. Expected {self.frame_length * 2} bytes"
            )

        # Unpack audio data
        audio_frame = struct.unpack_from("h" * self.frame_length, audio_data)

        try:
            # Process frame
            keyword_index = self.porcupine.process(audio_frame)

            # Return True if hotword detected (keyword_index >= 0)
            return keyword_index >= 0

        except Exception as e:
            raise VoiceProcessingError(f"Hotword detection failed: {e}")

    def __del__(self):
        """Cleanup Porcupine resources."""
        if self.porcupine:
            self.porcupine.delete()


class SimpleHotwordDetector:
    """Simple hotword detector using pattern matching (fallback)."""

    def __init__(self, hotword: str = "Мага", sensitivity: float = 0.5):
        self.hotword = hotword.lower()
        self.sensitivity = sensitivity
        self.sample_rate = 16000

        # Simple energy threshold for basic VAD
        self.energy_threshold = 500

    def _calculate_energy(self, audio_data: bytes) -> float:
        """Calculate audio energy."""
        # Convert to 16-bit samples
        samples = []
        for i in range(0, len(audio_data), 2):
            if i + 1 < len(audio_data):
                sample = struct.unpack('<h', audio_data[i:i+2])[0]
                samples.append(abs(sample))

        if not samples:
            return 0.0

        return sum(samples) / len(samples)

    def _simple_speech_detection(self, audio_data: bytes) -> bool:
        """Simple speech detection based on energy."""
        energy = self._calculate_energy(audio_data)
        return energy > self.energy_threshold

    def process_audio(self, audio_data: bytes) -> bool:
        """
        Simple hotword detection (always returns False - just a placeholder).

        In a real implementation, this would use:
        - FFT for frequency analysis
        - Pattern matching algorithms
        - Machine learning models

        For now, it only does basic speech detection.
        """
        return self._simple_speech_detection(audio_data)


# Choose detector based on availability
try:
    # Try to use Porcupine
    hotword_detector = HotwordDetector(
        hotword=settings.hotword,
        sensitivity=0.5
    )
except Exception as e:
    print(f"Porcupine not available: {e}. Using simple detector.")
    # Fallback to simple detector
    hotword_detector = SimpleHotwordDetector(hotword=settings.hotword)
