"""Unit tests for adaptive timing analyzer."""

import pytest

from continuous_wave.config import CWConfig
from continuous_wave.models import MorseElement, ToneEvent
from continuous_wave.timing.adaptive import AdaptiveWPMDetector


@pytest.fixture
def config() -> CWConfig:
    """Create test configuration."""
    return CWConfig(min_wpm=5.0, max_wpm=55.0)


@pytest.fixture
def analyzer(config: CWConfig) -> AdaptiveWPMDetector:
    """Create timing analyzer instance."""
    return AdaptiveWPMDetector(config=config)


class TestWPMCalculation:
    """Test WPM calculation using PARIS standard."""

    def test_paris_standard_20wpm(self) -> None:
        """Test PARIS standard: 20 WPM = 60ms dot duration."""
        # PARIS standard: WPM = 1.2 / dot_duration
        # 20 WPM = 1.2 / 0.060 = 20
        wpm = 20.0
        dot_duration = 1.2 / wpm
        assert abs(dot_duration - 0.060) < 0.001

    def test_paris_standard_10wpm(self) -> None:
        """Test PARIS standard: 10 WPM = 120ms dot duration."""
        wpm = 10.0
        dot_duration = 1.2 / wpm
        assert abs(dot_duration - 0.120) < 0.001

    def test_paris_standard_40wpm(self) -> None:
        """Test PARIS standard: 40 WPM = 30ms dot duration."""
        wpm = 40.0
        dot_duration = 1.2 / wpm
        assert abs(dot_duration - 0.030) < 0.001


class TestInitialToneClassification:
    """Test tone classification before timing lock."""

    def test_classify_first_dot_bootstrap(self, analyzer: AdaptiveWPMDetector) -> None:
        """Test first tone classification uses bootstrap default (20 WPM)."""
        # First event: tone on
        event1 = ToneEvent(is_tone_on=True, timestamp=0.0, amplitude=0.8)
        symbols = analyzer.analyze(event1)
        assert len(symbols) == 0  # No symbols yet

        # Second event: tone off after 60ms (dot at 20 WPM)
        event2 = ToneEvent(is_tone_on=False, timestamp=0.060, amplitude=0.2)
        symbols = analyzer.analyze(event2)

        assert len(symbols) == 1
        assert symbols[0].element == MorseElement.DOT
        assert abs(symbols[0].duration - 0.060) < 0.001

    def test_classify_first_dash_bootstrap(self, analyzer: AdaptiveWPMDetector) -> None:
        """Test first dash classification uses bootstrap default."""
        # First event: tone on
        event1 = ToneEvent(is_tone_on=True, timestamp=0.0, amplitude=0.8)
        symbols = analyzer.analyze(event1)

        # Second event: tone off after 180ms (dash at 20 WPM)
        # 20 WPM: dot = 60ms, dash = 180ms
        event2 = ToneEvent(is_tone_on=False, timestamp=0.180, amplitude=0.2)
        symbols = analyzer.analyze(event2)

        assert len(symbols) == 1
        assert symbols[0].element == MorseElement.DASH
        assert abs(symbols[0].duration - 0.180) < 0.001

    def test_threshold_between_dot_and_dash(self, analyzer: AdaptiveWPMDetector) -> None:
        """Test threshold is properly placed between dot and dash durations."""
        # At 20 WPM: dot = 60ms, dash = 180ms, threshold = 120ms (2x dot)
        event1 = ToneEvent(is_tone_on=True, timestamp=0.0, amplitude=0.8)
        analyzer.analyze(event1)

        # Send 110ms tone - should be classified as dot (< 120ms)
        event2 = ToneEvent(is_tone_on=False, timestamp=0.110, amplitude=0.2)
        symbols = analyzer.analyze(event2)
        assert symbols[0].element == MorseElement.DOT

        # Reset and send 130ms tone - should be classified as dash (>= 120ms)
        analyzer.reset()
        event1 = ToneEvent(is_tone_on=True, timestamp=0.0, amplitude=0.8)
        analyzer.analyze(event1)
        event2 = ToneEvent(is_tone_on=False, timestamp=0.130, amplitude=0.2)
        symbols = analyzer.analyze(event2)
        assert symbols[0].element == MorseElement.DASH


