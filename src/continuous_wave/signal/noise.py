"""Noise reduction and signal conditioning components.

This module implements AGC, bandpass filtering, and squelch gating for robust
signal processing in noisy environments.
"""

import numpy as np
import numpy.typing as npt
from scipy import signal

from continuous_wave.config import CWConfig
from continuous_wave.models import AudioSample


class AutomaticGainControl:
    """Automatic Gain Control (AGC) for normalizing signal levels.

    AGC maintains a constant output level regardless of input signal strength,
    preventing clipping and ensuring consistent decoding performance.

    Algorithm:
    - Track signal envelope using attack/release time constants
    - Adjust gain to maintain target output level
    - Fast attack (10ms default) for quick response to strong signals
    - Slow release (100ms default) for stability

    Attributes:
        target: Target output level (0.0 to 1.0)
        sample_rate: Sample rate in Hz
    """

    def __init__(self, config: CWConfig) -> None:
        """Initialize AGC.

        Args:
            config: Configuration object with AGC parameters
        """
        self.target = config.agc_target
        self.sample_rate = config.sample_rate

        # Convert time constants to samples
        attack_samples = int(config.agc_attack_ms * self.sample_rate / 1000.0)
        release_samples = int(config.agc_release_ms * self.sample_rate / 1000.0)

        # Compute smoothing coefficients (exponential moving average)
        self.attack_coef = 1.0 - np.exp(-1.0 / max(1, attack_samples))
        self.release_coef = 1.0 - np.exp(-1.0 / max(1, release_samples))

        # State
        self.envelope = 0.0
        self.gain = 1.0

    def process(self, audio: AudioSample) -> AudioSample:
        """Process audio through AGC.

        Args:
            audio: Input audio sample

        Returns:
            AudioSample with normalized levels
        """
        data = audio.data.copy()
        output = np.zeros_like(data)

        for i, sample in enumerate(data):
            # Compute instantaneous amplitude
            amplitude = abs(sample)

            # Update envelope with attack/release
            if amplitude > self.envelope:
                # Attack: fast response to increasing signal
                self.envelope += self.attack_coef * (amplitude - self.envelope)
            else:
                # Release: slow response to decreasing signal
                self.envelope += self.release_coef * (amplitude - self.envelope)

            # Compute required gain to reach target
            if self.envelope > 1e-10:  # Avoid division by zero
                desired_gain = self.target / self.envelope
                # Limit gain to prevent extreme amplification
                desired_gain = np.clip(desired_gain, 0.1, 10.0)
            else:
                desired_gain = 1.0

            # Smooth gain changes to avoid artifacts
            self.gain += self.attack_coef * (desired_gain - self.gain)

            # Apply gain
            output[i] = sample * self.gain

        return AudioSample(
            data=output.astype(np.float32),
            sample_rate=audio.sample_rate,
            timestamp=audio.timestamp,
        )

    def reset(self) -> None:
        """Reset AGC state."""
        self.envelope = 0.0
        self.gain = 1.0


class AdaptiveBandpassFilter:
    """Narrow bandpass filter around detected CW frequency.

    Uses a 4th-order Butterworth filter with second-order sections (SOS)
    for numerical stability. The filter can be retuned to track frequency changes.

    Attributes:
        center_frequency: Current center frequency in Hz
        bandwidth: Filter bandwidth in Hz
        sample_rate: Sample rate in Hz
    """

    def __init__(self, config: CWConfig, center_frequency: float | None = None) -> None:
        """Initialize bandpass filter.

        Args:
            config: Configuration object with filter parameters
            center_frequency: Initial center frequency in Hz (default: middle of freq_range)
        """
        self.sample_rate = config.sample_rate
        self.bandwidth = config.filter_bandwidth

        # Default to middle of frequency range
        if center_frequency is None:
            min_freq, max_freq = config.freq_range
            center_frequency = (min_freq + max_freq) / 2.0

        self.center_frequency = center_frequency

        # Design the filter
        self._design_filter()

    def _design_filter(self) -> None:
        """Design the bandpass filter using current parameters."""
        # Compute low and high cutoff frequencies
        low_freq = self.center_frequency - self.bandwidth / 2.0
        high_freq = self.center_frequency + self.bandwidth / 2.0

        # Ensure frequencies are within valid range
        nyquist = self.sample_rate / 2.0
        low_freq = max(1.0, min(low_freq, nyquist - 1.0))
        high_freq = max(low_freq + 1.0, min(high_freq, nyquist - 1.0))

        # Design 4th-order Butterworth bandpass filter
        self.sos = signal.butter(
            N=4,
            Wn=[low_freq, high_freq],
            btype="bandpass",
            fs=self.sample_rate,
            output="sos",
        )

        # Initialize filter state
        self.zi = signal.sosfilt_zi(self.sos)

    def filter(self, data: npt.NDArray[np.float32]) -> npt.NDArray[np.float32]:
        """Filter the input data.

        Args:
            data: Input audio data

        Returns:
            Filtered audio data
        """
        # Apply filter with state
        # Type ignore needed for mypy <1.9 with incomplete scipy-stubs
        filtered_output, new_zi = signal.sosfilt(self.sos, data, zi=self.zi)  # type: ignore
        self.zi = new_zi  # type: ignore
        result: npt.NDArray[np.float32] = np.asarray(filtered_output, dtype=np.float32)  # type: ignore
        return result

    def retune(self, center_frequency: float) -> None:
        """Retune the filter to a new center frequency.

        Args:
            center_frequency: New center frequency in Hz
        """
        self.center_frequency = center_frequency
        self._design_filter()

    def reset(self) -> None:
        """Reset filter state."""
        self.zi = signal.sosfilt_zi(self.sos)


