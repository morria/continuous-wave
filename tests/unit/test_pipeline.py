"""Unit tests for CW decoder pipeline."""

from collections.abc import AsyncIterator

import numpy as np
import pytest

from continuous_wave.config import CWConfig
from continuous_wave.models import (
    AudioSample,
    DecodedCharacter,
    MorseElement,
    MorseSymbol,
    SignalStats,
    TimingStats,
    ToneEvent,
)
from continuous_wave.pipeline import CWDecoderPipeline, CWDecoderState
from continuous_wave.signal.noise import NoiseReductionPipeline


class MockAudioSource:
    """Mock audio source for testing."""

    def __init__(self, samples: list[AudioSample]) -> None:
        self.samples = samples
        self.index = 0

    async def __aiter__(self) -> AsyncIterator[AudioSample]:
        """Iterate over audio samples."""
        for sample in self.samples:
            yield sample

    async def __anext__(self) -> AudioSample:
        """Get next audio sample."""
        if self.index >= len(self.samples):
            raise StopAsyncIteration
        sample = self.samples[self.index]
        self.index += 1
        return sample


class MockFrequencyDetector:
    """Mock frequency detector for testing."""

    def __init__(self, locked: bool = True, frequency: float = 600.0) -> None:
        self._locked = locked
        self._frequency = frequency
        self.detect_calls = 0
        self.reset_calls = 0

    def detect(self, audio: AudioSample) -> SignalStats | None:
        """Mock detect method."""
        self.detect_calls += 1
        if audio.num_samples == 0:
            return None
        return SignalStats(
            frequency=self._frequency,
            snr_db=20.0,
            power=0.5,
            timestamp=0.0,
        )

    @property
    def is_locked(self) -> bool:
        """Check if locked."""
        return self._locked

    def reset(self) -> None:
        """Reset detector."""
        self.reset_calls += 1


class MockToneDetector:
    """Mock tone detector for testing."""

    def __init__(self, events: list[ToneEvent] | None = None) -> None:
        self.events = events or []
        self.detect_calls = 0
        self.reset_calls = 0

    def detect(self, audio: AudioSample) -> list[ToneEvent]:
        """Mock detect method."""
        self.detect_calls += 1
        return self.events.copy()

    def reset(self) -> None:
        """Reset detector."""
        self.reset_calls += 1


class MockTimingAnalyzer:
    """Mock timing analyzer for testing."""

    def __init__(self, symbols: list[MorseSymbol] | None = None, locked: bool = True) -> None:
        self.symbols = symbols or []
        self._locked = locked
        self.analyze_calls = 0
        self.reset_calls = 0

    def analyze(self, event: ToneEvent) -> list[MorseSymbol]:
        """Mock analyze method."""
        self.analyze_calls += 1
        return self.symbols.copy()

    @property
    def is_locked(self) -> bool:
        """Check if locked."""
        return self._locked

    @property
    def timing_stats(self) -> TimingStats | None:
        """Get timing stats."""
        if not self._locked:
            return None
        return TimingStats(
            dot_duration=0.060,
            wpm=20.0,
            confidence=0.9,
            num_samples=10,
        )

    def reset(self) -> None:
        """Reset analyzer."""
        self.reset_calls += 1


class MockDecoder:
    """Mock decoder for testing."""

    def __init__(self, characters: list[DecodedCharacter] | None = None) -> None:
        self.characters = characters or []
        self.decode_calls = 0
        self.reset_calls = 0

    def decode(self, symbols: list[MorseSymbol]) -> list[DecodedCharacter]:
        """Mock decode method."""
        self.decode_calls += 1
        return self.characters.copy()

    def reset(self) -> None:
        """Reset decoder."""
        self.reset_calls += 1


@pytest.fixture
def config() -> CWConfig:
    """Create test configuration."""
    return CWConfig()


@pytest.fixture
def noise_pipeline(config: CWConfig) -> NoiseReductionPipeline:
    """Create noise reduction pipeline."""
    return NoiseReductionPipeline(config=config)