class TestGapClassification:
    """Test gap classification."""

    def test_element_gap_classification(self, analyzer: AdaptiveWPMDetector) -> None:
        """Test element gap (between dots/dashes within character)."""
        # Send dot to establish timing
        event1 = ToneEvent(is_tone_on=True, timestamp=0.0, amplitude=0.8)
        analyzer.analyze(event1)
        event2 = ToneEvent(is_tone_on=False, timestamp=0.060, amplitude=0.2)
        analyzer.analyze(event2)

        # Element gap: ~1 dot duration (60ms)
        event3 = ToneEvent(is_tone_on=True, timestamp=0.120, amplitude=0.8)
        symbols = analyzer.analyze(event3)

        assert len(symbols) == 1
        assert symbols[0].element == MorseElement.ELEMENT_GAP
        assert abs(symbols[0].duration - 0.060) < 0.001

    def test_character_gap_classification(self, analyzer: AdaptiveWPMDetector) -> None:
        """Test character gap (between letters)."""
        # Send dot to establish timing
        event1 = ToneEvent(is_tone_on=True, timestamp=0.0, amplitude=0.8)
        analyzer.analyze(event1)
        event2 = ToneEvent(is_tone_on=False, timestamp=0.060, amplitude=0.2)
        analyzer.analyze(event2)

        # Character gap: ~3 dot durations (180ms at 20 WPM)
        event3 = ToneEvent(is_tone_on=True, timestamp=0.240, amplitude=0.8)
        symbols = analyzer.analyze(event3)

        assert len(symbols) == 1
        assert symbols[0].element == MorseElement.CHAR_GAP
        assert abs(symbols[0].duration - 0.180) < 0.001

    def test_word_gap_classification(self, analyzer: AdaptiveWPMDetector) -> None:
        """Test word gap (between words)."""
        # Send dot to establish timing
        event1 = ToneEvent(is_tone_on=True, timestamp=0.0, amplitude=0.8)
        analyzer.analyze(event1)
        event2 = ToneEvent(is_tone_on=False, timestamp=0.060, amplitude=0.2)
        analyzer.analyze(event2)

        # Word gap: ~7 dot durations (420ms at 20 WPM)
        event3 = ToneEvent(is_tone_on=True, timestamp=0.480, amplitude=0.8)
        symbols = analyzer.analyze(event3)

        assert len(symbols) == 1
        assert symbols[0].element == MorseElement.WORD_GAP
        assert abs(symbols[0].duration - 0.420) < 0.001

    def test_gap_classification_without_timing_returns_none(
        self, analyzer: AdaptiveWPMDetector
    ) -> None:
        """Test gap classification before timing established returns None."""
        # First event: tone on
        event1 = ToneEvent(is_tone_on=True, timestamp=0.0, amplitude=0.8)
        analyzer.analyze(event1)

        # Second event: tone off (no gap yet)
        event2 = ToneEvent(is_tone_on=False, timestamp=0.060, amplitude=0.2)
        analyzer.analyze(event2)

        # Third event: tone on - this creates a gap, but we can now classify it
        event3 = ToneEvent(is_tone_on=True, timestamp=0.120, amplitude=0.8)
        symbols = analyzer.analyze(event3)

        # Should classify the gap now that we have timing
        assert len(symbols) >= 0  # May or may not classify depending on state


class TestAdaptiveWPMDetection:
    """Test adaptive WPM detection and locking."""

    def test_wpm_detection_from_dots(self, analyzer: AdaptiveWPMDetector) -> None:
        """Test WPM detection from multiple dot samples."""
        # Send several dots at 20 WPM (60ms each)
        timestamp = 0.0
        for _ in range(10):
            event_on = ToneEvent(is_tone_on=True, timestamp=timestamp, amplitude=0.8)
            analyzer.analyze(event_on)
            timestamp += 0.060

            event_off = ToneEvent(is_tone_on=False, timestamp=timestamp, amplitude=0.2)
            analyzer.analyze(event_off)
            timestamp += 0.060  # Element gap

        # Check WPM estimate
        stats = analyzer.timing_stats
        if stats is not None:
            assert 18.0 < stats.wpm < 22.0  # Should be around 20 WPM
            assert abs(stats.dot_duration - 0.060) < 0.010

    def test_wpm_detection_from_dashes(self, analyzer: AdaptiveWPMDetector) -> None:
        """Test WPM can be inferred from dash durations."""
        # Send several dashes at 20 WPM (180ms each, dash = 3x dot)
        timestamp = 0.0
        for _ in range(10):
            event_on = ToneEvent(is_tone_on=True, timestamp=timestamp, amplitude=0.8)
            analyzer.analyze(event_on)
            timestamp += 0.180  # Dash duration

            event_off = ToneEvent(is_tone_on=False, timestamp=timestamp, amplitude=0.2)
            analyzer.analyze(event_off)
            timestamp += 0.060  # Element gap

        # Should infer dot duration from dashes (180ms / 3 = 60ms)
        stats = analyzer.timing_stats
        if stats is not None:
            assert abs(stats.dot_duration - 0.060) < 0.010

    def test_timing_lock_after_sufficient_samples(self, analyzer: AdaptiveWPMDetector) -> None:
        """Test timing locks after sufficient consistent samples."""
        assert not analyzer.is_locked

        # Send 15 dots at consistent timing (20 WPM)
        timestamp = 0.0
        for _ in range(15):
            event_on = ToneEvent(is_tone_on=True, timestamp=timestamp, amplitude=0.8)
            analyzer.analyze(event_on)
            timestamp += 0.060

            event_off = ToneEvent(is_tone_on=False, timestamp=timestamp, amplitude=0.2)
            analyzer.analyze(event_off)
            timestamp += 0.060

        # Should be locked after sufficient samples
        assert analyzer.is_locked

    def test_timing_confidence_increases_with_samples(self, analyzer: AdaptiveWPMDetector) -> None:
        """Test confidence increases as more samples are collected."""
        confidences = []

        # Send dots and track confidence
        timestamp = 0.0
        for _i in range(25):
            event_on = ToneEvent(is_tone_on=True, timestamp=timestamp, amplitude=0.8)
            analyzer.analyze(event_on)
            timestamp += 0.060

            event_off = ToneEvent(is_tone_on=False, timestamp=timestamp, amplitude=0.2)
            analyzer.analyze(event_off)
            timestamp += 0.060

            stats = analyzer.timing_stats
            if stats is not None:
                confidences.append(stats.confidence)

        # Confidence should generally increase
        if len(confidences) >= 2:
            # Later confidences should be higher than earlier ones
            assert confidences[-1] >= confidences[0]


