"""Unit tests for Noise Reduction Pipeline."""

import numpy as np
from continuous_wave.config import CWConfig
from continuous_wave.models import AudioSample
from continuous_wave.signal.noise import NoiseReductionPipeline


class TestNoiseReductionPipeline:
    """Tests for NoiseReductionPipeline class."""

    def test_initialization(self, config: CWConfig) -> None:
        """Test pipeline initialization."""
        pipeline = NoiseReductionPipeline(config)

        assert pipeline.agc is not None
        assert pipeline.bandpass is not None
        assert pipeline.squelch is not None

    def test_initialization_with_center_frequency(self, config: CWConfig) -> None:
        """Test pipeline initialization with custom center frequency."""
        center_freq = 600.0
        pipeline = NoiseReductionPipeline(config, center_frequency=center_freq)

        assert pipeline.bandpass.center_frequency == center_freq

    def test_process_applies_all_stages(self, config: CWConfig) -> None:
        """Test that process() applies AGC, bandpass, and squelch."""
        pipeline = NoiseReductionPipeline(config, center_frequency=600.0)

        # Create a test signal at 600 Hz with high amplitude
        num_samples = 8000
        t = np.arange(num_samples) / config.sample_rate
        signal = np.sin(2 * np.pi * 600.0 * t).astype(np.float32) * 3.0

        audio = AudioSample(data=signal, sample_rate=config.sample_rate, timestamp=0.0)

        # Process through pipeline
        output = pipeline.process(audio)

        # Output should exist and be valid
        assert len(output.data) == len(audio.data)
        assert not np.any(np.isnan(output.data))
        assert not np.any(np.isinf(output.data))

    def test_process_chain_order(self, config: CWConfig) -> None:
        """Test that processing stages are applied in correct order: AGC → Filter → Squelch."""
        pipeline = NoiseReductionPipeline(config, center_frequency=600.0)

        # Create a strong signal at 600 Hz to ensure squelch opens
        num_samples = 8000
        t = np.arange(num_samples) / config.sample_rate
        signal = np.sin(2 * np.pi * 600.0 * t).astype(np.float32) * 5.0

        audio = AudioSample(data=signal, sample_rate=config.sample_rate, timestamp=0.0)

        # Process multiple times to let AGC and squelch settle
        for _ in range(10):
            output = pipeline.process(audio)

        # AGC should normalize the signal (amplitude should be closer to target)
        # Filter should pass the 600 Hz signal
        # Squelch should be open
        assert pipeline.squelch.is_open is True
        assert not np.all(output.data == 0.0)

        # Output amplitude should be normalized by AGC
        output_amplitude = np.max(np.abs(output.data))
        assert output_amplitude < 2.0  # Reduced from input amplitude of 5.0

    def test_retune(self, config: CWConfig) -> None:
        """Test retuning the pipeline to a new center frequency."""
        pipeline = NoiseReductionPipeline(config, center_frequency=600.0)

        assert pipeline.bandpass.center_frequency == 600.0

        # Retune to 800 Hz
        new_freq = 800.0
        pipeline.retune(new_freq)

        assert pipeline.bandpass.center_frequency == new_freq

    def test_reset(self, config: CWConfig) -> None:
        """Test that reset() clears all component states."""
        pipeline = NoiseReductionPipeline(config, center_frequency=600.0)

        # Build up state by processing signal
        num_samples = 8000
        t = np.arange(num_samples) / config.sample_rate
        signal = np.sin(2 * np.pi * 600.0 * t).astype(np.float32) * 3.0
        audio = AudioSample(data=signal, sample_rate=config.sample_rate, timestamp=0.0)

        for _ in range(10):
            pipeline.process(audio)

        # Components should have state
        assert pipeline.agc.gain != 1.0 or pipeline.agc.envelope != 0.0
        assert pipeline.squelch.is_open or pipeline.squelch.smoothed_level != 0.0

        # Reset
        pipeline.reset()

        # All component states should be cleared
        assert pipeline.agc.gain == 1.0
        assert pipeline.agc.envelope == 0.0
        assert pipeline.squelch.is_open is False
        assert pipeline.squelch.smoothed_level == 0.0

    def test_process_removes_out_of_band_noise(self, config: CWConfig) -> None:
        """Test that pipeline removes out-of-band noise."""
        center_freq = 600.0
        pipeline = NoiseReductionPipeline(config, center_frequency=center_freq)

        # Create a signal with in-band tone (600 Hz) + out-of-band noise (2000 Hz)
        num_samples = 8000
        t = np.arange(num_samples) / config.sample_rate

        in_band_signal = np.sin(2 * np.pi * center_freq * t) * 1.0
        out_of_band_noise = np.sin(2 * np.pi * 2000.0 * t) * 0.5

        combined_signal = (in_band_signal + out_of_band_noise).astype(np.float32)

        audio = AudioSample(data=combined_signal, sample_rate=config.sample_rate, timestamp=0.0)

        # Process through pipeline multiple times
        for _ in range(10):
            output = pipeline.process(audio)

        # Compute power spectrum of output to verify filtering
        # The 2000 Hz component should be significantly attenuated
        fft_output = np.fft.rfft(output.data)
        freqs = np.fft.rfftfreq(len(output.data), 1 / config.sample_rate)

        # Find power at 600 Hz and 2000 Hz
        idx_600 = np.argmin(np.abs(freqs - 600.0))
        idx_2000 = np.argmin(np.abs(freqs - 2000.0))

        power_600 = np.abs(fft_output[idx_600]) ** 2
        power_2000 = np.abs(fft_output[idx_2000]) ** 2

        # Power at 600 Hz should be much greater than at 2000 Hz
        assert power_600 > 10 * power_2000

    def test_process_handles_silence(self, config: CWConfig, silent_audio: AudioSample) -> None:
        """Test that pipeline handles silence without errors."""
        pipeline = NoiseReductionPipeline(config, center_frequency=600.0)

        output = pipeline.process(silent_audio)

        # Should handle silence without errors
        assert np.all(output.data == 0.0)
        assert not np.any(np.isnan(output.data))
        assert not np.any(np.isinf(output.data))

    def test_process_maintains_timestamp(self, config: CWConfig) -> None:
        """Test that pipeline preserves timestamp."""
        pipeline = NoiseReductionPipeline(config, center_frequency=600.0)

        audio = AudioSample(
            data=np.ones(100, dtype=np.float32),
            sample_rate=config.sample_rate,
            timestamp=42.5,
        )

        output = pipeline.process(audio)

        assert output.timestamp == 42.5

    def test_process_maintains_sample_rate(self, config: CWConfig) -> None:
        """Test that pipeline preserves sample rate."""
        pipeline = NoiseReductionPipeline(config, center_frequency=600.0)

        audio = AudioSample(
            data=np.ones(100, dtype=np.float32), sample_rate=config.sample_rate, timestamp=0.0
        )

        output = pipeline.process(audio)

        assert output.sample_rate == config.sample_rate

    def test_process_numerical_stability(self, config: CWConfig) -> None:
        """Test numerical stability over many iterations."""
        pipeline = NoiseReductionPipeline(config, center_frequency=600.0)

        # Process many chunks
        for i in range(100):
            signal = np.random.randn(256).astype(np.float32)
            audio = AudioSample(
                data=signal, sample_rate=config.sample_rate, timestamp=float(i) * 0.032
            )

            output = pipeline.process(audio)

            # Check for numerical issues
            assert not np.any(np.isnan(output.data))
            assert not np.any(np.isinf(output.data))
            assert np.max(np.abs(output.data)) < 1000.0
