"""Unit tests for data models."""

import numpy as np
import pytest
from continuous_wave.models import (
    AudioSample,
    DecodedCharacter,
    MorseElement,
    MorseSymbol,
    SignalStats,
    TimingStats,
    ToneEvent,
)


class TestAudioSample:
    """Tests for AudioSample model."""

    def test_creation(self) -> None:
        """Test creating a valid AudioSample."""
        data = np.array([1.0, 2.0, 3.0], dtype=np.float32)
        sample = AudioSample(data=data, sample_rate=8000, timestamp=0.0)

        assert len(sample.data) == 3
        assert sample.sample_rate == 8000
        assert sample.timestamp == 0.0

    def test_duration_property(self) -> None:
        """Test duration calculation."""
        data = np.zeros(8000, dtype=np.float32)
        sample = AudioSample(data=data, sample_rate=8000, timestamp=0.0)

        assert sample.duration == 1.0  # 8000 samples at 8000 Hz = 1 second

    def test_num_samples_property(self) -> None:
        """Test num_samples property."""
        data = np.zeros(100, dtype=np.float32)
        sample = AudioSample(data=data, sample_rate=8000, timestamp=0.0)

        assert sample.num_samples == 100

    def test_invalid_sample_rate(self) -> None:
        """Test that invalid sample rate raises ValueError."""
        data = np.array([1.0, 2.0, 3.0], dtype=np.float32)

        with pytest.raises(ValueError, match="Sample rate must be positive"):
            AudioSample(data=data, sample_rate=0, timestamp=0.0)

        with pytest.raises(ValueError, match="Sample rate must be positive"):
            AudioSample(data=data, sample_rate=-1, timestamp=0.0)

    def test_invalid_timestamp(self) -> None:
        """Test that negative timestamp raises ValueError."""
        data = np.array([1.0, 2.0, 3.0], dtype=np.float32)

        with pytest.raises(ValueError, match="Timestamp must be non-negative"):
            AudioSample(data=data, sample_rate=8000, timestamp=-1.0)

    def test_empty_data(self) -> None:
        """Test that empty data raises ValueError."""
        data = np.array([], dtype=np.float32)

        with pytest.raises(ValueError, match="Audio data cannot be empty"):
            AudioSample(data=data, sample_rate=8000, timestamp=0.0)


class TestToneEvent:
    """Tests for ToneEvent model."""

    def test_creation(self) -> None:
        """Test creating a valid ToneEvent."""
        event = ToneEvent(is_tone_on=True, timestamp=1.5, amplitude=0.8)

        assert event.is_tone_on is True
        assert event.timestamp == 1.5
        assert event.amplitude == 0.8

    def test_invalid_timestamp(self) -> None:
        """Test that negative timestamp raises ValueError."""
        with pytest.raises(ValueError, match="Timestamp must be non-negative"):
            ToneEvent(is_tone_on=True, timestamp=-1.0, amplitude=0.8)

    def test_invalid_amplitude(self) -> None:
        """Test that negative amplitude raises ValueError."""
        with pytest.raises(ValueError, match="Amplitude must be non-negative"):
            ToneEvent(is_tone_on=True, timestamp=1.0, amplitude=-0.5)


class TestMorseElement:
    """Tests for MorseElement enum."""

    def test_values(self) -> None:
        """Test that MorseElement has correct values."""
        assert MorseElement.DOT.value == "."
        assert MorseElement.DASH.value == "-"
        assert MorseElement.ELEMENT_GAP.value == " "
        assert MorseElement.CHAR_GAP.value == "  "
        assert MorseElement.WORD_GAP.value == "   "


class TestMorseSymbol:
    """Tests for MorseSymbol model."""

    def test_creation(self) -> None:
        """Test creating a valid MorseSymbol."""
        symbol = MorseSymbol(element=MorseElement.DOT, duration=0.05, timestamp=1.0)

        assert symbol.element == MorseElement.DOT
        assert symbol.duration == 0.05
        assert symbol.timestamp == 1.0

    def test_invalid_duration(self) -> None:
        """Test that negative duration raises ValueError."""
        with pytest.raises(ValueError, match="Duration must be non-negative"):
            MorseSymbol(element=MorseElement.DOT, duration=-0.1, timestamp=1.0)

    def test_invalid_timestamp(self) -> None:
        """Test that negative timestamp raises ValueError."""
        with pytest.raises(ValueError, match="Timestamp must be non-negative"):
            MorseSymbol(element=MorseElement.DOT, duration=0.05, timestamp=-1.0)


