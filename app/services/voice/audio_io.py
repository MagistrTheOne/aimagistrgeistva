"""Audio I/O abstraction layer."""

import asyncio
import platform
import queue
import threading
import time
from typing import Any, Callable, Optional

import numpy as np
import pyaudio

from app.core.config import settings
from app.core.errors import VoiceProcessingError


class AudioDevice:
    """Audio device information."""

    def __init__(self, index: int, name: str, max_input_channels: int, max_output_channels: int):
        self.index = index
        self.name = name
        self.max_input_channels = max_input_channels
        self.max_output_channels = max_output_channels

    @property
    def is_input_device(self) -> bool:
        """Check if device supports input."""
        return self.max_input_channels > 0

    @property
    def is_output_device(self) -> bool:
        """Check if device supports output."""
        return self.max_output_channels > 0

    def __str__(self) -> str:
        return f"AudioDevice(index={self.index}, name='{self.name}', in={self.max_input_channels}, out={self.max_output_channels})"


class AudioConfig:
    """Audio configuration."""

    def __init__(
        self,
        sample_rate: int = 16000,
        channels: int = 1,
        format_type: int = pyaudio.paInt16,
        chunk_size: int = 1024,
        buffer_size: int = 4096,
    ):
        self.sample_rate = sample_rate
        self.channels = channels
        self.format_type = format_type
        self.chunk_size = chunk_size
        self.buffer_size = buffer_size

    @property
    def sample_width(self) -> int:
        """Get sample width in bytes."""
        if self.format_type == pyaudio.paInt16:
            return 2
        elif self.format_type == pyaudio.paInt32:
            return 4
        elif self.format_type == pyaudio.paFloat32:
            return 4
        else:
            return 2  # default

    @property
    def dtype(self) -> np.dtype:
        """Get numpy dtype for audio format."""
        if self.format_type == pyaudio.paInt16:
            return np.int16
        elif self.format_type == pyaudio.paInt32:
            return np.int32
        elif self.format_type == pyaudio.paFloat32:
            return np.float32
        else:
            return np.int16