class TestPipelineInitialization:
    """Test pipeline initialization."""

    def test_pipeline_initializes_state(
        self, config: CWConfig, noise_pipeline: NoiseReductionPipeline
    ) -> None:
        """Test pipeline initializes with proper state."""
        audio_source = MockAudioSource([])
        freq_detector = MockFrequencyDetector()
        tone_detector = MockToneDetector()
        timing_analyzer = MockTimingAnalyzer()
        decoder = MockDecoder()

        pipeline = CWDecoderPipeline(
            config=config,
            audio_source=audio_source,
            noise_pipeline=noise_pipeline,
            frequency_detector=freq_detector,
            tone_detector=tone_detector,
            timing_analyzer=timing_analyzer,
            decoder=decoder,
        )

        assert pipeline._state is not None
        assert pipeline._state.frequency_stats is None
        assert pipeline._state.timing_stats is None
        assert not pipeline._state.is_frequency_locked
        assert not pipeline._state.is_timing_locked
        assert pipeline._state.characters_decoded == 0

    def test_get_state_returns_current_state(
        self, config: CWConfig, noise_pipeline: NoiseReductionPipeline
    ) -> None:
        """Test get_state returns current state."""
        audio_source = MockAudioSource([])
        freq_detector = MockFrequencyDetector()
        tone_detector = MockToneDetector()
        timing_analyzer = MockTimingAnalyzer()
        decoder = MockDecoder()

        pipeline = CWDecoderPipeline(
            config=config,
            audio_source=audio_source,
            noise_pipeline=noise_pipeline,
            frequency_detector=freq_detector,
            tone_detector=tone_detector,
            timing_analyzer=timing_analyzer,
            decoder=decoder,
        )

        state = pipeline.get_state()
        assert isinstance(state, CWDecoderState)
        assert state.characters_decoded == 0


class TestPipelineReset:
    """Test pipeline reset functionality."""

    def test_reset_clears_state(
        self, config: CWConfig, noise_pipeline: NoiseReductionPipeline
    ) -> None:
        """Test reset clears all pipeline state."""
        audio_source = MockAudioSource([])
        freq_detector = MockFrequencyDetector()
        tone_detector = MockToneDetector()
        timing_analyzer = MockTimingAnalyzer()
        decoder = MockDecoder()

        pipeline = CWDecoderPipeline(
            config=config,
            audio_source=audio_source,
            noise_pipeline=noise_pipeline,
            frequency_detector=freq_detector,
            tone_detector=tone_detector,
            timing_analyzer=timing_analyzer,
            decoder=decoder,
        )

        # Modify state
        pipeline._state.characters_decoded = 10
        pipeline._state.is_frequency_locked = True

        # Reset
        pipeline.reset()

        # State should be cleared
        assert pipeline._state.characters_decoded == 0
        assert not pipeline._state.is_frequency_locked

    def test_reset_calls_component_resets(
        self, config: CWConfig, noise_pipeline: NoiseReductionPipeline
    ) -> None:
        """Test reset calls reset on all components."""
        audio_source = MockAudioSource([])
        freq_detector = MockFrequencyDetector()
        tone_detector = MockToneDetector()
        timing_analyzer = MockTimingAnalyzer()
        decoder = MockDecoder()

        pipeline = CWDecoderPipeline(
            config=config,
            audio_source=audio_source,
            noise_pipeline=noise_pipeline,
            frequency_detector=freq_detector,
            tone_detector=tone_detector,
            timing_analyzer=timing_analyzer,
            decoder=decoder,
        )

        pipeline.reset()

        # All components should have reset called
        assert freq_detector.reset_calls == 1
        assert tone_detector.reset_calls == 1
        assert timing_analyzer.reset_calls == 1
        assert decoder.reset_calls == 1


class TestPipelineDataFlow:
    """Test data flow through pipeline."""

    @pytest.mark.asyncio
    async def test_processes_audio_samples(
        self, config: CWConfig, noise_pipeline: NoiseReductionPipeline
    ) -> None:
        """Test pipeline processes audio samples."""
        # Create audio sample
        data = np.random.randn(1024).astype(np.float64)
        audio = AudioSample(data=data, sample_rate=config.sample_rate, timestamp=0.0)

        audio_source = MockAudioSource([audio])
        freq_detector = MockFrequencyDetector(locked=True)
        tone_detector = MockToneDetector()
        timing_analyzer = MockTimingAnalyzer()
        decoder = MockDecoder()

        pipeline = CWDecoderPipeline(
            config=config,
            audio_source=audio_source,
            noise_pipeline=noise_pipeline,
            frequency_detector=freq_detector,
            tone_detector=tone_detector,
            timing_analyzer=timing_analyzer,
            decoder=decoder,
        )

        # Run pipeline (should process audio even if no characters decoded)
        results = []
        async for char, state in pipeline.run():
            results.append((char, state))

        # Frequency detector should have been called
        assert freq_detector.detect_calls == 1

    @pytest.mark.asyncio
    async def test_updates_frequency_stats(
        self, config: CWConfig, noise_pipeline: NoiseReductionPipeline
    ) -> None:
        """Test pipeline updates frequency stats."""
        data = np.random.randn(1024).astype(np.float64)
        audio = AudioSample(data=data, sample_rate=config.sample_rate, timestamp=0.0)

        audio_source = MockAudioSource([audio])
        freq_detector = MockFrequencyDetector(locked=True, frequency=650.0)
        tone_detector = MockToneDetector()
        timing_analyzer = MockTimingAnalyzer()
        decoder = MockDecoder()

        pipeline = CWDecoderPipeline(
            config=config,
            audio_source=audio_source,
            noise_pipeline=noise_pipeline,
            frequency_detector=freq_detector,
            tone_detector=tone_detector,
            timing_analyzer=timing_analyzer,
            decoder=decoder,
        )

        async for _char, _state in pipeline.run():
            pass

        # State should have frequency stats
        state = pipeline.get_state()
        assert state.frequency_stats is not None
        assert state.frequency_stats.frequency == 650.0
        assert state.is_frequency_locked

    @pytest.mark.asyncio
    async def test_only_processes_tone_when_frequency_locked(
        self, config: CWConfig, noise_pipeline: NoiseReductionPipeline
    ) -> None:
        """Test tone detection only happens when frequency is locked."""
        data = np.random.randn(1024).astype(np.float64)
        audio = AudioSample(data=data, sample_rate=config.sample_rate, timestamp=0.0)

        # Not locked
        audio_source = MockAudioSource([audio])
        freq_detector = MockFrequencyDetector(locked=False)
        tone_detector = MockToneDetector()
        timing_analyzer = MockTimingAnalyzer()
        decoder = MockDecoder()

        pipeline = CWDecoderPipeline(
            config=config,
            audio_source=audio_source,
            noise_pipeline=noise_pipeline,
            frequency_detector=freq_detector,
            tone_detector=tone_detector,
            timing_analyzer=timing_analyzer,
            decoder=decoder,
        )

        async for _char, _state in pipeline.run():
            pass

        # Tone detector should not have been called
        assert tone_detector.detect_calls == 0


