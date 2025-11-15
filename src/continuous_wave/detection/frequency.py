"""Frequency detection for CW signals using FFT and Goertzel algorithm."""

from dataclasses import dataclass
from typing import Optional

import numpy as np
from numpy.typing import NDArray
from scipy import signal

from continuous_wave.config import CWConfig
from continuous_wave.models import SignalStats
from continuous_wave.protocols import FrequencyDetector


@dataclass
class FrequencyDetectorImpl(FrequencyDetector):
    """FFT-based frequency detector with Goertzel tracking.

    Uses FFT for initial frequency acquisition and Goertzel algorithm
    for efficient single-frequency tracking once locked.
    """

    config: CWConfig
    _current_frequency: Optional[float] = None
    _lock_count: int = 0
    _required_lock_samples: int = 5
    _fft_window: Optional[NDArray[np.float64]] = None

    def __post_init__(self) -> None:
        """Initialize FFT window for spectral analysis."""
        # Create Hann window for FFT to reduce spectral leakage
        self._fft_window = np.hanning(self.config.audio.chunk_size)

    def detect(self, audio: NDArray[np.float64]) -> Optional[SignalStats]:
        """Detect frequency and signal characteristics.

        Args:
            audio: Audio samples to analyze

        Returns:
            SignalStats with detected frequency and SNR, or None if no signal
        """
        if len(audio) < self.config.audio.chunk_size // 2:
            return None

        if self._current_frequency is None or not self.is_locked():
            # Not locked - use FFT for frequency search
            return self._fft_detect(audio)
        else:
            # Locked - use Goertzel for efficient tracking
            return self._goertzel_track(audio, self._current_frequency)

    def is_locked(self) -> bool:
        """Check if detector is locked onto a frequency.

        Returns:
            True if frequency lock is stable
        """
        return self._lock_count >= self._required_lock_samples

    def reset(self) -> None:
        """Reset detector state."""
        self._current_frequency = None
        self._lock_count = 0

    def _fft_detect(self, audio: NDArray[np.float64]) -> Optional[SignalStats]:
        """Detect frequency using FFT across search range.

        Args:
            audio: Audio samples to analyze

        Returns:
            SignalStats if strong signal found, None otherwise
        """
        # Apply window and compute FFT
        windowed = audio[: len(self._fft_window)] * self._fft_window
        fft = np.fft.rfft(windowed)
        power_spectrum = np.abs(fft) ** 2

        # Convert bin indices to frequencies
        freqs = np.fft.rfftfreq(len(windowed), 1 / self.config.audio.sample_rate)

        # Find peaks in the frequency range of interest
        min_freq = self.config.frequency.min_frequency
        max_freq = self.config.frequency.max_frequency

        # Mask to search range
        freq_mask = (freqs >= min_freq) & (freqs <= max_freq)
        if not np.any(freq_mask):
            return None

        # Find peak in range
        search_power = power_spectrum[freq_mask]
        search_freqs = freqs[freq_mask]

        peak_idx = np.argmax(search_power)
        peak_freq = search_freqs[peak_idx]
        peak_power = search_power[peak_idx]

        # Estimate noise floor (median of spectrum outside peak region)
        noise_mask = freq_mask & (np.abs(freqs - peak_freq) > 100)  # >100Hz from peak
        if np.any(noise_mask):
            noise_floor = np.median(power_spectrum[noise_mask])
        else:
            noise_floor = np.median(power_spectrum[freq_mask])

        # Calculate SNR in dB
        if noise_floor > 0:
            snr_db = 10 * np.log10(peak_power / noise_floor)
        else:
            snr_db = 100.0  # Very strong signal

        # Check if SNR meets threshold
        if snr_db < self.config.frequency.min_snr_db:
            self._lock_count = 0
            self._current_frequency = None
            return None

        # Update tracking state
        if self._current_frequency is None:
            self._current_frequency = peak_freq
            self._lock_count = 1
        elif abs(peak_freq - self._current_frequency) < 10:  # Within 10Hz
            self._lock_count += 1
            # Smooth frequency estimate
            alpha = 0.3
            self._current_frequency = (
                alpha * peak_freq + (1 - alpha) * self._current_frequency
            )
        else:
            # Frequency jumped - restart lock
            self._current_frequency = peak_freq
            self._lock_count = 1

        return SignalStats(
            frequency=self._current_frequency,
            snr_db=snr_db,
            power=float(peak_power),
            timestamp=0.0,  # Will be set by pipeline
        )

    def _goertzel_track(
        self, audio: NDArray[np.float64], target_freq: float
    ) -> Optional[SignalStats]:
        """Track a specific frequency using Goertzel algorithm.

        More efficient than FFT when tracking a single frequency.

        Args:
            audio: Audio samples to analyze
            target_freq: Frequency to track (Hz)

        Returns:
            SignalStats for the tracked frequency
        """
        # Goertzel algorithm for single frequency
        N = len(audio)
        k = int(0.5 + (N * target_freq) / self.config.audio.sample_rate)
        w = (2.0 * np.pi * k) / N
        cosine = np.cos(w)
        sine = np.sin(w)
        coeff = 2.0 * cosine

        # Goertzel filter
        q0 = 0.0
        q1 = 0.0
        q2 = 0.0

        for sample in audio:
            q0 = coeff * q1 - q2 + sample
            q2 = q1
            q1 = q0

        # Calculate magnitude
        real = q1 - q2 * cosine
        imag = q2 * sine
        magnitude = np.sqrt(real * real + imag * imag)
        power = magnitude * magnitude

        # Estimate noise floor using nearby frequencies
        noise_power = 0.0
        for offset in [-50, 50]:  # Check ±50Hz
            offset_freq = target_freq + offset
            if (
                self.config.frequency.min_frequency
                <= offset_freq
                <= self.config.frequency.max_frequency
            ):
                noise_power += self._goertzel_power(audio, offset_freq)
        noise_power /= 2.0

        # Calculate SNR
        if noise_power > 0:
            snr_db = 10 * np.log10(power / noise_power)
        else:
            snr_db = 100.0

        # Check if still locked
        if snr_db < self.config.frequency.min_snr_db:
            self._lock_count = max(0, self._lock_count - 1)
            if self._lock_count == 0:
                self._current_frequency = None
            return None

        self._lock_count = min(self._lock_count + 1, self._required_lock_samples + 5)

        return SignalStats(
            frequency=target_freq,
            snr_db=snr_db,
            power=float(power),
            timestamp=0.0,  # Will be set by pipeline
        )

    def _goertzel_power(self, audio: NDArray[np.float64], freq: float) -> float:
        """Calculate power at a specific frequency using Goertzel.

        Args:
            audio: Audio samples
            freq: Target frequency (Hz)

        Returns:
            Power at the target frequency
        """
        N = len(audio)
        k = int(0.5 + (N * freq) / self.config.audio.sample_rate)
        w = (2.0 * np.pi * k) / N
        cosine = np.cos(w)
        sine = np.sin(w)
        coeff = 2.0 * cosine

        q0 = 0.0
        q1 = 0.0
        q2 = 0.0

        for sample in audio:
            q0 = coeff * q1 - q2 + sample
            q2 = q1
            q1 = q0

        real = q1 - q2 * cosine
        imag = q2 * sine
        magnitude = np.sqrt(real * real + imag * imag)
        return magnitude * magnitude