class AudioIO:
    """Audio I/O abstraction layer."""

    def __init__(self, config: Optional[AudioConfig] = None):
        self.config = config or AudioConfig()
        self._pyaudio: Optional[pyaudio.PyAudio] = None
        self._input_stream: Optional[pyaudio.Stream] = None
        self._output_stream: Optional[pyaudio.Stream] = None
        self._input_thread: Optional[threading.Thread] = None
        self._output_thread: Optional[threading.Thread] = None
        self._running = False
        self._input_queue: queue.Queue = queue.Queue()
        self._output_queue: queue.Queue = queue.Queue()

        # Device indices
        self._input_device_index: Optional[int] = None
        self._output_device_index: Optional[int] = None

        # Callbacks
        self._audio_callback: Optional[Callable[[bytes], None]] = None

    def initialize(self):
        """Initialize PyAudio."""
        try:
            self._pyaudio = pyaudio.PyAudio()
        except Exception as e:
            raise VoiceProcessingError(f"Failed to initialize PyAudio: {e}")

    def terminate(self):
        """Terminate PyAudio."""
        self.stop_streams()

        if self._pyaudio:
            self._pyaudio.terminate()
            self._pyaudio = None

    def get_devices(self) -> list[AudioDevice]:
        """Get list of available audio devices."""
        if not self._pyaudio:
            raise VoiceProcessingError("PyAudio not initialized")

        devices = []
        for i in range(self._pyaudio.get_device_count()):
            try:
                info = self._pyaudio.get_device_info_by_index(i)
                device = AudioDevice(
                    index=i,
                    name=info.get('name', f'Device {i}'),
                    max_input_channels=int(info.get('maxInputChannels', 0)),
                    max_output_channels=int(info.get('maxOutputChannels', 0)),
                )
                devices.append(device)
            except Exception:
                continue  # Skip invalid devices

        return devices

    def set_input_device(self, device_name: Optional[str] = None):
        """Set input device by name or use default."""
        devices = self.get_devices()
        input_devices = [d for d in devices if d.is_input_device]

        if not input_devices:
            raise VoiceProcessingError("No input devices available")

        if device_name:
            device = next((d for d in input_devices if device_name.lower() in d.name.lower()), None)
            if not device:
                available = [d.name for d in input_devices]
                raise VoiceProcessingError(f"Input device '{device_name}' not found. Available: {available}")
        else:
            # Use default device
            device = input_devices[0]

        self._input_device_index = device.index

    def set_output_device(self, device_name: Optional[str] = None):
        """Set output device by name or use default."""
        devices = self.get_devices()
        output_devices = [d for d in devices if d.is_output_device]

        if not output_devices:
            raise VoiceProcessingError("No output devices available")

        if device_name:
            device = next((d for d in output_devices if device_name.lower() in d.name.lower()), None)
            if not device:
                available = [d.name for d in output_devices]
                raise VoiceProcessingError(f"Output device '{device_name}' not found. Available: {available}")
        else:
            # Use default device
            device = output_devices[0]

        self._output_device_index = device.index

    def set_audio_callback(self, callback: Callable[[bytes], None]):
        """Set callback for audio data."""
        self._audio_callback = callback

    def _input_callback(self, in_data, frame_count, time_info, status):
        """PyAudio input callback."""
        if self._running and in_data:
            # Put data in queue for async processing
            try:
                self._input_queue.put_nowait(in_data)
            except queue.Full:
                pass  # Drop old data if queue is full

            # Call user callback if set
            if self._audio_callback:
                try:
                    self._audio_callback(in_data)
                except Exception:
                    pass  # Don't let callback errors break audio

        return (in_data, pyaudio.paContinue)

    def _output_callback(self, in_data, frame_count, time_info, status):
        """PyAudio output callback."""
        try:
            # Get data from output queue
            data = self._output_queue.get_nowait()
            return (data, pyaudio.paContinue)
        except queue.Empty:
            # Return silence if no data
            silence = b'\x00' * (frame_count * self.config.channels * self.config.sample_width)
            return (silence, pyaudio.paContinue)

    def start_input_stream(self):
        """Start audio input stream."""
        if not self._pyaudio:
            raise VoiceProcessingError("PyAudio not initialized")

        if self._input_stream:
            return  # Already started

        try:
            self._input_stream = self._pyaudio.open(
                format=self.config.format_type,
                channels=self.config.channels,
                rate=self.config.sample_rate,
                input=True,
                input_device_index=self._input_device_index,
                frames_per_buffer=self.config.chunk_size,
                stream_callback=self._input_callback,
            )
            self._input_stream.start_stream()
        except Exception as e:
            raise VoiceProcessingError(f"Failed to start input stream: {e}")

    def start_output_stream(self):
        """Start audio output stream."""
        if not self._pyaudio:
            raise VoiceProcessingError("PyAudio not initialized")

        if self._output_stream:
            return  # Already started

        try:
            self._output_stream = self._pyaudio.open(
                format=self.config.format_type,
                channels=self.config.channels,
                rate=self.config.sample_rate,
                output=True,
                output_device_index=self._output_device_index,
                frames_per_buffer=self.config.chunk_size,
                stream_callback=self._output_callback,
            )
            self._output_stream.start_stream()
        except Exception as e:
            raise VoiceProcessingError(f"Failed to start output stream: {e}")

    def stop_streams(self):
        """Stop all audio streams."""
        if self._input_stream:
            try:
                self._input_stream.stop_stream()
                self._input_stream.close()
            except Exception:
                pass
            self._input_stream = None

        if self._output_stream:
            try:
                self._output_stream.stop_stream()
                self._output_stream.close()
            except Exception:
                pass
            self._output_stream = None

    async def read_audio_chunk(self, timeout: float = 0.1) -> Optional[bytes]:
        """Read audio chunk asynchronously."""
        try:
            # Convert async to sync call
            loop = asyncio.get_event_loop()
            chunk = await loop.run_in_executor(None, self._input_queue.get, timeout)
            return chunk
        except queue.Empty:
            return None

    def write_audio_chunk(self, data: bytes):
        """Write audio chunk to output queue."""
        try:
            self._output_queue.put_nowait(data)
        except queue.Full:
            pass  # Drop data if queue is full

    async def play_audio(self, audio_data: bytes, sample_rate: Optional[int] = None):
        """Play audio data."""
        if not self._output_stream:
            raise VoiceProcessingError("Output stream not started")

        # Resample if necessary
        if sample_rate and sample_rate != self.config.sample_rate:
            audio_data = self._resample_audio(audio_data, sample_rate, self.config.sample_rate)

        # Write to output queue
        self.write_audio_chunk(audio_data)

    def _resample_audio(self, data: bytes, from_rate: int, to_rate: int) -> bytes:
        """Simple audio resampling (basic implementation)."""
        # Convert bytes to numpy array
        audio_array = np.frombuffer(data, dtype=self.config.dtype)

        # Calculate resampling ratio
        ratio = to_rate / from_rate

        # Simple linear interpolation (not high quality but works)
        import scipy.signal
        resampled = scipy.signal.resample(audio_array, int(len(audio_array) * ratio))

        # Convert back to bytes
        return resampled.astype(self.config.dtype).tobytes()

    def is_input_active(self) -> bool:
        """Check if input stream is active."""
        return self._input_stream is not None and self._input_stream.is_active()

    def is_output_active(self) -> bool:
        """Check if output stream is active."""
        return self._output_stream is not None and self._output_stream.is_active()

    @property
    def input_device_name(self) -> Optional[str]:
        """Get current input device name."""
        if self._input_device_index is not None and self._pyaudio:
            try:
                info = self._pyaudio.get_device_info_by_index(self._input_device_index)
                return info.get('name')
            except Exception:
                pass
        return None

    @property
    def output_device_name(self) -> Optional[str]:
        """Get current output device name."""
        if self._output_device_index is not None and self._pyaudio:
            try:
                info = self._pyaudio.get_device_info_by_index(self._output_device_index)
                return info.get('name')
            except Exception:
                pass
        return None


# Global audio I/O instance
audio_io = AudioIO()