class TestEndToEndDecoding:
    """Test end-to-end character decoding."""

    @pytest.mark.asyncio
    async def test_decodes_character_end_to_end(
        self, config: CWConfig, noise_pipeline: NoiseReductionPipeline
    ) -> None:
        """Test complete pipeline decodes characters."""
        data = np.random.randn(1024).astype(np.float64)
        audio = AudioSample(data=data, sample_rate=config.sample_rate, timestamp=0.0)

        # Setup mocks to produce a decoded character
        tone_event = ToneEvent(is_tone_on=True, timestamp=0.0, amplitude=0.8)
        morse_symbol = MorseSymbol(element=MorseElement.DOT, duration=0.06, timestamp=0.0)
        decoded_char = DecodedCharacter(char="E", confidence=1.0, morse_pattern=".", timestamp=0.0)

        audio_source = MockAudioSource([audio])
        freq_detector = MockFrequencyDetector(locked=True)
        tone_detector = MockToneDetector(events=[tone_event])
        timing_analyzer = MockTimingAnalyzer(symbols=[morse_symbol], locked=True)
        decoder = MockDecoder(characters=[decoded_char])

        pipeline = CWDecoderPipeline(
            config=config,
            audio_source=audio_source,
            noise_pipeline=noise_pipeline,
            frequency_detector=freq_detector,
            tone_detector=tone_detector,
            timing_analyzer=timing_analyzer,
            decoder=decoder,
        )

        results = []
        async for char, state in pipeline.run():
            results.append((char, state))

        # Should have decoded one character
        assert len(results) == 1
        assert results[0][0].char == "E"
        assert results[0][1].characters_decoded == 1

    @pytest.mark.asyncio
    async def test_decodes_multiple_characters(
        self, config: CWConfig, noise_pipeline: NoiseReductionPipeline
    ) -> None:
        """Test pipeline decodes multiple characters."""
        data = np.random.randn(1024).astype(np.float64)
        audio = AudioSample(data=data, sample_rate=config.sample_rate, timestamp=0.0)

        # Multiple decoded characters
        char1 = DecodedCharacter(char="S", confidence=1.0, morse_pattern="...", timestamp=0.0)
        char2 = DecodedCharacter(char="O", confidence=1.0, morse_pattern="---", timestamp=0.1)

        tone_event = ToneEvent(is_tone_on=True, timestamp=0.0, amplitude=0.8)
        morse_symbol = MorseSymbol(element=MorseElement.DOT, duration=0.06, timestamp=0.0)

        audio_source = MockAudioSource([audio])
        freq_detector = MockFrequencyDetector(locked=True)
        tone_detector = MockToneDetector(events=[tone_event])
        timing_analyzer = MockTimingAnalyzer(symbols=[morse_symbol], locked=True)
        decoder = MockDecoder(characters=[char1, char2])

        pipeline = CWDecoderPipeline(
            config=config,
            audio_source=audio_source,
            noise_pipeline=noise_pipeline,
            frequency_detector=freq_detector,
            tone_detector=tone_detector,
            timing_analyzer=timing_analyzer,
            decoder=decoder,
        )

        results = []
        async for char, state in pipeline.run():
            results.append((char, state))

        # Should have decoded two characters
        assert len(results) == 2
        assert results[0][0].char == "S"
        assert results[1][0].char == "O"
        assert results[1][1].characters_decoded == 2

    @pytest.mark.asyncio
    async def test_handles_no_characters_decoded(
        self, config: CWConfig, noise_pipeline: NoiseReductionPipeline
    ) -> None:
        """Test pipeline handles case where no characters are decoded."""
        data = np.random.randn(1024).astype(np.float64)
        audio = AudioSample(data=data, sample_rate=config.sample_rate, timestamp=0.0)

        audio_source = MockAudioSource([audio])
        freq_detector = MockFrequencyDetector(locked=True)
        tone_detector = MockToneDetector(events=[])  # No events
        timing_analyzer = MockTimingAnalyzer(symbols=[], locked=True)
        decoder = MockDecoder(characters=[])  # No characters

        pipeline = CWDecoderPipeline(
            config=config,
            audio_source=audio_source,
            noise_pipeline=noise_pipeline,
            frequency_detector=freq_detector,
            tone_detector=tone_detector,
            timing_analyzer=timing_analyzer,
            decoder=decoder,
        )

        results = []
        async for char, state in pipeline.run():
            results.append((char, state))

        # Should have no results
        assert len(results) == 0

        # But state should still be updated
        state = pipeline.get_state()
        assert state.is_frequency_locked
        # Timing won't lock without events, so we don't assert is_timing_locked