class SquelchGate:
    """Squelch gate to mute output below threshold.

    Prevents noise from triggering the decoder when no signal is present.
    Uses hysteresis to prevent chattering at the threshold.

    Algorithm:
    - Open gate when signal > threshold + hysteresis
    - Close gate when signal < threshold - hysteresis
    - Smooth transitions to avoid clicks

    Attributes:
        threshold: Squelch threshold (0.0 to 1.0)
        hysteresis: Hysteresis amount (0.0 to 1.0)
    """

    def __init__(self, config: CWConfig) -> None:
        """Initialize squelch gate.

        Args:
            config: Configuration object with squelch parameters
        """
        self.threshold = config.squelch_threshold
        self.hysteresis = config.squelch_hysteresis

        # State
        self.is_open = False
        self.smoothed_level = 0.0

        # Smoothing coefficient (prevents rapid switching)
        self.smooth_coef = 0.1

    def process(self, audio: AudioSample) -> AudioSample:
        """Process audio through squelch gate.

        Args:
            audio: Input audio sample

        Returns:
            AudioSample with squelch applied (zeros if gate closed)
        """
        data = audio.data

        # Compute RMS level of the signal
        rms = np.sqrt(np.mean(data**2))

        # Smooth the level measurement
        self.smoothed_level += self.smooth_coef * (rms - self.smoothed_level)

        # Update gate state with hysteresis
        if self.smoothed_level > self.threshold + self.hysteresis:
            self.is_open = True
        elif self.smoothed_level < self.threshold - self.hysteresis:
            self.is_open = False

        # Apply gate
        output_data = data if self.is_open else np.zeros_like(data)

        return AudioSample(
            data=output_data.astype(np.float32),
            sample_rate=audio.sample_rate,
            timestamp=audio.timestamp,
        )

    def reset(self) -> None:
        """Reset squelch state."""
        self.is_open = False
        self.smoothed_level = 0.0


class NoiseReductionPipeline:
    """Complete noise reduction pipeline combining AGC, filtering, and squelch.

    This is a convenience class that chains together all noise reduction
    components in the proper order.

    Processing order:
    1. AGC - Normalize signal levels
    2. Bandpass filter - Remove out-of-band noise
    3. Squelch - Mute when no signal present
    """

    def __init__(
        self,
        config: CWConfig,
        center_frequency: float | None = None,
    ) -> None:
        """Initialize noise reduction pipeline.

        Args:
            config: Configuration object
            center_frequency: Initial center frequency for bandpass filter
        """
        self.agc = AutomaticGainControl(config)
        self.bandpass = AdaptiveBandpassFilter(config, center_frequency)
        self.squelch = SquelchGate(config)

    def process(self, audio: AudioSample) -> AudioSample:
        """Process audio through the complete noise reduction pipeline.

        Args:
            audio: Input audio sample

        Returns:
            Processed audio sample
        """
        # Stage 1: AGC
        audio = self.agc.process(audio)

        # Stage 2: Bandpass filtering
        filtered_data = self.bandpass.filter(audio.data)
        audio = AudioSample(
            data=filtered_data,
            sample_rate=audio.sample_rate,
            timestamp=audio.timestamp,
        )

        # Stage 3: Squelch
        audio = self.squelch.process(audio)

        return audio

    def retune(self, center_frequency: float) -> None:
        """Retune the bandpass filter to a new center frequency.

        Args:
            center_frequency: New center frequency in Hz
        """
        self.bandpass.retune(center_frequency)

    def reset(self) -> None:
        """Reset all components."""
        self.agc.reset()
        self.bandpass.reset()
        self.squelch.reset()
