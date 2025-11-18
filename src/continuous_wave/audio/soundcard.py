"""Soundcard audio input source."""

import asyncio
import time
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import numpy as np
from numpy.typing import NDArray

from continuous_wave.config import CWConfig
from continuous_wave.models import AudioSample
from continuous_wave.protocols import AudioSource

if TYPE_CHECKING:
    pass


@dataclass
class SoundcardSource(AudioSource):
    """Audio source that reads from soundcard input.

    Uses sounddevice library to capture audio from the default
    input device or a specified device.
    """

    config: CWConfig
    device: int | str | None = None
    _stream: Any | None = field(default=None, init=False)
    _queue: asyncio.Queue[NDArray[np.float64]] = field(default=None, init=False)
    _is_running: bool = field(default=False, init=False)

    def __post_init__(self) -> None:
        """Initialize audio queue."""
        self._queue = asyncio.Queue(maxsize=10)

    async def read(self) -> AudioSample:
        """Read one chunk of audio from soundcard.

        Returns:
            AudioSample with audio data and metadata
        """
        if not self._is_running:
            self._start_stream()

        # Wait for audio data from callback
        audio_data = await self._queue.get()

        return AudioSample(
            data=audio_data,
            sample_rate=self.config.sample_rate,
            timestamp=time.time(),
        )

    async def __aiter__(self) -> AsyncIterator[AudioSample]:
        """Async iterator over audio samples.

        Yields:
            AudioSample objects continuously
        """
        if not self._is_running:
            self._start_stream()

        while self._is_running:
            try:
                sample = await self.read()
                yield sample
            except asyncio.CancelledError:
                break

    def _start_stream(self) -> None:
        """Start the audio input stream."""
        if self._is_running:
            return

        # Import sounddevice here to avoid import errors when not needed
        try:
            import sounddevice as sd
        except (ImportError, OSError) as e:
            raise RuntimeError(
                "sounddevice library not available. "
                "Please install PortAudio system library (libportaudio2) "
                f"and sounddevice Python package. Error: {e}"
            ) from e

        def audio_callback(
            indata: NDArray[np.float64],
            _frames: int,
            _time_info: dict,
            status: Any,
        ) -> None:
            """Callback for audio input.

            Called by sounddevice when audio data is available.
            """
            if status:
                # Log any issues (overflows, etc.)
                pass

            # Convert to mono if stereo
            audio = indata[:, 0].copy() if len(indata.shape) > 1 else indata.copy()

            # Put in queue (non-blocking)
            from contextlib import suppress

            with suppress(asyncio.QueueFull):
                self._queue.put_nowait(audio)

        # Create and start stream
        self._stream = sd.InputStream(
            device=self.device,
            channels=1,
            samplerate=self.config.sample_rate,
            blocksize=self.config.chunk_size,
            dtype=np.float64,
            callback=audio_callback,
        )
        self._stream.start()
        self._is_running = True

    def stop(self) -> None:
        """Stop the audio input stream."""
        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
            self._stream = None
        self._is_running = False

    def __del__(self) -> None:
        """Cleanup on deletion."""
        self.stop()
