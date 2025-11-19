"""Immutable data models for the CW parser library.

This module defines all core data structures used throughout the pipeline.
All models are frozen dataclasses to ensure immutability.
"""

from dataclasses import dataclass
from enum import Enum

import numpy as np
import numpy.typing as npt


@dataclass(frozen=True)
class AudioSample:
    """A chunk of audio data with metadata.

    Attributes:
        data: Audio samples as a NumPy array
        sample_rate: Sample rate in Hz
        timestamp: Timestamp of the first sample in seconds
    """

    data: npt.NDArray[np.float32]
    sample_rate: int
    timestamp: float

    def __post_init__(self) -> None:
        """Validate the audio sample data."""
        if self.sample_rate <= 0:
            raise ValueError(f"Sample rate must be positive, got {self.sample_rate}")
        if self.timestamp < 0:
            raise ValueError(f"Timestamp must be non-negative, got {self.timestamp}")
        if len(self.data) == 0:
            raise ValueError("Audio data cannot be empty")

    @property
    def duration(self) -> float:
        """Duration of the audio chunk in seconds."""
        return len(self.data) / self.sample_rate

    @property
    def num_samples(self) -> int:
        """Number of samples in the audio chunk."""
        return len(self.data)


@dataclass(frozen=True)
class ToneEvent:
    """A detected tone on/off event.

    Attributes:
        is_tone_on: True if tone started, False if tone ended
        timestamp: Time of the event in seconds
        amplitude: Amplitude of the signal at the event
    """

    is_tone_on: bool
    timestamp: float
    amplitude: float

    def __post_init__(self) -> None:
        """Validate the tone event."""
        if self.timestamp < 0:
            raise ValueError(f"Timestamp must be non-negative, got {self.timestamp}")
        if self.amplitude < 0:
            raise ValueError(f"Amplitude must be non-negative, got {self.amplitude}")


class MorseElement(Enum):
    """Morse code elements."""

    DOT = "."
    DASH = "-"
    ELEMENT_GAP = " "  # Gap between dots/dashes within a character
    CHAR_GAP = "  "  # Gap between characters
    WORD_GAP = "   "  # Gap between words


@dataclass(frozen=True)
class MorseSymbol:
    """A decoded Morse symbol with timing information.

    Attributes:
        element: The Morse element (dot, dash, or gap)
        duration: Duration of the element in seconds
        timestamp: Start time of the element in seconds
    """

    element: MorseElement
    duration: float
    timestamp: float

    def __post_init__(self) -> None:
        """Validate the Morse symbol."""
        if self.duration < 0:
            raise ValueError(f"Duration must be non-negative, got {self.duration}")
        if self.timestamp < 0:
            raise ValueError(f"Timestamp must be non-negative, got {self.timestamp}")


@dataclass(frozen=True)
class DecodedCharacter:
    """A decoded character with confidence score.

    Attributes:
        char: The decoded character
        confidence: Confidence score (0.0 to 1.0)
        timestamp: Time when the character was decoded
        morse_pattern: The Morse pattern that was decoded (e.g., ".-" for 'A')
    """

    char: str
    confidence: float
    timestamp: float
    morse_pattern: str

    def __post_init__(self) -> None:
        """Validate the decoded character."""
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"Confidence must be in [0, 1], got {self.confidence}")
        if self.timestamp < 0:
            raise ValueError(f"Timestamp must be non-negative, got {self.timestamp}")
        # Allow single characters or prosigns (which start with '<')
        if len(self.char) != 1 and not self.char.startswith('<'):
            raise ValueError(f"Character must be a single character or prosign, got '{self.char}'")


@dataclass(frozen=True)
class TimingStats:
    """Timing statistics for Morse code decoding.

    Attributes:
        dot_duration: Average dot duration in seconds
        wpm: Words per minute (using PARIS standard)
        confidence: Confidence in the timing estimates (0.0 to 1.0)
        num_samples: Number of samples used to compute statistics
    """

    dot_duration: float
    wpm: float
    confidence: float
    num_samples: int

    def __post_init__(self) -> None:
        """Validate the timing statistics."""
        if self.dot_duration <= 0:
            raise ValueError(f"Dot duration must be positive, got {self.dot_duration}")
        if self.wpm <= 0:
            raise ValueError(f"WPM must be positive, got {self.wpm}")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"Confidence must be in [0, 1], got {self.confidence}")
        if self.num_samples < 0:
            raise ValueError(f"Number of samples must be non-negative, got {self.num_samples}")

    @classmethod
    def from_dot_duration(cls, dot_duration: float, num_samples: int = 0) -> "TimingStats":
        """Create TimingStats from dot duration using PARIS standard.

        Args:
            dot_duration: Dot duration in seconds
            num_samples: Number of samples used to compute the dot duration

        Returns:
            TimingStats instance with computed WPM
        """
        # PARIS standard: WPM = 1200 / dot_duration_ms
        wpm = 1200.0 / (dot_duration * 1000.0)
        # Confidence based on number of samples
        confidence = min(1.0, num_samples / 10.0) if num_samples > 0 else 0.0
        return cls(
            dot_duration=dot_duration,
            wpm=wpm,
            confidence=confidence,
            num_samples=num_samples,
        )


@dataclass(frozen=True)
class SignalStats:
    """Statistics about the detected signal.

    Attributes:
        frequency: Detected frequency in Hz
        snr_db: Signal-to-noise ratio in dB
        power: Signal power
        timestamp: Time of the measurement
    """

    frequency: float
    snr_db: float
    power: float
    timestamp: float

    def __post_init__(self) -> None:
        """Validate the signal statistics."""
        if self.frequency < 0:
            raise ValueError(f"Frequency must be non-negative, got {self.frequency}")
        if self.power < 0:
            raise ValueError(f"Power must be non-negative, got {self.power}")
        if self.timestamp < 0:
            raise ValueError(f"Timestamp must be non-negative, got {self.timestamp}")
