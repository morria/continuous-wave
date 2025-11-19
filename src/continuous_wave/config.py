"""Configuration classes for the CW parser library.

This module provides centralized configuration with sensible defaults.
"""

from dataclasses import dataclass


@dataclass
class CWConfig:
    """Configuration for the CW parser pipeline.

    All parameters have sensible defaults based on the design document.

    Attributes:
        sample_rate: Audio sample rate in Hz (default: 8000)
        chunk_size: Number of samples per processing chunk (default: 256)
        freq_range: Tuple of (min_freq, max_freq) in Hz for CW detection
        min_snr_db: Minimum signal-to-noise ratio in dB for detection
        filter_bandwidth: Bandpass filter bandwidth in Hz
        agc_target: Target output level for AGC (0.0 to 1.0)
        agc_attack_ms: AGC attack time in milliseconds
        agc_release_ms: AGC release time in milliseconds
        squelch_threshold: Squelch threshold (0.0 to 1.0)
        squelch_hysteresis: Squelch hysteresis (0.0 to 1.0)
        tone_threshold: Tone detection threshold (0.0 to 1.0)
        initial_wpm: Initial WPM estimate for decoding
        min_wpm: Minimum WPM for detection
        max_wpm: Maximum WPM for detection
        adaptive_timing: Enable adaptive WPM detection
    """

    # Audio settings
    sample_rate: int = 8000
    chunk_size: int = 256

    # Frequency detection
    freq_range: tuple[float, float] = (200.0, 1200.0)
    min_snr_db: float = 6.0

    # Filtering
    filter_bandwidth: float = 200.0

    # AGC
    agc_target: float = 0.5
    agc_attack_ms: float = 10.0
    agc_release_ms: float = 100.0

    # Squelch
    squelch_threshold: float = 0.05
    squelch_hysteresis: float = 0.02

    # Tone detection
    tone_threshold: float = 0.1

    # WPM detection
    initial_wpm: float = 20.0
    min_wpm: float = 5.0
    max_wpm: float = 55.0
    adaptive_timing: bool = True

    def __post_init__(self) -> None:
        """Validate configuration parameters."""
        if self.sample_rate <= 0:
            raise ValueError(f"Sample rate must be positive, got {self.sample_rate}")
        if self.chunk_size <= 0:
            raise ValueError(f"Chunk size must be positive, got {self.chunk_size}")

        min_freq, max_freq = self.freq_range
        if min_freq < 0:
            raise ValueError(f"Minimum frequency must be non-negative, got {min_freq}")
        if max_freq <= min_freq:
            raise ValueError(
                f"Maximum frequency must be greater than minimum, got {max_freq} <= {min_freq}"
            )

        if self.min_snr_db < 0:
            raise ValueError(f"Minimum SNR must be non-negative, got {self.min_snr_db}")

        if self.filter_bandwidth <= 0:
            raise ValueError(f"Filter bandwidth must be positive, got {self.filter_bandwidth}")

        if not 0.0 <= self.agc_target <= 1.0:
            raise ValueError(f"AGC target must be in [0, 1], got {self.agc_target}")
        if self.agc_attack_ms <= 0:
            raise ValueError(f"AGC attack time must be positive, got {self.agc_attack_ms}")
        if self.agc_release_ms <= 0:
            raise ValueError(f"AGC release time must be positive, got {self.agc_release_ms}")

        if not 0.0 <= self.squelch_threshold <= 1.0:
            raise ValueError(f"Squelch threshold must be in [0, 1], got {self.squelch_threshold}")
        if not 0.0 <= self.squelch_hysteresis <= 1.0:
            raise ValueError(f"Squelch hysteresis must be in [0, 1], got {self.squelch_hysteresis}")

        if not 0.0 <= self.tone_threshold <= 1.0:
            raise ValueError(f"Tone threshold must be in [0, 1], got {self.tone_threshold}")

        if self.initial_wpm <= 0:
            raise ValueError(f"Initial WPM must be positive, got {self.initial_wpm}")
        if self.min_wpm <= 0:
            raise ValueError(f"Minimum WPM must be positive, got {self.min_wpm}")
        if self.max_wpm <= self.min_wpm:
            raise ValueError(
                f"Maximum WPM must be greater than minimum, got {self.max_wpm} <= {self.min_wpm}"
            )

    @property
    def nyquist_frequency(self) -> float:
        """Get the Nyquist frequency for the configured sample rate.

        Returns:
            Nyquist frequency in Hz (sample_rate / 2)
        """
        return self.sample_rate / 2.0

    @property
    def chunk_duration_ms(self) -> float:
        """Get the duration of each audio chunk in milliseconds.

        Returns:
            Chunk duration in milliseconds
        """
        return (self.chunk_size / self.sample_rate) * 1000.0

    def validate_frequency(self, frequency: float) -> bool:
        """Check if a frequency is within the configured detection range.

        Args:
            frequency: Frequency to check in Hz

        Returns:
            True if frequency is within range, False otherwise
        """
        min_freq, max_freq = self.freq_range
        return min_freq <= frequency <= max_freq

    def validate_wpm(self, wpm: float) -> bool:
        """Check if a WPM value is within the configured detection range.

        Args:
            wpm: WPM to check

        Returns:
            True if WPM is within range, False otherwise
        """
        return self.min_wpm <= wpm <= self.max_wpm