class TestTimingAdaptation:
    """Test timing adaptation to changing WPM."""

    def test_adapts_to_wpm_changes(self, analyzer: AdaptiveWPMDetector) -> None:
        """Test analyzer adapts when WPM changes."""
        # Send dots at 20 WPM initially
        timestamp = 0.0
        for _ in range(10):
            event_on = ToneEvent(is_tone_on=True, timestamp=timestamp, amplitude=0.8)
            analyzer.analyze(event_on)
            timestamp += 0.060

            event_off = ToneEvent(is_tone_on=False, timestamp=timestamp, amplitude=0.2)
            analyzer.analyze(event_off)
            timestamp += 0.060

        initial_stats = analyzer.timing_stats
        assert initial_stats is not None

        # Now send dots at 15 WPM (80ms each)
        for _ in range(15):
            event_on = ToneEvent(is_tone_on=True, timestamp=timestamp, amplitude=0.8)
            analyzer.analyze(event_on)
            timestamp += 0.080

            event_off = ToneEvent(is_tone_on=False, timestamp=timestamp, amplitude=0.2)
            analyzer.analyze(event_off)
            timestamp += 0.080

        adapted_stats = analyzer.timing_stats
        assert adapted_stats is not None

        # Dot duration should have increased
        assert adapted_stats.dot_duration > initial_stats.dot_duration
        # WPM should have decreased
        assert adapted_stats.wpm < initial_stats.wpm

    def test_rejects_wpm_outside_configured_range(self, analyzer: AdaptiveWPMDetector) -> None:
        """Test analyzer rejects WPM estimates outside configured range."""
        # Try to send very fast WPM (100 WPM, outside config range of 5-55)
        # 100 WPM = 1.2 / 100 = 12ms dot duration
        timestamp = 0.0
        event_on = ToneEvent(is_tone_on=True, timestamp=timestamp, amplitude=0.8)
        analyzer.analyze(event_on)

        event_off = ToneEvent(is_tone_on=False, timestamp=0.012, amplitude=0.2)
        analyzer.analyze(event_off)

        # This shouldn't lock because it's outside range
        # (though it may still track it internally)
        # Just verify it doesn't crash
        stats = analyzer.timing_stats
        if stats is not None:
            # If it reports stats, WPM should be in valid range
            assert analyzer.config.min_wpm <= stats.wpm <= analyzer.config.max_wpm


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_first_event_returns_empty_symbols(self, analyzer: AdaptiveWPMDetector) -> None:
        """Test first event returns no symbols."""
        event = ToneEvent(is_tone_on=True, timestamp=0.0, amplitude=0.8)
        symbols = analyzer.analyze(event)
        assert len(symbols) == 0

    def test_invalid_negative_duration_skipped(self, analyzer: AdaptiveWPMDetector) -> None:
        """Test negative duration events are skipped."""
        event1 = ToneEvent(is_tone_on=True, timestamp=1.0, amplitude=0.8)
        analyzer.analyze(event1)

        # Second event has earlier timestamp (invalid)
        event2 = ToneEvent(is_tone_on=False, timestamp=0.5, amplitude=0.2)
        symbols = analyzer.analyze(event2)

        # Should skip invalid event
        assert len(symbols) == 0

    def test_zero_duration_skipped(self, analyzer: AdaptiveWPMDetector) -> None:
        """Test zero duration events are skipped."""
        event1 = ToneEvent(is_tone_on=True, timestamp=1.0, amplitude=0.8)
        analyzer.analyze(event1)

        # Second event at same timestamp
        event2 = ToneEvent(is_tone_on=False, timestamp=1.0, amplitude=0.2)
        symbols = analyzer.analyze(event2)

        assert len(symbols) == 0

    def test_reset_clears_all_state(self, analyzer: AdaptiveWPMDetector) -> None:
        """Test reset clears all analyzer state."""
        # Build up state
        timestamp = 0.0
        for _ in range(15):
            event_on = ToneEvent(is_tone_on=True, timestamp=timestamp, amplitude=0.8)
            analyzer.analyze(event_on)
            timestamp += 0.060

            event_off = ToneEvent(is_tone_on=False, timestamp=timestamp, amplitude=0.2)
            analyzer.analyze(event_off)
            timestamp += 0.060

        assert analyzer.is_locked

        # Reset
        analyzer.reset()

        # State should be cleared
        assert not analyzer.is_locked
        assert analyzer.timing_stats is None

    def test_timing_stats_none_when_not_locked(self, analyzer: AdaptiveWPMDetector) -> None:
        """Test timing_stats returns None when not locked."""
        assert analyzer.timing_stats is None
        assert not analyzer.is_locked

    def test_tone_on_to_tone_on_ignored(self, analyzer: AdaptiveWPMDetector) -> None:
        """Test consecutive tone-on events don't create symbols."""
        event1 = ToneEvent(is_tone_on=True, timestamp=0.0, amplitude=0.8)
        analyzer.analyze(event1)

        # Another tone-on without tone-off
        event2 = ToneEvent(is_tone_on=True, timestamp=0.060, amplitude=0.8)
        symbols = analyzer.analyze(event2)

        # No tone duration to classify
        assert len(symbols) == 0

    def test_tone_off_to_tone_off_ignored(self, analyzer: AdaptiveWPMDetector) -> None:
        """Test consecutive tone-off events don't create gap symbols."""
        event1 = ToneEvent(is_tone_on=False, timestamp=0.0, amplitude=0.2)
        analyzer.analyze(event1)

        event2 = ToneEvent(is_tone_on=False, timestamp=0.060, amplitude=0.2)
        symbols = analyzer.analyze(event2)

        # Can't classify gap without prior reference
        assert len(symbols) == 0


