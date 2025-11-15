"""Unit tests for Squelch Gate."""

import numpy as np

from continuous_wave.config import CWConfig
from continuous_wave.models import AudioSample
from continuous_wave.signal.noise import SquelchGate


class TestSquelchGate:
    """Tests for SquelchGate class."""

    def test_initialization(self, config: CWConfig) -> None:
        """Test squelch gate initialization."""
        squelch = SquelchGate(config)

        assert squelch.threshold == config.squelch_threshold
        assert squelch.hysteresis == config.squelch_hysteresis
        assert squelch.is_open is False
        assert squelch.smoothed_level == 0.0

    def test_process_opens_gate_on_strong_signal(self, config: CWConfig) -> None:
        """Test that gate opens when signal exceeds threshold + hysteresis."""
        # Set a higher threshold for this test
        config_custom = CWConfig(squelch_threshold=0.2, squelch_hysteresis=0.05)
        squelch = SquelchGate(config_custom)

        # Create a very strong signal that will quickly exceed threshold + hysteresis (0.25)
        # Use amplitude of 2.0 which is well above threshold
        strong_signal = np.ones(1000, dtype=np.float32) * 2.0
        audio = AudioSample(data=strong_signal, sample_rate=config.sample_rate, timestamp=0.0)

        # Process signal multiple times to let smoothed level build up
        for _ in range(10):
            output = squelch.process(audio)

        # Gate should open
        assert squelch.is_open is True
        # Output should pass through (not all zeros)
        assert not np.all(output.data == 0.0)

    def test_process_keeps_gate_closed_on_weak_signal(
        self, config: CWConfig, silent_audio: AudioSample
    ) -> None:
        """Test that gate stays closed when signal is below threshold."""
        squelch = SquelchGate(config)

        # Process weak signal
        output = squelch.process(silent_audio)

        # Gate should remain closed
        assert squelch.is_open is False
        # Output should be all zeros
        assert np.all(output.data == 0.0)

    def test_process_hysteresis_prevents_chattering(self, config: CWConfig) -> None:
        """Test that hysteresis prevents gate from chattering at threshold."""
        config_custom = CWConfig(squelch_threshold=0.2, squelch_hysteresis=0.05)
        squelch = SquelchGate(config_custom)

        # First, open the gate with a very strong signal
        strong_signal = np.ones(1000, dtype=np.float32) * 2.0
        audio = AudioSample(data=strong_signal, sample_rate=config.sample_rate, timestamp=0.0)

        # Process multiple times to open gate
        for _ in range(10):
            squelch.process(audio)
        assert squelch.is_open is True

        # Now send a signal that's above lower threshold but below upper threshold
        # Lower threshold = 0.2 - 0.05 = 0.15
        # Upper threshold = 0.2 + 0.05 = 0.25
        # Send signal with RMS around 0.20 (between thresholds)
        medium_signal = np.ones(1000, dtype=np.float32) * 0.20
        audio = AudioSample(data=medium_signal, sample_rate=config.sample_rate, timestamp=0.0)

        output = squelch.process(audio)

        # Gate should stay open due to hysteresis
        assert squelch.is_open is True
        assert not np.all(output.data == 0.0)

    def test_process_closes_gate_on_weak_signal_after_open(self, config: CWConfig) -> None:
        """Test that gate closes when signal drops below threshold - hysteresis."""
        config_custom = CWConfig(squelch_threshold=0.2, squelch_hysteresis=0.05)
        squelch = SquelchGate(config_custom)

        # Open the gate with very strong signal
        strong_signal = np.ones(1000, dtype=np.float32) * 2.0
        audio = AudioSample(data=strong_signal, sample_rate=config.sample_rate, timestamp=0.0)

        # Process multiple times to open gate
        for _ in range(10):
            squelch.process(audio)
        assert squelch.is_open is True

        # Send very weak signal below lower threshold (< 0.15)
        weak_signal = np.ones(1000, dtype=np.float32) * 0.01
        audio = AudioSample(data=weak_signal, sample_rate=config.sample_rate, timestamp=0.0)

        # Process many times to let smoothed level decrease sufficiently
        # With smooth_coef=0.1, it takes many iterations to decay from 2.0 to below 0.15
        for _ in range(30):
            output = squelch.process(audio)

        # Gate should eventually close
        assert squelch.is_open is False
        assert np.all(output.data == 0.0)

    def test_process_smooths_level_measurement(self, config: CWConfig) -> None:
        """Test that level measurement is smoothed over time."""
        squelch = SquelchGate(config)

        # Process one chunk of strong signal
        strong_signal = np.ones(100, dtype=np.float32) * 1.0
        audio = AudioSample(data=strong_signal, sample_rate=config.sample_rate, timestamp=0.0)
        squelch.process(audio)

        level_after_one_chunk = squelch.smoothed_level

        # Process another chunk
        squelch.process(audio)

        level_after_two_chunks = squelch.smoothed_level

        # Smoothed level should increase gradually (not jump immediately to 1.0)
        assert 0.0 < level_after_one_chunk < 1.0
        assert level_after_two_chunks > level_after_one_chunk

    def test_process_outputs_zeros_when_closed(
        self, config: CWConfig, silent_audio: AudioSample
    ) -> None:
        """Test that output is zeros when gate is closed."""
        squelch = SquelchGate(config)

        # Gate starts closed
        assert squelch.is_open is False

        # Use silent audio to ensure gate stays closed
        output = squelch.process(silent_audio)

        # Output should be all zeros
        assert np.all(output.data == 0.0)

    def test_process_passes_signal_when_open(self, config: CWConfig) -> None:
        """Test that signal passes through when gate is open."""
        squelch = SquelchGate(config)

        # Create strong signal to open gate
        strong_signal = np.random.randn(1000).astype(np.float32) * 2.0
        audio = AudioSample(data=strong_signal, sample_rate=config.sample_rate, timestamp=0.0)

        output = squelch.process(audio)

        # Gate should be open
        assert squelch.is_open is True

        # Output should match input (signal passes through)
        np.testing.assert_array_equal(output.data, audio.data)

    def test_reset(self, config: CWConfig) -> None:
        """Test that reset() clears squelch state."""
        squelch = SquelchGate(config)

        # Build up some state
        strong_signal = np.ones(1000, dtype=np.float32) * 2.0
        audio = AudioSample(data=strong_signal, sample_rate=config.sample_rate, timestamp=0.0)
        squelch.process(audio)

        # State should be non-zero
        assert squelch.is_open is True
        assert squelch.smoothed_level > 0.0

        # Reset
        squelch.reset()

        # State should be cleared
        assert squelch.is_open is False
        assert squelch.smoothed_level == 0.0

    def test_process_maintains_timestamp(self, config: CWConfig) -> None:
        """Test that squelch preserves timestamp in output."""
        squelch = SquelchGate(config)

        audio = AudioSample(
            data=np.ones(100, dtype=np.float32),
            sample_rate=config.sample_rate,
            timestamp=42.5,
        )

        output = squelch.process(audio)

        assert output.timestamp == 42.5

    def test_process_maintains_sample_rate(self, config: CWConfig) -> None:
        """Test that squelch preserves sample rate in output."""
        squelch = SquelchGate(config)

        audio = AudioSample(
            data=np.ones(100, dtype=np.float32), sample_rate=config.sample_rate, timestamp=0.0
        )

        output = squelch.process(audio)

        assert output.sample_rate == config.sample_rate

    def test_process_rms_calculation(self, config: CWConfig) -> None:
        """Test that RMS calculation is correct."""
        config_custom = CWConfig(squelch_threshold=0.5, squelch_hysteresis=0.01)
        squelch = SquelchGate(config_custom)

        # Create signal with known RMS
        # For a constant signal, RMS = abs(value)
        value = 0.6
        signal = np.ones(1000, dtype=np.float32) * value
        audio = AudioSample(data=signal, sample_rate=config.sample_rate, timestamp=0.0)

        # Process multiple times to let smoothed level stabilize
        for _ in range(20):
            squelch.process(audio)

        # Smoothed level should approach the RMS value
        expected_rms = value
        assert abs(squelch.smoothed_level - expected_rms) < 0.1
