"""Adaptive timing analysis for CW signals."""

from collections import deque
from dataclasses import dataclass, field

from continuous_wave.config import CWConfig
from continuous_wave.models import MorseElement, MorseSymbol, TimingStats, ToneEvent
from continuous_wave.protocols import TimingAnalyzer


@dataclass
class AdaptiveWPMDetector(TimingAnalyzer):
    """Adaptive WPM detector using timing statistics.

    Automatically detects sending speed (WPM) and classifies
    tone/gap durations as dots, dashes, or gaps.

    Uses PARIS standard: 1 WPM = 1.2 second dot duration
    """

    config: CWConfig
    _last_event: ToneEvent | None = field(default=None, init=False)
    _dot_durations: deque[float] = field(default_factory=lambda: deque(maxlen=20), init=False)
    _dash_durations: deque[float] = field(default_factory=lambda: deque(maxlen=20), init=False)
    _estimated_dot_duration: float | None = field(default=None, init=False)
    _estimated_wpm: float | None = field(default=None, init=False)
    _lock_count: int = field(default=0, init=False)
    _required_lock_samples: int = field(default=5, init=False)  # Reduced from 10 to lock faster
    _buffered_events: deque[ToneEvent] = field(
        default_factory=lambda: deque(maxlen=100), init=False
    )  # Buffer events until locked
    _has_emitted_buffered: bool = field(default=False, init=False)  # Track if buffer was replayed

    def analyze(self, event: ToneEvent) -> list[MorseSymbol]:
        """Analyze tone event and generate Morse symbols.

        Args:
            event: Tone on/off event to analyze

        Returns:
            List of MorseSymbol objects (may be empty if analysis incomplete)
        """
        symbols: list[MorseSymbol] = []

        # Check if we just locked and need to replay buffered events
        if self.is_locked and not self._has_emitted_buffered and len(self._buffered_events) > 1:
            # Replay all buffered events with correct timing
            symbols.extend(self._replay_buffered_events())
            self._has_emitted_buffered = True
            # Don't process current event yet - it will be added to buffer below
            # and processed normally next time
            self._buffered_events.append(event)
            return symbols

        # Buffer events until we're locked
        if not self.is_locked:
            self._buffered_events.append(event)

        if self._last_event is None:
            # First event - just record it
            self._last_event = event
            return symbols

        # Calculate duration since last event
        duration = event.timestamp - self._last_event.timestamp

        if duration <= 0:
            # Invalid timing - skip
            return symbols

        if self._last_event.is_tone_on and not event.is_tone_on:
            # Tone turned off - this was a tone duration (dot or dash)
            symbol = self._classify_tone(duration)
            if symbol is not None:
                # Only emit symbols after we're locked (for regular processing)
                # Buffered events will be replayed when we lock
                if self.is_locked and self._has_emitted_buffered:
                    symbols.append(symbol)

        elif not self._last_event.is_tone_on and event.is_tone_on:
            # Tone turned on - previous duration was a gap
            gap_symbol = self._classify_gap(duration)
            if gap_symbol is not None:
                # Only emit symbols after we're locked
                if self.is_locked and self._has_emitted_buffered:
                    symbols.append(gap_symbol)

        self._last_event = event
        return symbols

    @property
    def timing_stats(self) -> TimingStats | None:
        """Get current timing statistics.

        Returns:
            TimingStats if locked, None otherwise
        """
        if not self.is_locked:
            return None

        confidence = min(1.0, self._lock_count / (self._required_lock_samples * 2))

        return TimingStats(
            dot_duration=self._estimated_dot_duration or 0.0,
            wpm=self._estimated_wpm or 0.0,
            confidence=confidence,
            num_samples=len(self._dot_durations) + len(self._dash_durations),
        )

    @property
    def is_locked(self) -> bool:
        """Check if timing is locked.

        Returns:
            True if WPM estimation is stable
        """
        return (
            self._lock_count >= self._required_lock_samples
            and self._estimated_dot_duration is not None
        )

    def reset(self) -> None:
        """Reset timing analyzer state."""
        self._last_event = None
        self._dot_durations.clear()
        self._dash_durations.clear()
        self._estimated_dot_duration = None
        self._estimated_wpm = None
        self._lock_count = 0
        self._buffered_events.clear()
        self._has_emitted_buffered = False

    def _replay_buffered_events(self) -> list[MorseSymbol]:
        """Replay buffered tone events with correct timing.

        This is called once when timing locks to re-analyze all buffered
        events with the now-known timing parameters.

        Returns:
            List of MorseSymbol objects from re-analyzing buffered events
        """
        symbols: list[MorseSymbol] = []

        if len(self._buffered_events) < 2:
            return symbols

        # Re-analyze all buffered events with correct timing
        prev_event = None
        last_valid_tone = False  # Track if last emitted symbol was a valid tone

        for event in self._buffered_events:
            if prev_event is None:
                prev_event = event
                continue

            duration = event.timestamp - prev_event.timestamp

            if duration <= 0:
                prev_event = event
                continue

            if prev_event.is_tone_on and not event.is_tone_on:
                # Tone duration (dot or dash)
                # Re-classify with current timing
                symbol = self._reclassify_tone(duration)
                if symbol is not None:
                    symbols.append(symbol)
                    last_valid_tone = True
                else:
                    last_valid_tone = False

            elif not prev_event.is_tone_on and event.is_tone_on:
                # Gap duration - only emit if we've had a valid tone before
                if last_valid_tone:
                    gap_symbol = self._classify_gap(duration)
                    if gap_symbol is not None:
                        symbols.append(gap_symbol)

            prev_event = event

        return symbols

    def _reclassify_tone(self, duration: float) -> MorseSymbol | None:
        """Re-classify a tone duration without updating statistics.

        This is used when replaying buffered events - we use the current
        timing estimate but don't add to statistics (already added during
        initial pass).

        Args:
            duration: Tone duration in seconds

        Returns:
            MorseSymbol for dot or dash, or None if it's an artifact
        """
        if self._estimated_dot_duration is None:
            return None

        # Filter out very short tones that are likely artifacts
        # Use same threshold as in _update_timing_estimate (30ms)
        if duration < 0.030:
            return None

        threshold = self._estimated_dot_duration * 2.0

        if duration < threshold:
            return MorseSymbol(
                element=MorseElement.DOT,
                duration=duration,
                timestamp=0.0,
            )
        else:
            return MorseSymbol(
                element=MorseElement.DASH,
                duration=duration,
                timestamp=0.0,
            )

    def _classify_tone(self, duration: float) -> MorseSymbol | None:
        """Classify a tone duration as dot or dash.

        Args:
            duration: Tone duration in seconds

        Returns:
            MorseSymbol for dot or dash, or None if uncertain
        """
        if self._estimated_dot_duration is None:
            # No timing reference yet - bootstrap using config defaults
            # Assume mid-range WPM (20 WPM = 60ms dot duration)
            default_wpm = 20.0
            default_dot = 1.2 / default_wpm  # PARIS standard

            # Classify based on default threshold
            threshold = default_dot * 2.0  # Dots < 2x, dashes >= 2x

            if duration < threshold:
                self._dot_durations.append(duration)
                self._update_timing_estimate()
                return MorseSymbol(
                    element=MorseElement.DOT,
                    duration=duration,
                    timestamp=0.0,  # Will be set by pipeline
                )
            else:
                self._dash_durations.append(duration)
                self._update_timing_estimate()
                return MorseSymbol(
                    element=MorseElement.DASH,
                    duration=duration,
                    timestamp=0.0,
                )
        else:
            # Use established timing reference
            # Standard: dash = 3x dot duration
            threshold = self._estimated_dot_duration * 2.0  # Midpoint between dot and dash

            if duration < threshold:
                # It's a dot
                self._dot_durations.append(duration)
                self._update_timing_estimate()
                return MorseSymbol(
                    element=MorseElement.DOT,
                    duration=duration,
                    timestamp=0.0,
                )
            else:
                # It's a dash
                self._dash_durations.append(duration)
                self._update_timing_estimate()
                return MorseSymbol(
                    element=MorseElement.DASH,
                    duration=duration,
                    timestamp=0.0,
                )

    def _classify_gap(self, duration: float) -> MorseSymbol | None:
        """Classify a gap duration.

        Args:
            duration: Gap duration in seconds

        Returns:
            MorseSymbol for gap type, or None if too short
        """
        if self._estimated_dot_duration is None:
            # Can't classify gaps without timing reference
            return None

        # Standard gaps:
        # - Element gap (between dots/dashes): 1 dot duration
        # - Character gap: 3 dot durations
        # - Word gap: 7 dot durations

        if duration < self._estimated_dot_duration * 2.0:
            # Element gap
            return MorseSymbol(
                element=MorseElement.ELEMENT_GAP,
                duration=duration,
                timestamp=0.0,
            )
        elif duration < self._estimated_dot_duration * 5.0:
            # Character gap (midpoint between 3 and 7)
            return MorseSymbol(
                element=MorseElement.CHAR_GAP,
                duration=duration,
                timestamp=0.0,
            )
        else:
            # Word gap
            return MorseSymbol(
                element=MorseElement.WORD_GAP,
                duration=duration,
                timestamp=0.0,
            )

    def _update_timing_estimate(self) -> None:
        """Update WPM and dot duration estimates from collected samples."""
        if not self._dot_durations and not self._dash_durations:
            return

        # Require minimum samples before establishing initial timing
        # This prevents early artifacts from corrupting the timing estimate
        # We need at least 2 samples, with preference for having both dots and dashes
        if self._estimated_dot_duration is None:
            total_samples = len(self._dot_durations) + len(self._dash_durations)
            # Require at least 2 samples total, or 2 of the same type
            # This allows faster locking while still filtering out single bad samples
            has_multiple_dots = len(self._dot_durations) >= 2
            has_multiple_dashes = len(self._dash_durations) >= 2
            has_mixed = len(self._dot_durations) >= 1 and len(self._dash_durations) >= 1

            if not (has_multiple_dots or has_multiple_dashes or (has_mixed and total_samples >= 2)):
                # Not enough samples yet to establish timing
                return

        # Filter outliers before calculating timing
        # Use adaptive filtering based on the distribution of samples
        # This is more robust than fixed thresholds
        def filter_outliers(durations: list[float]) -> list[float]:
            if len(durations) < 3:
                # Not enough samples for robust filtering, use minimal threshold
                return [d for d in durations if 0.025 <= d <= 0.600]

            sorted_durations = sorted(durations)
            # Use median and IQR for outlier detection
            median = sorted_durations[len(sorted_durations) // 2]
            q1 = sorted_durations[len(sorted_durations) // 4]
            q3 = sorted_durations[(3 * len(sorted_durations)) // 4]
            iqr = q3 - q1

            # Filter out values more than 1.5*IQR below Q1 or above Q3
            # This removes extreme outliers while keeping the core distribution
            lower_bound = max(0.025, q1 - 1.5 * iqr)
            upper_bound = min(0.600, q3 + 1.5 * iqr)

            # Also filter out values less than 50% of median (likely artifacts)
            lower_bound = max(lower_bound, median * 0.5)

            return [d for d in durations if lower_bound <= d <= upper_bound]

        filtered_dots = filter_outliers(list(self._dot_durations))
        filtered_dashes = filter_outliers(list(self._dash_durations))

        # Calculate median dot duration from dot samples
        if filtered_dots:
            dot_estimate = sorted(filtered_dots)[len(filtered_dots) // 2]
        elif filtered_dashes:
            # Infer from dash durations (dash = 3x dot)
            dash_estimate = sorted(filtered_dashes)[len(filtered_dashes) // 2]
            dot_estimate = dash_estimate / 3.0
        else:
            # No valid samples after filtering
            return

        # If we have dash durations, refine estimate
        if filtered_dashes and filtered_dots:
            dash_estimate = sorted(filtered_dashes)[len(filtered_dashes) // 2]
            dot_from_dash = dash_estimate / 3.0

            # Weighted average (prefer dots as they're more consistent)
            dot_estimate = 0.7 * dot_estimate + 0.3 * dot_from_dash

        # Check if within valid WPM range
        # PARIS standard: WPM = 1.2 / dot_duration
        wpm_estimate = 1.2 / dot_estimate

        if not (self.config.min_wpm <= wpm_estimate <= self.config.max_wpm):
            # Invalid WPM - don't update
            return

        # Update estimates with smoothing
        if self._estimated_dot_duration is None:
            self._estimated_dot_duration = dot_estimate
            self._estimated_wpm = wpm_estimate
            self._lock_count = 1
        else:
            # Exponential moving average for smoothing
            assert self._estimated_dot_duration is not None
            assert self._estimated_wpm is not None
            alpha = 0.2
            new_dot = alpha * dot_estimate + (1 - alpha) * self._estimated_dot_duration
            new_wpm = 1.2 / new_dot

            # Check if estimate is stable
            if abs(new_wpm - self._estimated_wpm) < 2.0:  # Within 2 WPM
                self._lock_count = min(self._lock_count + 1, self._required_lock_samples + 10)
            else:
                self._lock_count = max(0, self._lock_count - 1)

            self._estimated_dot_duration = new_dot
            self._estimated_wpm = new_wpm
