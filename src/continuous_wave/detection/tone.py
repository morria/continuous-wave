"""Tone detection for CW on/off keying."""

from collections import deque
from dataclasses import dataclass, field

import numpy as np

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
    _threshold: float = field(default=0.1, init=False)
    _hysteresis: float = field(default=0.02, init=False)
    _is_tone_on: bool = field(default=False, init=False)
    _signal_floor: float = field(default=0.0, init=False)
    _signal_ceiling: float = field(default=1.0, init=False)
    _window_size: int = field(default=0, init=False)
    _sample_buffer: deque[float] = field(default_factory=deque, init=False)

    def __post_init__(self) -> None:
        """Initialize envelope detector."""
        # Window size for moving average
        # Use 15ms window for good smoothing while maintaining CW timing accuracy
        # At 20 WPM, dot = 60ms, so 15ms window gives 4x resolution
        window_ms = 15.0
        self._window_size = int(window_ms * self.config.sample_rate / 1000.0)
        self._sample_buffer = deque(maxlen=self._window_size)

        # Initialize threshold based on config tone threshold
        self._threshold = self.config.tone_threshold
        self._hysteresis = self.config.tone_threshold * 0.5  # 50% hysteresis for stability

    def detect(self, audio: AudioSample) -> list[ToneEvent]:
        """Detect tone on/off events in audio.

        Args:
            audio: Audio sample to analyze

        Returns:
            List of ToneEvent objects for state transitions
        """
        if audio.num_samples == 0:
            return []

        # Compute envelope using moving window RMS
        # Process sample by sample for maximum timing precision
        events: list[ToneEvent] = []

        # Square the samples for RMS calculation
        squared_samples = audio.data ** 2

        for i, squared_sample in enumerate(squared_samples):
            # Add to buffer
            self._sample_buffer.append(float(squared_sample))

            # Compute RMS envelope (sqrt of mean of squares)
            if len(self._sample_buffer) >= self._window_size // 2:  # At least half full
                envelope_value = np.sqrt(np.mean(self._sample_buffer))

                # Adaptive threshold tracking
                # Update floor (min) and ceiling (max) with slow decay
                floor_alpha = 0.0001  # Very slow tracking for floor
                ceiling_alpha = 0.001  # Slow tracking for ceiling

                if envelope_value < self._signal_floor or self._signal_floor == 0.0:
                    self._signal_floor = envelope_value
                else:
                    self._signal_floor += floor_alpha * (envelope_value - self._signal_floor)

                if envelope_value > self._signal_ceiling:
                    self._signal_ceiling = envelope_value
                else:
                    self._signal_ceiling += ceiling_alpha * (envelope_value - self._signal_ceiling)

                # Calculate adaptive threshold
                signal_range = self._signal_ceiling - self._signal_floor
                if signal_range > 0.1:  # Only use adaptive if there's enough dynamic range
                    # Use 45% point (closer to floor) for better noise rejection
                    adaptive_threshold = self._signal_floor + signal_range * 0.45
                    # Use larger hysteresis for stability
                    adaptive_hysteresis = signal_range * 0.2
                else:
                    # Fall back to fixed threshold
                    adaptive_threshold = self.config.tone_threshold
                    adaptive_hysteresis = self.config.tone_threshold * 0.5

                # Calculate timestamp for this sample
                sample_timestamp = audio.timestamp + (i / self.config.sample_rate)

                # Hysteresis-based threshold detection
                if not self._is_tone_on:
                    # Currently off - check for turn-on
                    if envelope_value > adaptive_threshold + adaptive_hysteresis:
                        self._is_tone_on = True
                        events.append(
                            ToneEvent(
                                is_tone_on=True,
                                timestamp=sample_timestamp,
                                amplitude=float(envelope_value),
                            )
                        )
                else:
                    # Currently on - check for turn-off
                    if envelope_value < adaptive_threshold - adaptive_hysteresis:
                        self._is_tone_on = False
                        events.append(
                            ToneEvent(
                                is_tone_on=False,
                                timestamp=sample_timestamp,
                                amplitude=float(envelope_value),
                            )
                        )

        return events

    def reset(self) -> None:
        """Reset detector state."""
        self._sample_buffer.clear()
        self._is_tone_on = False
        self._signal_floor = 0.0
        self._signal_ceiling = 1.0
