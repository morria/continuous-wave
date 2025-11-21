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
    # Immediate lock - bootstrap from first sample for fast acquisition
    _required_lock_samples: int = field(default=1, init=False)

    def analyze(self, event: ToneEvent) -> list[MorseSymbol]:
        """Analyze tone event and generate Morse symbols.

        Args:
            event: Tone on/off event to analyze

        Returns:
            List of MorseSymbol objects (may be empty if analysis incomplete)
        """
        symbols: list[MorseSymbol] = []

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
                symbols.append(symbol)

        elif not self._last_event.is_tone_on and event.is_tone_on:
            # Tone turned on - previous duration was a gap
            gap_symbol = self._classify_gap(duration)
            if gap_symbol is not None:
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

    def flush(self) -> list[MorseSymbol]:
        """Flush any pending state at end of stream.

        If there's a pending tone-on event without a corresponding tone-off,
        generate a final CHAR_GAP to trigger decoding of the last character.

        Returns:
            List of MorseSymbol instances for any pending events
        """
        symbols: list[MorseSymbol] = []

        # If we have a pending tone-on event, treat end-of-stream as tone-off
        # followed by a character gap
        if (
            self._last_event is not None
            and self._last_event.is_tone_on
            and self._estimated_dot_duration is not None
        ):
            # Generate a synthetic tone-off event to classify the last tone
            # Assume a dash duration for safety
            duration = self._estimated_dot_duration * 3.0
            symbol = MorseSymbol(
                element=MorseElement.DASH,
                duration=duration,
                timestamp=0.0,
            )
            symbols.append(symbol)

        # Always add a final CHAR_GAP to trigger decoding of any pending pattern
        if self._estimated_dot_duration is not None:
            char_gap = MorseSymbol(
                element=MorseElement.CHAR_GAP,
                duration=self._estimated_dot_duration * 3.0,
                timestamp=0.0,
            )
            symbols.append(char_gap)

        return symbols

    def reset(self) -> None:
        """Reset timing analyzer state."""
        self._last_event = None
        self._dot_durations.clear()
        self._dash_durations.clear()
        self._estimated_dot_duration = None
        self._estimated_wpm = None
        self._lock_count = 0

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

        # Calculate median dot duration from dot samples
        if self._dot_durations:
            dot_estimate = sorted(self._dot_durations)[len(self._dot_durations) // 2]
        else:
            # Infer from dash durations (dash = 3x dot)
            dash_estimate = sorted(self._dash_durations)[len(self._dash_durations) // 2]
            dot_estimate = dash_estimate / 3.0

        # If we have dash durations, refine estimate
        if self._dash_durations and self._dot_durations:
            dash_estimate = sorted(self._dash_durations)[len(self._dash_durations) // 2]
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
