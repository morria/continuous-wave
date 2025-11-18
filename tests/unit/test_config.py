"""Unit tests for configuration."""

import pytest
from continuous_wave.config import CWConfig


class TestCWConfig:
    """Tests for CWConfig dataclass."""

    def test_default_values(self) -> None:
        """Test that default configuration has expected values."""
        config = CWConfig()

        # Audio settings
        assert config.sample_rate == 8000
        assert config.chunk_size == 256

        # Frequency detection
        assert config.freq_range == (200.0, 1200.0)
        assert config.min_snr_db == 6.0

        # Filtering
        assert config.filter_bandwidth == 100.0

        # AGC
        assert config.agc_target == 0.5
        assert config.agc_attack_ms == 10.0
        assert config.agc_release_ms == 100.0

        # Squelch
        assert config.squelch_threshold == 0.05
        assert config.squelch_hysteresis == 0.02

        # Tone detection
        assert config.tone_threshold == 0.1

        # WPM detection
        assert config.initial_wpm == 20.0
        assert config.min_wpm == 5.0
        assert config.max_wpm == 55.0
        assert config.adaptive_timing is True

    def test_custom_values(self) -> None:
        """Test creating configuration with custom values."""
        config = CWConfig(
            sample_rate=16000,
            chunk_size=512,
            freq_range=(300.0, 1000.0),
            min_snr_db=10.0,
        )

        assert config.sample_rate == 16000
        assert config.chunk_size == 512
        assert config.freq_range == (300.0, 1000.0)
        assert config.min_snr_db == 10.0

    def test_nyquist_frequency(self) -> None:
        """Test Nyquist frequency calculation."""
        config = CWConfig(sample_rate=8000)
        assert config.nyquist_frequency == 4000.0

        config = CWConfig(sample_rate=16000)
        assert config.nyquist_frequency == 8000.0

    def test_chunk_duration_ms(self) -> None:
        """Test chunk duration calculation."""
        config = CWConfig(sample_rate=8000, chunk_size=256)
        assert config.chunk_duration_ms == 32.0  # 256 / 8000 * 1000

        config = CWConfig(sample_rate=8000, chunk_size=512)
        assert config.chunk_duration_ms == 64.0

    def test_validate_frequency(self) -> None:
        """Test frequency validation."""
        config = CWConfig(freq_range=(200.0, 1200.0))

        assert config.validate_frequency(600.0) is True
        assert config.validate_frequency(200.0) is True
        assert config.validate_frequency(1200.0) is True
        assert config.validate_frequency(100.0) is False
        assert config.validate_frequency(1500.0) is False

    def test_validate_wpm(self) -> None:
        """Test WPM validation."""
        config = CWConfig(min_wpm=5.0, max_wpm=55.0)

        assert config.validate_wpm(20.0) is True
        assert config.validate_wpm(5.0) is True
        assert config.validate_wpm(55.0) is True
        assert config.validate_wpm(2.0) is False
        assert config.validate_wpm(60.0) is False

    def test_invalid_sample_rate(self) -> None:
        """Test that invalid sample rate raises ValueError."""
        with pytest.raises(ValueError, match="Sample rate must be positive"):
            CWConfig(sample_rate=0)

        with pytest.raises(ValueError, match="Sample rate must be positive"):
            CWConfig(sample_rate=-1)

    def test_invalid_chunk_size(self) -> None:
        """Test that invalid chunk size raises ValueError."""
        with pytest.raises(ValueError, match="Chunk size must be positive"):
            CWConfig(chunk_size=0)

        with pytest.raises(ValueError, match="Chunk size must be positive"):
            CWConfig(chunk_size=-1)

    def test_invalid_freq_range(self) -> None:
        """Test that invalid frequency range raises ValueError."""
        with pytest.raises(ValueError, match="Minimum frequency must be non-negative"):
            CWConfig(freq_range=(-100.0, 1200.0))

        with pytest.raises(ValueError, match="Maximum frequency must be greater than minimum"):
            CWConfig(freq_range=(1200.0, 200.0))

        with pytest.raises(ValueError, match="Maximum frequency must be greater than minimum"):
            CWConfig(freq_range=(500.0, 500.0))

    def test_invalid_min_snr_db(self) -> None:
        """Test that invalid minimum SNR raises ValueError."""
        with pytest.raises(ValueError, match="Minimum SNR must be non-negative"):
            CWConfig(min_snr_db=-1.0)

    def test_invalid_filter_bandwidth(self) -> None:
        """Test that invalid filter bandwidth raises ValueError."""
        with pytest.raises(ValueError, match="Filter bandwidth must be positive"):
            CWConfig(filter_bandwidth=0.0)

        with pytest.raises(ValueError, match="Filter bandwidth must be positive"):
            CWConfig(filter_bandwidth=-10.0)

    def test_invalid_agc_target(self) -> None:
        """Test that invalid AGC target raises ValueError."""
        with pytest.raises(ValueError, match="AGC target must be in"):
            CWConfig(agc_target=-0.1)

        with pytest.raises(ValueError, match="AGC target must be in"):
            CWConfig(agc_target=1.5)

    def test_invalid_agc_attack_ms(self) -> None:
        """Test that invalid AGC attack time raises ValueError."""
        with pytest.raises(ValueError, match="AGC attack time must be positive"):
            CWConfig(agc_attack_ms=0.0)

        with pytest.raises(ValueError, match="AGC attack time must be positive"):
            CWConfig(agc_attack_ms=-1.0)

    def test_invalid_agc_release_ms(self) -> None:
        """Test that invalid AGC release time raises ValueError."""
        with pytest.raises(ValueError, match="AGC release time must be positive"):
            CWConfig(agc_release_ms=0.0)

        with pytest.raises(ValueError, match="AGC release time must be positive"):
            CWConfig(agc_release_ms=-1.0)

    def test_invalid_squelch_threshold(self) -> None:
        """Test that invalid squelch threshold raises ValueError."""
        with pytest.raises(ValueError, match="Squelch threshold must be in"):
            CWConfig(squelch_threshold=-0.1)

        with pytest.raises(ValueError, match="Squelch threshold must be in"):
            CWConfig(squelch_threshold=1.5)

    def test_invalid_squelch_hysteresis(self) -> None:
        """Test that invalid squelch hysteresis raises ValueError."""
        with pytest.raises(ValueError, match="Squelch hysteresis must be in"):
            CWConfig(squelch_hysteresis=-0.1)

        with pytest.raises(ValueError, match="Squelch hysteresis must be in"):
            CWConfig(squelch_hysteresis=1.5)

    def test_invalid_tone_threshold(self) -> None:
        """Test that invalid tone threshold raises ValueError."""
        with pytest.raises(ValueError, match="Tone threshold must be in"):
            CWConfig(tone_threshold=-0.1)

        with pytest.raises(ValueError, match="Tone threshold must be in"):
            CWConfig(tone_threshold=1.5)

    def test_invalid_initial_wpm(self) -> None:
        """Test that invalid initial WPM raises ValueError."""
        with pytest.raises(ValueError, match="Initial WPM must be positive"):
            CWConfig(initial_wpm=0.0)

        with pytest.raises(ValueError, match="Initial WPM must be positive"):
            CWConfig(initial_wpm=-1.0)

    def test_invalid_min_wpm(self) -> None:
        """Test that invalid minimum WPM raises ValueError."""
        with pytest.raises(ValueError, match="Minimum WPM must be positive"):
            CWConfig(min_wpm=0.0)

        with pytest.raises(ValueError, match="Minimum WPM must be positive"):
            CWConfig(min_wpm=-1.0)

    def test_invalid_max_wpm(self) -> None:
        """Test that invalid maximum WPM raises ValueError."""
        with pytest.raises(ValueError, match="Maximum WPM must be greater than minimum"):
            CWConfig(min_wpm=20.0, max_wpm=10.0)

        with pytest.raises(ValueError, match="Maximum WPM must be greater than minimum"):
            CWConfig(min_wpm=20.0, max_wpm=20.0)
