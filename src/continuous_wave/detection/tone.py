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
        self._zi = sp_signal.sosfilt_zi(sos).astype(np.float64)

        # Initialize threshold based on config squelch
        self._threshold = self.config.squelch_threshold
        self._hysteresis = self.config.squelch_hysteresis

    def detect(self, audio: AudioSample) -> list[ToneEvent]:
        """Detect tone on/off events in audio.

        Args:
            audio: Audio sample to analyze

        Returns:
            List of ToneEvent objects for state transitions
        """
        if audio.num_samples == 0 or self._envelope_filter is None or self._zi is None:
            return []

        # Rectify signal (absolute value)
        rectified = np.abs(audio.data)

        # Apply lowpass filter to get envelope
        envelope, self._zi = sp_signal.sosfilt(  # type: ignore[assignment]
            self._envelope_filter, rectified, zi=self._zi
        )

        # Detect transitions
        events: list[ToneEvent] = []

        for level in envelope:
            # Smooth level measurement with exponential moving average
            alpha = 0.1
            self._smoothed_level = alpha * level + (1 - alpha) * self._smoothed_level

            # Hysteresis-based threshold detection
            if not self._is_tone_on:
                # Currently off - check for turn-on
                if self._smoothed_level > self._threshold + self._hysteresis:
                    self._is_tone_on = True
                    events.append(
                        ToneEvent(
                            is_tone_on=True,
                            timestamp=0.0,  # Will be set by pipeline
                            amplitude=float(self._smoothed_level),
                        )
                    )
            else:
                # Currently on - check for turn-off
                if self._smoothed_level < self._threshold - self._hysteresis:
                    self._is_tone_on = False
                    events.append(
                        ToneEvent(
                            is_tone_on=False,
                            timestamp=0.0,  # Will be set by pipeline
                            amplitude=float(self._smoothed_level),
                        )
                    )

        return events

    def reset(self) -> None:
        """Reset detector state."""
        if self._envelope_filter is not None:
            self._zi = sp_signal.sosfilt_zi(self._envelope_filter).astype(np.float64)  # type: ignore[assignment]
        self._is_tone_on = False
        self._smoothed_level = 0.0