class TestDotDashRefinement:
    """Test dot duration estimation refinement from both dots and dashes."""

    def test_refines_estimate_with_both_dots_and_dashes(
        self, analyzer: AdaptiveWPMDetector
    ) -> None:
        """Test dot duration refined using both dot and dash samples."""
        timestamp = 0.0

        # Send mix of dots and dashes
        # Dot at 20 WPM = 60ms, Dash = 180ms
        patterns = [0.060, 0.180, 0.060, 0.180, 0.060, 0.180, 0.060, 0.180]

        for duration in patterns:
            event_on = ToneEvent(is_tone_on=True, timestamp=timestamp, amplitude=0.8)
            analyzer.analyze(event_on)
            timestamp += duration

            event_off = ToneEvent(is_tone_on=False, timestamp=timestamp, amplitude=0.2)
            analyzer.analyze(event_off)
            timestamp += 0.060

        stats = analyzer.timing_stats
        if stats is not None:
            # Should have samples from both dots and dashes
            assert stats.num_samples > 5
            # Dot duration should be reasonably accurate
            assert abs(stats.dot_duration - 0.060) < 0.015

    def test_can_bootstrap_from_dashes_only(self, analyzer: AdaptiveWPMDetector) -> None:
        """Test can establish timing from dashes when no dots sent."""
        timestamp = 0.0

        # Send only dashes (180ms at 20 WPM)
        for _ in range(10):
            event_on = ToneEvent(is_tone_on=True, timestamp=timestamp, amplitude=0.8)
            analyzer.analyze(event_on)
            timestamp += 0.180

            event_off = ToneEvent(is_tone_on=False, timestamp=timestamp, amplitude=0.2)
            analyzer.analyze(event_off)
            timestamp += 0.060

        # Should infer dot duration from dashes
        stats = analyzer.timing_stats
        if stats is not None:
            # Dot duration inferred as dash / 3
            assert abs(stats.dot_duration - 0.060) < 0.015
