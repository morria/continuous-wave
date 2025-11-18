"""continuous-wave: Modern, testable CW (Morse code) decoder library.

This library provides a modular pipeline for decoding Morse code (CW) from audio streams.
It is designed for testability, maintainability, and extensibility.

Example:
    >>> from continuous_wave import CWConfig, AudioSample
    >>> config = CWConfig(sample_rate=8000, initial_wpm=20.0)
    >>> # Process audio samples through the CW decoder pipeline
"""

# Version information
__version__ = "0.1.0"
__author__ = "continuous-wave contributors"
__license__ = "MIT"

# Core configuration
from continuous_wave.config import CWConfig

# Data models
from continuous_wave.models import (
    AudioSample,
    DecodedCharacter,
    MorseElement,
    MorseSymbol,
    SignalStats,
    TimingStats,
    ToneEvent,
)

# Public API
__all__ = [
    # Version info
    "__version__",
    "__author__",
    "__license__",
    # Configuration
    "CWConfig",
    # Models
    "AudioSample",
    "ToneEvent",
    "MorseElement",
    "MorseSymbol",
    "DecodedCharacter",
    "TimingStats",
    "SignalStats",
]
