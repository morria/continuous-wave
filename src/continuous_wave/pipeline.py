"""Main CW decoder pipeline orchestration."""

import time
from collections.abc import AsyncIterator
from dataclasses import dataclass

from continuous_wave.config import CWConfig
from continuous_wave.models import DecodedCharacter, SignalStats, TimingStats
from continuous_wave.protocols import (
    AudioSource,
    Decoder,
    FrequencyDetector,
    TimingAnalyzer,
    ToneDetector,
)
from continuous_wave.signal.noise import NoiseReductionPipeline


@dataclass
class CWDecoderState:
    """Current state of the CW decoder."""

    frequency_stats: SignalStats | None = None
    timing_stats: TimingStats | None = None
    is_frequency_locked: bool = False
    is_timing_locked: bool = False
    characters_decoded: int = 0


@dataclass
class CWDecoderPipeline:
    """Complete CW decoder pipeline.

    Orchestrates the flow:
    Audio → Noise Reduction → Frequency Detection → Tone Detection →
    Timing Analysis → Morse Decoding → Characters
    """

    config: CWConfig
    audio_source: AudioSource
    noise_pipeline: NoiseReductionPipeline
    frequency_detector: FrequencyDetector
    tone_detector: ToneDetector
    timing_analyzer: TimingAnalyzer
    decoder: Decoder

    _state: CWDecoderState = None
    _start_time: float = 0.0

    def __post_init__(self) -> None:
        """Initialize pipeline state."""
        self._state = CWDecoderState()
        self._start_time = time.time()

    async def run(self) -> AsyncIterator[tuple[DecodedCharacter, CWDecoderState]]:
        """Run the complete decoding pipeline.

        Yields:
            Tuples of (DecodedCharacter, CWDecoderState) for each decoded character
        """
        async for audio_sample in self.audio_source:
            # Update timestamp relative to start
            current_time = time.time() - self._start_time

            # Step 1: Noise reduction (AGC → Bandpass → Squelch)
            cleaned_audio = self.noise_pipeline.process(audio_sample.data)

            # Step 2: Frequency detection
            freq_stats = self.frequency_detector.detect(cleaned_audio)
            if freq_stats is not None:
                freq_stats.timestamp = current_time
                self._state.frequency_stats = freq_stats
                self._state.is_frequency_locked = self.frequency_detector.is_locked()

                # Update bandpass filter center frequency if locked
                if self._state.is_frequency_locked:
                    self.noise_pipeline.retune_filter(freq_stats.frequency)

            # Step 3: Tone detection (only if frequency is locked)
            if self._state.is_frequency_locked and freq_stats is not None:
                tone_events = self.tone_detector.detect(cleaned_audio)

                # Step 4: Timing analysis
                for event in tone_events:
                    event.timestamp = current_time
                    morse_symbols = self.timing_analyzer.analyze(event)

                    # Update timing state
                    timing_stats = self.timing_analyzer.timing_stats()
                    if timing_stats is not None:
                        self._state.timing_stats = timing_stats
                        self._state.is_timing_locked = self.timing_analyzer.is_locked()

                    # Step 5: Morse decoding
                    if morse_symbols:
                        decoded_chars = self.decoder.decode(morse_symbols)

                        # Yield each decoded character with current state
                        for char in decoded_chars:
                            char.timestamp = current_time
                            self._state.characters_decoded += 1
                            yield char, self._state

    def get_state(self) -> CWDecoderState:
        """Get current decoder state.

        Returns:
            Current CWDecoderState
        """
        return self._state

    def reset(self) -> None:
        """Reset all pipeline components."""
        self.noise_pipeline.reset()
        self.frequency_detector.reset()
        self.tone_detector.reset()
        self.timing_analyzer.reset()
        self.decoder.reset()
        self._state = CWDecoderState()
        self._start_time = time.time()
