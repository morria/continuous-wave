"""Tone detection for CW on/off keying."""

from dataclasses import dataclass, field

import numpy as np
from numpy.typing import NDArray
from scipy import signal as sp_signal

from continuous_wave.config import CWConfig
from continuous_wave.models import AudioSample, ToneEvent
from continuous_wave.protocols import ToneDetector


@dataclass
class EnvelopeDetector(ToneDetector):
    """Envelope-based tone detector for CW on/off keying.

    Uses envelope detection (rectify + lowpass) to determine when
    the carrier tone is present vs. absent.
    """

    config: CWConfig
    _envelope_filter: NDArray[np.float64] | None = field(default=None, init=False)
    _zi: NDArray[np.float64] | None = field(default=None, init=False)
    _threshold: float = field(default=0.1, init=False)
    _hysteresis: float = field(default=0.02, init=False)
    _is_tone_on: bool = field(default=False, init=False)
    _smoothed_level: float = field(default=0.0, init=False)
    _signal_floor: float = field(default=0.0, init=False)
    _signal_ceiling: float = field(default=1.0, init=False)

    def __post_init__(self) -> None:
        """Initialize envelope detection filter."""
        # Design lowpass filter for envelope detection
        # Cutoff at ~50Hz to smooth envelope while preserving CW keying
        cutoff_hz = 50.0
        nyquist = self.config.sample_rate / 2
        normalized_cutoff = cutoff_hz / nyquist

        # 4th order Butterworth lowpass
        sos = sp_signal.butter(
            4, normalized_cutoff, btype="low", output="sos", fs=self.config.sample_rate
        )
        self._envelope_filter = sos  # type: ignore[assignment]
        # Initialize filter state to zeros (not step response initial conditions)
        # Each section in SOS has 2 state variables
        num_sections = sos.shape[0]
        self._zi = np.zeros((num_sections, 2), dtype=np.float64)

        # Initialize threshold based on config tone threshold
        # Use tone_threshold which is more appropriate for envelope detection
        self._threshold = self.config.tone_threshold
        self._hysteresis = self.config.tone_threshold * 0.3  # 30% hysteresis

    def detect(self, audio: AudioSample) -> list[ToneEvent]:
        """Detect tone on/off events in audio.

        Args:
            audio: Audio sample to analyze

        Returns:
            List of ToneEvent objects for state transitions
        """
        if audio.num_samples == 0 or self._envelope_filter is None or self._zi is None:
            return []

        # Calculate signal level directly from audio chunk
        # Use RMS of the absolute values (simple envelope detection)
        # This is more responsive than using a lowpass filter on small chunks
        chunk_level = np.sqrt(np.mean(audio.data**2))

        # Adaptive threshold tracking
        # Update floor (min) and ceiling (max) with slow decay
        floor_alpha = 0.01  # Very slow tracking for floor
        ceiling_alpha = 0.05  # Slow tracking for ceiling

        if chunk_level < self._signal_floor or self._signal_floor == 0.0:
            self._signal_floor = chunk_level
        else:
            # Slowly increase floor towards current level if we're above it
            self._signal_floor += floor_alpha * (chunk_level - self._signal_floor)

        if chunk_level > self._signal_ceiling:
            self._signal_ceiling = chunk_level
        else:
            # Slowly decrease ceiling towards current level if we're below it
            self._signal_ceiling += ceiling_alpha * (chunk_level - self._signal_ceiling)

        # Calculate adaptive threshold as midpoint between floor and ceiling
        signal_range = self._signal_ceiling - self._signal_floor
        if signal_range > 0.05:  # Only use adaptive if there's enough dynamic range
            adaptive_threshold = self._signal_floor + signal_range * 0.5
            adaptive_hysteresis = signal_range * 0.1
        else:
            # Fall back to fixed threshold if signal is weak/flat
            adaptive_threshold = self.config.tone_threshold
            adaptive_hysteresis = self.config.tone_threshold * 0.3

        events: list[ToneEvent] = []

        # Hysteresis-based threshold detection
        if not self._is_tone_on:
            # Currently off - check for turn-on
            if chunk_level > adaptive_threshold + adaptive_hysteresis:
                self._is_tone_on = True
                events.append(
                    ToneEvent(
                        is_tone_on=True,
                        timestamp=audio.timestamp,
                        amplitude=float(chunk_level),
                    )
                )
        else:
            # Currently on - check for turn-off
            if chunk_level < adaptive_threshold - adaptive_hysteresis:
                self._is_tone_on = False
                events.append(
                    ToneEvent(
                        is_tone_on=False,
                        timestamp=audio.timestamp,
                        amplitude=float(chunk_level),
                    )
                )

        return events

    def reset(self) -> None:
        """Reset detector state."""
        if self._envelope_filter is not None:
            # Reset filter state to zeros
            num_sections = self._envelope_filter.shape[0]  # type: ignore[union-attr]
            self._zi = np.zeros((num_sections, 2), dtype=np.float64)
        self._is_tone_on = False
        self._smoothed_level = 0.0
        self._signal_floor = 0.0
        self._signal_ceiling = 1.0