class TestDecodedCharacter:
    """Tests for DecodedCharacter model."""

    def test_creation(self) -> None:
        """Test creating a valid DecodedCharacter."""
        char = DecodedCharacter(char="A", confidence=1.0, timestamp=2.0, morse_pattern=".-")

        assert char.char == "A"
        assert char.confidence == 1.0
        assert char.timestamp == 2.0
        assert char.morse_pattern == ".-"

    def test_invalid_confidence(self) -> None:
        """Test that invalid confidence raises ValueError."""
        with pytest.raises(ValueError, match="Confidence must be in"):
            DecodedCharacter(char="A", confidence=1.5, timestamp=2.0, morse_pattern=".-")

        with pytest.raises(ValueError, match="Confidence must be in"):
            DecodedCharacter(char="A", confidence=-0.1, timestamp=2.0, morse_pattern=".-")

    def test_invalid_timestamp(self) -> None:
        """Test that negative timestamp raises ValueError."""
        with pytest.raises(ValueError, match="Timestamp must be non-negative"):
            DecodedCharacter(char="A", confidence=1.0, timestamp=-1.0, morse_pattern=".-")

    def test_invalid_char_length(self) -> None:
        """Test that multi-character string raises ValueError."""
        with pytest.raises(ValueError, match="Character must be a single character"):
            DecodedCharacter(char="AB", confidence=1.0, timestamp=2.0, morse_pattern=".-")


class TestTimingStats:
    """Tests for TimingStats model."""

    def test_creation(self) -> None:
        """Test creating a valid TimingStats."""
        stats = TimingStats(dot_duration=0.06, wpm=20.0, confidence=0.9, num_samples=10)

        assert stats.dot_duration == 0.06
        assert stats.wpm == 20.0
        assert stats.confidence == 0.9
        assert stats.num_samples == 10

    def test_from_dot_duration(self) -> None:
        """Test creating TimingStats from dot duration."""
        # For 20 WPM: dot_duration = 1200 / 20 / 1000 = 0.06 seconds
        stats = TimingStats.from_dot_duration(0.06, num_samples=10)

        assert stats.dot_duration == 0.06
        assert abs(stats.wpm - 20.0) < 0.01
        assert stats.confidence == 1.0  # 10 samples = 100% confidence
        assert stats.num_samples == 10

    def test_from_dot_duration_confidence(self) -> None:
        """Test confidence calculation from number of samples."""
        stats = TimingStats.from_dot_duration(0.06, num_samples=5)
        assert stats.confidence == 0.5  # 5 samples = 50% confidence

        stats = TimingStats.from_dot_duration(0.06, num_samples=0)
        assert stats.confidence == 0.0  # No samples = 0% confidence

        stats = TimingStats.from_dot_duration(0.06, num_samples=20)
        assert stats.confidence == 1.0  # Capped at 1.0

    def test_invalid_dot_duration(self) -> None:
        """Test that invalid dot duration raises ValueError."""
        with pytest.raises(ValueError, match="Dot duration must be positive"):
            TimingStats(dot_duration=0.0, wpm=20.0, confidence=0.9, num_samples=10)

        with pytest.raises(ValueError, match="Dot duration must be positive"):
            TimingStats(dot_duration=-0.1, wpm=20.0, confidence=0.9, num_samples=10)

    def test_invalid_wpm(self) -> None:
        """Test that invalid WPM raises ValueError."""
        with pytest.raises(ValueError, match="WPM must be positive"):
            TimingStats(dot_duration=0.06, wpm=0.0, confidence=0.9, num_samples=10)

    def test_invalid_confidence(self) -> None:
        """Test that invalid confidence raises ValueError."""
        with pytest.raises(ValueError, match="Confidence must be in"):
            TimingStats(dot_duration=0.06, wpm=20.0, confidence=1.5, num_samples=10)

    def test_invalid_num_samples(self) -> None:
        """Test that negative num_samples raises ValueError."""
        with pytest.raises(ValueError, match="Number of samples must be non-negative"):
            TimingStats(dot_duration=0.06, wpm=20.0, confidence=0.9, num_samples=-1)


class TestSignalStats:
    """Tests for SignalStats model."""

    def test_creation(self) -> None:
        """Test creating a valid SignalStats."""
        stats = SignalStats(frequency=600.0, snr_db=10.0, power=0.5, timestamp=1.0)

        assert stats.frequency == 600.0
        assert stats.snr_db == 10.0
        assert stats.power == 0.5
        assert stats.timestamp == 1.0

    def test_invalid_frequency(self) -> None:
        """Test that negative frequency raises ValueError."""
        with pytest.raises(ValueError, match="Frequency must be non-negative"):
            SignalStats(frequency=-100.0, snr_db=10.0, power=0.5, timestamp=1.0)

    def test_invalid_power(self) -> None:
        """Test that negative power raises ValueError."""
        with pytest.raises(ValueError, match="Power must be non-negative"):
            SignalStats(frequency=600.0, snr_db=10.0, power=-0.1, timestamp=1.0)

    def test_invalid_timestamp(self) -> None:
        """Test that negative timestamp raises ValueError."""
        with pytest.raises(ValueError, match="Timestamp must be non-negative"):
            SignalStats(frequency=600.0, snr_db=10.0, power=0.5, timestamp=-1.0)