class TestStateTracking:
    """Test pipeline state tracking."""

    @pytest.mark.asyncio
    async def test_tracks_timing_lock_state(
        self, config: CWConfig, noise_pipeline: NoiseReductionPipeline
    ) -> None:
        """Test pipeline tracks timing lock state."""
        data = np.random.randn(1024).astype(np.float64)
        audio = AudioSample(data=data, sample_rate=config.sample_rate, timestamp=0.0)

        tone_event = ToneEvent(is_tone_on=True, timestamp=0.0, amplitude=0.8)
        morse_symbol = MorseSymbol(element=MorseElement.DOT, duration=0.06, timestamp=0.0)
        decoded_char = DecodedCharacter(char="E", confidence=1.0, morse_pattern=".", timestamp=0.0)

        audio_source = MockAudioSource([audio])
        freq_detector = MockFrequencyDetector(locked=True)
        tone_detector = MockToneDetector(events=[tone_event])
        timing_analyzer = MockTimingAnalyzer(symbols=[morse_symbol], locked=True)
        decoder = MockDecoder(characters=[decoded_char])

        pipeline = CWDecoderPipeline(
            config=config,
            audio_source=audio_source,
            noise_pipeline=noise_pipeline,
            frequency_detector=freq_detector,
            tone_detector=tone_detector,
            timing_analyzer=timing_analyzer,
            decoder=decoder,
        )

        async for _char, state in pipeline.run():
            # State should show timing is locked
            assert state.is_timing_locked
            assert state.timing_stats is not None
            assert state.timing_stats.wpm == 20.0

    @pytest.mark.asyncio
    async def test_tracks_total_characters_decoded(
        self, config: CWConfig, noise_pipeline: NoiseReductionPipeline
    ) -> None:
        """Test pipeline tracks total characters decoded."""
        data = np.random.randn(1024).astype(np.float64)
        audio = AudioSample(data=data, sample_rate=config.sample_rate, timestamp=0.0)

        char1 = DecodedCharacter(char="S", confidence=1.0, morse_pattern="...", timestamp=0.0)
        char2 = DecodedCharacter(char="O", confidence=1.0, morse_pattern="---", timestamp=0.1)

        tone_event = ToneEvent(is_tone_on=True, timestamp=0.0, amplitude=0.8)
        morse_symbol = MorseSymbol(element=MorseElement.DOT, duration=0.06, timestamp=0.0)

        audio_source = MockAudioSource([audio])
        freq_detector = MockFrequencyDetector(locked=True)
        tone_detector = MockToneDetector(events=[tone_event])
        timing_analyzer = MockTimingAnalyzer(symbols=[morse_symbol], locked=True)
        decoder = MockDecoder(characters=[char1, char2])

        pipeline = CWDecoderPipeline(
            config=config,
            audio_source=audio_source,
            noise_pipeline=noise_pipeline,
            frequency_detector=freq_detector,
            tone_detector=tone_detector,
            timing_analyzer=timing_analyzer,
            decoder=decoder,
        )

        results = []
        async for char, state in pipeline.run():
            results.append((char, state))

        # Should have decoded 2 characters total
        assert len(results) == 2
        # Final state should show 2 characters decoded
        assert results[-1][1].characters_decoded == 2
