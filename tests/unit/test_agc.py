"""Unit tests for Automatic Gain Control (AGC)."""

import numpy as np
from continuous_wave.config import CWConfig
from continuous_wave.models import AudioSample
from continuous_wave.signal.noise import AutomaticGainControl


class TestAutomaticGainControl:
    """Tests for AutomaticGainControl class."""

    def test_initialization(self, config: CWConfig) -> None:
        """Test AGC initialization."""
        agc = AutomaticGainControl(config)

        assert agc.target == config.agc_target
        assert agc.sample_rate == config.sample_rate
        assert agc.envelope == 0.0
        assert agc.gain == 1.0

    def test_process_normalizes_strong_signal(self, config: CWConfig) -> None:
        """Test that AGC normalizes a strong signal down to target level."""
        agc = AutomaticGainControl(config)

        # Create a strong signal (amplitude = 2.0, well above target of 0.5)
        strong_signal = np.ones(1000, dtype=np.float32) * 2.0
        audio = AudioSample(data=strong_signal, sample_rate=config.sample_rate, timestamp=0.0)

        # Process multiple times to let AGC settle
        for _ in range(10):
            audio = agc.process(audio)

        # Output should be closer to target level
        output_level = np.max(np.abs(audio.data))
        assert output_level < 1.5  # Should be significantly reduced
        assert output_level > 0.3  # But not too much

    def test_process_amplifies_weak_signal(self, config: CWConfig) -> None:
        """Test that AGC amplifies a weak signal up to target level."""
        agc = AutomaticGainControl(config)

        # Create a weak signal (amplitude = 0.1, well below target of 0.5)
        weak_signal = np.ones(1000, dtype=np.float32) * 0.1

        # Process multiple times to let AGC settle, feeding same input each time
        output = None
        for _ in range(10):
            audio = AudioSample(data=weak_signal, sample_rate=config.sample_rate, timestamp=0.0)
            output = agc.process(audio)

        # Output should be closer to target level
        assert output is not None
        output_level = np.max(np.abs(output.data))
        assert output_level > 0.2  # Should be amplified
        assert output_level < 0.8  # But not too much

    def test_process_preserves_waveform_shape(self, config: CWConfig) -> None:
        """Test that AGC preserves the waveform shape (only scales amplitude)."""
        agc = AutomaticGainControl(config)

        # Create a sine wave
        num_samples = 1000
        t = np.arange(num_samples) / config.sample_rate
        frequency = 600.0
        original = np.sin(2 * np.pi * frequency * t).astype(np.float32) * 0.3

        audio = AudioSample(data=original, sample_rate=config.sample_rate, timestamp=0.0)

        # Process multiple times
        for _ in range(10):
            audio = agc.process(audio)

        # Normalize both signals to unit amplitude for comparison
        original_norm = original / (np.max(np.abs(original)) + 1e-10)
        output_norm = audio.data / (np.max(np.abs(audio.data)) + 1e-10)

        # Shapes should be similar (allowing for some deviation due to AGC dynamics)
        correlation = np.correlate(original_norm, output_norm, mode="valid")[0]
        assert correlation > 0.9  # High correlation means shape is preserved

    def test_process_handles_silence(self, config: CWConfig, silent_audio: AudioSample) -> None:
        """Test that AGC handles silence without dividing by zero."""
        agc = AutomaticGainControl(config)

        output = agc.process(silent_audio)

        # Should output silence without errors
        assert np.all(output.data == 0.0)
        assert not np.any(np.isnan(output.data))
        assert not np.any(np.isinf(output.data))

    def test_process_limits_extreme_gain(self, config: CWConfig) -> None:
        """Test that AGC limits gain to prevent extreme amplification."""
        agc = AutomaticGainControl(config)

        # Create an extremely weak signal
        tiny_signal = np.ones(100, dtype=np.float32) * 1e-6
        audio = AudioSample(data=tiny_signal, sample_rate=config.sample_rate, timestamp=0.0)

        output = agc.process(audio)

        # Gain should be limited (check that output isn't absurdly large)
        assert np.max(np.abs(output.data)) < 100.0  # Reasonable limit
        assert not np.any(np.isnan(output.data))
        assert not np.any(np.isinf(output.data))

    def test_process_fast_attack(self, config: CWConfig) -> None:
        """Test that AGC has fast attack time (responds quickly to strong signals)."""
        agc = AutomaticGainControl(config)

        # Start with weak signal, then sudden strong signal
        weak_signal = np.ones(100, dtype=np.float32) * 0.1
        strong_signal = np.ones(100, dtype=np.float32) * 5.0

        # Process weak signal first to build up gain
        for _ in range(10):
            audio = AudioSample(data=weak_signal, sample_rate=config.sample_rate, timestamp=0.0)
            agc.process(audio)

        # Then process strong signal multiple times to see response
        for _ in range(3):
            audio = AudioSample(data=strong_signal, sample_rate=config.sample_rate, timestamp=0.0)
            output = agc.process(audio)

        # AGC should respond quickly
        output_level = np.mean(np.abs(output.data))
        # Should be significantly reduced from input
        assert output_level < 3.5  # Should be lower than initial strong signal

    def test_process_slow_release(self, config: CWConfig) -> None:
        """Test that AGC has slow release time (responds slowly to weak signals)."""
        agc = AutomaticGainControl(config)

        # Start with strong signal, then sudden weak signal
        strong_signal = np.ones(100, dtype=np.float32) * 5.0
        weak_signal = np.ones(100, dtype=np.float32) * 0.1

        # Process strong signal first
        audio = AudioSample(data=strong_signal, sample_rate=config.sample_rate, timestamp=0.0)
        agc.process(audio)

        # Then process weak signal
        audio = AudioSample(data=weak_signal, sample_rate=config.sample_rate, timestamp=0.0)
        output = agc.process(audio)

        # AGC should respond slowly (gain shouldn't increase much in one chunk)
        # The output should still be relatively low
        output_level = np.mean(np.abs(output.data))
        assert output_level < 0.5  # Should not amplify much yet

    def test_reset(self, config: CWConfig) -> None:
        """Test that reset() clears AGC state."""
        agc = AutomaticGainControl(config)

        # Process some signal to build up state
        signal = np.ones(1000, dtype=np.float32) * 2.0
        audio = AudioSample(data=signal, sample_rate=config.sample_rate, timestamp=0.0)
        for _ in range(10):
            agc.process(audio)

        # State should be non-zero
        assert agc.envelope > 0.0
        assert agc.gain != 1.0

        # Reset
        agc.reset()

        # State should be cleared
        assert agc.envelope == 0.0
        assert agc.gain == 1.0

    def test_process_maintains_timestamp(self, config: CWConfig) -> None:
        """Test that AGC preserves timestamp in output."""
        agc = AutomaticGainControl(config)

        audio = AudioSample(
            data=np.ones(100, dtype=np.float32),
            sample_rate=config.sample_rate,
            timestamp=42.5,
        )

        output = agc.process(audio)

        assert output.timestamp == 42.5

    def test_process_maintains_sample_rate(self, config: CWConfig) -> None:
        """Test that AGC preserves sample rate in output."""
        agc = AutomaticGainControl(config)

        audio = AudioSample(
            data=np.ones(100, dtype=np.float32), sample_rate=config.sample_rate, timestamp=0.0
        )

        output = agc.process(audio)

        assert output.sample_rate == config.sample_rate
