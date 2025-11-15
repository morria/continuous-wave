"""Protocol definitions for dependency injection and testing.

This module defines protocol interfaces that enable duck typing and testability.
All components accept dependencies via these protocols.
"""

from collections.abc import AsyncIterator, Iterator
from typing import Any, Protocol

import numpy.typing as npt

from continuous_wave.models import (
    AudioSample,
    DecodedCharacter,
    MorseSymbol,
    SignalStats,
    TimingStats,
    ToneEvent,
)


class AudioSource(Protocol):
    """Protocol for audio input sources.

    Audio sources provide a stream of audio samples. Implementations include:
    - SoundcardSource: Reads from system audio input
    - FileSource: Reads from WAV files
    - SyntheticSource: Generates test signals
    """

    async def read(self, chunk_size: int) -> AsyncIterator[AudioSample]:
        """Read audio samples in chunks.

        Args:
            chunk_size: Number of samples per chunk

        Yields:
            AudioSample instances with the specified chunk size
        """
        ...

    async def close(self) -> None:
        """Close the audio source and release resources."""
        ...


class SignalProcessor(Protocol):
    """Protocol for signal processing components.

    Signal processors transform audio samples (e.g., filtering, AGC).
    """

    def process(self, audio: AudioSample) -> AudioSample:
        """Process an audio sample.

        Args:
            audio: Input audio sample

        Returns:
            Processed audio sample
        """
        ...

    def reset(self) -> None:
        """Reset the processor state."""
        ...


class FrequencyDetector(Protocol):
    """Protocol for frequency detection.

    Frequency detectors identify the CW signal frequency in the audio spectrum.
    """

    def detect(self, audio: AudioSample) -> SignalStats | None:
        """Detect the signal frequency in the audio.

        Args:
            audio: Audio sample to analyze

        Returns:
            SignalStats if a signal is detected, None otherwise
        """
        ...

    @property
    def is_locked(self) -> bool:
        """Check if the detector has locked onto a stable frequency.

        Returns:
            True if frequency is locked, False otherwise
        """
        ...

    def reset(self) -> None:
        """Reset the detector state."""
        ...


class ToneDetector(Protocol):
    """Protocol for tone detection.

    Tone detectors identify tone on/off transitions in the audio signal.
    """

    def detect(self, audio: AudioSample) -> Iterator[ToneEvent]:
        """Detect tone events in the audio sample.

        Args:
            audio: Audio sample to analyze

        Yields:
            ToneEvent instances for detected tone transitions
        """
        ...

    def reset(self) -> None:
        """Reset the detector state."""
        ...


class TimingAnalyzer(Protocol):
    """Protocol for timing analysis.

    Timing analyzers convert tone events to Morse symbols and estimate timing.
    """

    def analyze(self, events: Iterator[ToneEvent]) -> Iterator[MorseSymbol]:
        """Analyze tone events and produce Morse symbols.

        Args:
            events: Iterator of tone events

        Yields:
            MorseSymbol instances
        """
        ...

    @property
    def timing_stats(self) -> TimingStats | None:
        """Get current timing statistics.

        Returns:
            TimingStats if available, None otherwise
        """
        ...

    @property
    def is_locked(self) -> bool:
        """Check if timing analysis has locked onto stable timing.

        Returns:
            True if timing is locked, False otherwise
        """
        ...

    def reset(self) -> None:
        """Reset the analyzer state."""
        ...


class Decoder(Protocol):
    """Protocol for Morse code decoding.

    Decoders convert Morse symbols to text characters.
    """

    def decode(self, symbols: Iterator[MorseSymbol]) -> Iterator[DecodedCharacter]:
        """Decode Morse symbols to characters.

        Args:
            symbols: Iterator of Morse symbols

        Yields:
            DecodedCharacter instances
        """
        ...

    def reset(self) -> None:
        """Reset the decoder state."""
        ...


class Filter(Protocol):
    """Protocol for digital filters.

    Filters process audio data to remove noise or isolate frequencies.
    """

    def filter(self, data: npt.NDArray[Any]) -> npt.NDArray[Any]:
        """Filter the input data.

        Args:
            data: Input data array

        Returns:
            Filtered data array
        """
        ...

    def reset(self) -> None:
        """Reset the filter state."""
        ...
