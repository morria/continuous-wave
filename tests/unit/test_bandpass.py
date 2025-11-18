"""Unit tests for Adaptive Bandpass Filter."""

import numpy as np

from continuous_wave.config import CWConfig
from continuous_wave.signal.noise import AdaptiveBandpassFilter


class TestAdaptiveBandpassFilter:
    """Tests for AdaptiveBandpassFilter class."""

    def test_initialization_with_default_frequency(self, config: CWConfig) -> None:
        """Test filter initialization with default center frequency."""
        filt = AdaptiveBandpassFilter(config)

        # Should default to middle of frequency range
        expected_center = (config.freq_range[0] + config.freq_range[1]) / 2.0
        assert filt.center_frequency == expected_center
        assert filt.bandwidth == config.filter_bandwidth
        assert filt.sample_rate == config.sample_rate

    def test_initialization_with_custom_frequency(self, config: CWConfig) -> None:
        """Test filter initialization with custom center frequency."""
        center_freq = 600.0
        filt = AdaptiveBandpassFilter(config, center_frequency=center_freq)

        assert filt.center_frequency == center_freq

    def test_filter_passes_in_band_signal(self, config: CWConfig) -> None:
        """Test that filter passes signals within the passband."""
        center_freq = 600.0
        filt = AdaptiveBandpassFilter(config, center_frequency=center_freq)

        # Create a signal at the center frequency
        num_samples = 8000  # 1 second
        t = np.arange(num_samples) / config.sample_rate
        signal = np.sin(2 * np.pi * center_freq * t).astype(np.float32)

        # Filter the signal
        output = filt.filter(signal)

        # Output power should be significant (filter passes the signal)
        input_power = np.mean(signal**2)
        output_power = np.mean(output**2)

        # Should retain most of the power (allowing some loss from filter)
        assert output_power > 0.5 * input_power

    def test_filter_attenuates_out_of_band_signal(self, config: CWConfig) -> None:
        """Test that filter attenuates signals outside the passband."""
        center_freq = 600.0
        filt = AdaptiveBandpassFilter(config, center_frequency=center_freq)

        # Create a signal well outside the passband (2000 Hz)
        num_samples = 8000  # 1 second
        t = np.arange(num_samples) / config.sample_rate
        out_of_band_freq = 2000.0
        signal = np.sin(2 * np.pi * out_of_band_freq * t).astype(np.float32)

        # Filter the signal
        output = filt.filter(signal)

        # Output power should be significantly reduced
        input_power = np.mean(signal**2)
        output_power = np.mean(output**2)

        # Should attenuate significantly
        assert output_power < 0.1 * input_power

    def test_filter_bandwidth(self, config: CWConfig) -> None:
        """Test filter bandwidth by checking attenuation at edges."""
        center_freq = 600.0
        bandwidth = 100.0
        config_with_bandwidth = CWConfig(filter_bandwidth=bandwidth)
        filt = AdaptiveBandpassFilter(config_with_bandwidth, center_frequency=center_freq)

        num_samples = 8000

        # Test signal at center frequency (should pass)
        t = np.arange(num_samples) / config.sample_rate
        center_signal = np.sin(2 * np.pi * center_freq * t).astype(np.float32)
        center_output = filt.filter(center_signal)
        center_power = np.mean(center_output**2)

        # Reset filter state for next test
        filt.reset()

        # Test signal at edge of passband (center + bandwidth/2)
        edge_freq = center_freq + bandwidth / 2.0
        edge_signal = np.sin(2 * np.pi * edge_freq * t).astype(np.float32)
        edge_output = filt.filter(edge_signal)
        edge_power = np.mean(edge_output**2)

        # Edge should have less power than center, but still significant
        assert edge_power < center_power
        assert edge_power > 0.1 * center_power  # Still in passband

    def test_retune(self, config: CWConfig) -> None:
        """Test retuning the filter to a new center frequency."""
        filt = AdaptiveBandpassFilter(config, center_frequency=600.0)

        # Initially tuned to 600 Hz
        assert filt.center_frequency == 600.0

        # Retune to 800 Hz
        new_freq = 800.0
        filt.retune(new_freq)

        assert filt.center_frequency == new_freq

        # Test that it now passes 800 Hz signal
        num_samples = 8000
        t = np.arange(num_samples) / config.sample_rate
        signal = np.sin(2 * np.pi * new_freq * t).astype(np.float32)

        output = filt.filter(signal)
        output_power = np.mean(output**2)
        input_power = np.mean(signal**2)

        # Should pass the signal at new frequency
        assert output_power > 0.5 * input_power

    def test_reset(self, config: CWConfig) -> None:
        """Test that reset() clears filter state."""
        filt = AdaptiveBandpassFilter(config, center_frequency=600.0)

        # Process some signal to build up filter state
        num_samples = 1000
        t = np.arange(num_samples) / config.sample_rate
        signal = np.sin(2 * np.pi * 600.0 * t).astype(np.float32)

        filt.filter(signal)

        # Reset
        filt.reset()

        # Filter state should be reset (zi should be back to initial state)
        # We can't directly check zi, but we can verify it doesn't error
        # and produces expected output
        output = filt.filter(signal)
        assert len(output) == len(signal)
        assert not np.any(np.isnan(output))

    def test_filter_handles_edge_frequencies(self, config: CWConfig) -> None:
        """Test filter with frequencies at edges of valid range."""
        # Test with very low frequency
        low_freq = 10.0
        filt = AdaptiveBandpassFilter(config, center_frequency=low_freq)
        assert filt.center_frequency == low_freq

        num_samples = 1000
        t = np.arange(num_samples) / config.sample_rate
        signal = np.sin(2 * np.pi * low_freq * t).astype(np.float32)
        output = filt.filter(signal)

        assert not np.any(np.isnan(output))
        assert not np.any(np.isinf(output))

        # Test with high frequency (near Nyquist)
        high_freq = config.sample_rate / 2.0 - 200.0
        filt = AdaptiveBandpassFilter(config, center_frequency=high_freq)
        assert filt.center_frequency == high_freq

        signal = np.sin(2 * np.pi * high_freq * t).astype(np.float32)
        output = filt.filter(signal)

        assert not np.any(np.isnan(output))
        assert not np.any(np.isinf(output))

    def test_filter_output_length_matches_input(self, config: CWConfig) -> None:
        """Test that output length matches input length."""
        filt = AdaptiveBandpassFilter(config, center_frequency=600.0)

        for length in [100, 256, 512, 1000]:
            signal = np.random.randn(length).astype(np.float32)
            output = filt.filter(signal)
            assert len(output) == length

    def test_filter_numerical_stability(self, config: CWConfig) -> None:
        """Test that filter remains numerically stable over many iterations."""
        filt = AdaptiveBandpassFilter(config, center_frequency=600.0)

        # Process many chunks of data
        for _ in range(100):
            signal = np.random.randn(256).astype(np.float32)
            output = filt.filter(signal)

            # Check for numerical issues
            assert not np.any(np.isnan(output))
            assert not np.any(np.isinf(output))
            assert np.max(np.abs(output)) < 1000.0  # Reasonable bound

    def test_filter_preserves_dtype(self, config: CWConfig) -> None:
        """Test that filter output has float32 dtype."""
        filt = AdaptiveBandpassFilter(config, center_frequency=600.0)

        signal = np.random.randn(256).astype(np.float32)
        output = filt.filter(signal)

        assert output.dtype == np.float32
