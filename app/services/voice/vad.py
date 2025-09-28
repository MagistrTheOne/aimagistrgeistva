"""Voice Activity Detection (VAD) using WebRTC VAD."""

import webrtcvad
from typing import List, Optional

import numpy as np

from app.core.errors import VoiceProcessingError


class VoiceActivityDetector:
    """Voice Activity Detection using WebRTC VAD."""

    def __init__(self, mode: int = 3):
        """
        Initialize VAD.

        Args:
            mode: Aggressiveness mode (0-3), higher = more aggressive
        """
        self.mode = mode
        self.vad = webrtcvad.Vad(mode)

        # VAD works with 16-bit PCM at specific sample rates
        self.valid_sample_rates = [8000, 16000, 32000, 48000]
        self.frame_duration_ms = 30  # WebRTC VAD requires 10, 20, or 30ms frames
        self.frame_size = 480  # 30ms at 16kHz = 480 samples

    def is_speech(self, audio_data: bytes, sample_rate: int = 16000) -> bool:
        """
        Check if audio frame contains speech.

        Args:
            audio_data: Raw PCM audio data (16-bit)
            sample_rate: Sample rate of audio

        Returns:
            True if speech detected, False otherwise
        """
        if sample_rate not in self.valid_sample_rates:
            raise VoiceProcessingError(f"Invalid sample rate {sample_rate}. Valid: {self.valid_sample_rates}")

        if len(audio_data) != self.frame_size * 2:  # 2 bytes per sample
            raise VoiceProcessingError(f"Invalid frame size {len(audio_data)}. Expected {self.frame_size * 2} bytes")

        try:
            return self.vad.is_speech(audio_data, sample_rate)
        except Exception as e:
            raise VoiceProcessingError(f"VAD processing failed: {e}")

    def detect_speech_segments(
        self,
        audio_data: bytes,
        sample_rate: int = 16000,
        min_speech_duration: float = 0.3,
        min_silence_duration: float = 0.5,
    ) -> List[tuple[int, int]]:
        """
        Detect speech segments in audio data.

        Args:
            audio_data: Raw PCM audio data
            sample_rate: Sample rate
            min_speech_duration: Minimum speech segment duration in seconds
            min_silence_duration: Minimum silence between segments in seconds

        Returns:
            List of (start_sample, end_sample) tuples for speech segments
        """
        if sample_rate not in self.valid_sample_rates:
            sample_rate = 16000  # Default fallback

        # Convert to numpy array
        audio_array = np.frombuffer(audio_data, dtype=np.int16)
        total_samples = len(audio_array)

        # Frame size in samples
        frame_samples = int(sample_rate * self.frame_duration_ms / 1000)
        frame_bytes = frame_samples * 2  # 16-bit = 2 bytes

        segments = []
        current_segment_start = None
        silence_counter = 0

        min_speech_frames = int(min_speech_duration * 1000 / self.frame_duration_ms)
        min_silence_frames = int(min_silence_duration * 1000 / self.frame_duration_ms)

        speech_frames = 0

        for i in range(0, total_samples - frame_samples + 1, frame_samples):
            frame_data = audio_array[i:i + frame_samples].tobytes()

            if len(frame_data) != frame_bytes:
                continue  # Skip incomplete frames

            try:
                is_speech = self.vad.is_speech(frame_data, sample_rate)

                if is_speech:
                    if current_segment_start is None:
                        current_segment_start = i
                        speech_frames = 1
                    else:
                        speech_frames += 1
                    silence_counter = 0
                else:
                    silence_counter += 1

                    # End segment if enough silence
                    if (current_segment_start is not None and
                        silence_counter >= min_silence_frames and
                        speech_frames >= min_speech_frames):

                        segment_end = i
                        segments.append((current_segment_start, segment_end))
                        current_segment_start = None
                        speech_frames = 0

            except Exception:
                continue  # Skip problematic frames

        # Handle final segment
        if (current_segment_start is not None and
            speech_frames >= min_speech_frames):
            segments.append((current_segment_start, total_samples))

        return segments

    def get_speech_audio(
        self,
        audio_data: bytes,
        sample_rate: int = 16000,
        **kwargs
    ) -> bytes:
        """
        Extract speech portions from audio data.

        Returns:
            Audio data containing only speech segments
        """
        segments = self.detect_speech_segments(audio_data, sample_rate, **kwargs)

        if not segments:
            return b''

        audio_array = np.frombuffer(audio_data, dtype=np.int16)
        speech_audio = []

        for start, end in segments:
            speech_audio.append(audio_array[start:end])

        if speech_audio:
            return np.concatenate(speech_audio).tobytes()

        return b''

    def calculate_speech_ratio(
        self,
        audio_data: bytes,
        sample_rate: int = 16000
    ) -> float:
        """
        Calculate ratio of speech to total audio duration.

        Returns:
            Speech ratio (0.0 to 1.0)
        """
        segments = self.detect_speech_segments(audio_data, sample_rate)

        if not segments:
            return 0.0

        total_samples = len(np.frombuffer(audio_data, dtype=np.int16))
        speech_samples = sum(end - start for start, end in segments)

        return speech_samples / total_samples if total_samples > 0 else 0.0


class AdaptiveVAD:
    """Adaptive VAD that adjusts sensitivity based on environment."""

    def __init__(self):
        self.vad_conservative = VoiceActivityDetector(mode=0)  # Less aggressive
        self.vad_aggressive = VoiceActivityDetector(mode=3)    # More aggressive
        self.current_mode = 1  # Start with moderate

    def is_speech(self, audio_data: bytes, sample_rate: int = 16000) -> bool:
        """Adaptive speech detection."""
        # Use conservative VAD first
        if self.vad_conservative.is_speech(audio_data, sample_rate):
            return True

        # If in aggressive mode, also check aggressive VAD
        if self.current_mode >= 2:
            return self.vad_aggressive.is_speech(audio_data, sample_rate)

        return False

    def adjust_sensitivity(self, false_positives: int, false_negatives: int):
        """Adjust VAD sensitivity based on detection accuracy."""
        if false_positives > false_negatives:
            # Too many false positives, make more conservative
            self.current_mode = max(0, self.current_mode - 1)
        elif false_negatives > false_positives:
            # Too many false negatives, make more aggressive
            self.current_mode = min(3, self.current_mode + 1)


# Global VAD instances
vad = VoiceActivityDetector()
adaptive_vad = AdaptiveVAD()
