"""WAV file audio input source."""

import wave
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
from numpy.typing import NDArray
from scipy import signal as sp_signal

from continuous_wave.config import CWConfig
from continuous_wave.models import AudioSample
from continuous_wave.protocols import AudioSource


@dataclass
class WavFileSource(AudioSource):
    """Audio source that reads from a WAV file.

    Supports resampling if file sample rate doesn't match config.
    """

    config: CWConfig
    file_path: Path
    _wav_file: wave.Wave_read | None = field(default=None, init=False)
    _file_sample_rate: int = field(default=0, init=False)
    _num_channels: int = field(default=0, init=False)
    _sample_width: int = field(default=0, init=False)
    _is_open: bool = field(default=False, init=False)
    _current_timestamp: float = field(default=0.0, init=False)

    def __post_init__(self) -> None:
        """Open and validate WAV file."""
        self._open_file()

    def _open_file(self) -> None:
        """Open WAV file and read parameters."""
        if not self.file_path.exists():
            raise FileNotFoundError(f"WAV file not found: {self.file_path}")

        # Open file and keep it open for streaming (closed in close() method)
        self._wav_file = wave.open(str(self.file_path), "rb")  # noqa: SIM115
        self._file_sample_rate = self._wav_file.getframerate()
        self._num_channels = self._wav_file.getnchannels()
        self._sample_width = self._wav_file.getsampwidth()
        self._is_open = True

        # Validate file parameters
        if self._sample_width not in (1, 2, 4):
            raise ValueError(
                f"Unsupported sample width: {self._sample_width} bytes. "
                f"Supported: 1, 2, or 4 bytes."
            )

    async def read(self) -> AudioSample | None:
        """Read one chunk of audio from WAV file.

        Returns:
            AudioSample with audio data, or None if end of file
        """
        if not self._is_open or self._wav_file is None:
            return None

        # Read chunk of frames
        frames = self._wav_file.readframes(self.config.chunk_size)

        if len(frames) == 0:
            # End of file
            return None

        # Convert bytes to numpy array
        audio_data = self._bytes_to_float(frames)

        # Convert to mono if stereo
        if self._num_channels > 1:
            audio_data = audio_data[:: self._num_channels]

        # Resample if needed
        if self._file_sample_rate != self.config.sample_rate:
            audio_data = self._resample(audio_data)

        # Convert to float32 for AudioSample
        audio_data_float32 = audio_data.astype(np.float32)

        # Update timestamp based on samples read
        sample = AudioSample(
            data=audio_data_float32,
            sample_rate=self.config.sample_rate,
            timestamp=self._current_timestamp,
        )

        # Increment timestamp
        duration = len(audio_data) / self.config.sample_rate
        self._current_timestamp += duration

        return sample

    def __aiter__(self) -> AsyncIterator[AudioSample]:
        """Async iterator over audio samples.

        Returns:
            Self as async iterator
        """
        return self

    async def __anext__(self) -> AudioSample:
        """Get next audio sample.

        Returns:
            Next AudioSample from the file

        Raises:
            StopAsyncIteration: When end of file is reached
        """
        sample = await self.read()
        if sample is None:
            raise StopAsyncIteration
        return sample

    def _bytes_to_float(self, frames: bytes) -> NDArray[np.float64]:
        """Convert raw audio bytes to float64 array.

        Args:
            frames: Raw audio bytes from WAV file

        Returns:
            Normalized float64 array in range [-1.0, 1.0]
        """
        # Determine dtype based on sample width
        if self._sample_width == 1:
            # 8-bit unsigned
            audio = np.frombuffer(frames, dtype=np.uint8).astype(np.float64)
            audio = (audio - 128.0) / 128.0  # Convert to signed, normalize
        elif self._sample_width == 2:
            # 16-bit signed
            audio = np.frombuffer(frames, dtype=np.int16).astype(np.float64)
            audio = audio / 32768.0  # Normalize
        elif self._sample_width == 4:
            # 32-bit signed
            audio = np.frombuffer(frames, dtype=np.int32).astype(np.float64)
            audio = audio / 2147483648.0  # Normalize
        else:
            raise ValueError(f"Unsupported sample width: {self._sample_width}")

        return audio

    def _resample(self, audio: NDArray[np.float64]) -> NDArray[np.float64]:
        """Resample audio to target sample rate.

        Args:
            audio: Input audio at file sample rate

        Returns:
            Resampled audio at config sample rate
        """
        # Calculate number of output samples
        num_samples = int(len(audio) * self.config.sample_rate / self._file_sample_rate)

        # Use scipy's resample for high-quality resampling
        resampled = sp_signal.resample(audio, num_samples)

        return resampled

    def close(self) -> None:
        """Close the WAV file."""
        if self._wav_file is not None:
            self._wav_file.close()
            self._wav_file = None
        self._is_open = False

    def __del__(self) -> None:
        """Cleanup on deletion."""
        self.close()
