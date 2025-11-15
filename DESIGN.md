# CW Parser Library - Design Document

## Overview

This document outlines the design for a modern, highly pythonic, extremely testable CW (Morse code) parser library. The library will read from a soundcard, automatically detect signal parameters, handle noise robustly, and decode CW in real-time.

## Design Principles

1. **Dependency Injection** - All components accept dependencies via constructor
2. **Protocol-based interfaces** - Use `typing.Protocol` for duck typing and testability
3. **Streaming/Generator-based** - Process audio in chunks, yielding results incrementally
4. **Immutable data models** - Use `dataclasses` (frozen) for all data structures
5. **Type hints everywhere** - Full mypy strict mode compliance
6. **Async-first** - Use `asyncio` for I/O operations
7. **Pure functions** - Stateless processing functions where possible
8. **Factory pattern** - For creating configured instances

## Architecture

### Pipeline Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    CONTINUOUS-WAVE PIPELINE                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  Audio Input → AGC → Bandpass → Frequency Detection              │
│                  ↓                      ↓                         │
│              Goertzel Detector → Envelope Detector                │
│                                      ↓                            │
│                            Adaptive Timing Analyzer               │
│                                      ↓                            │
│                              Morse Decoder                        │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

### State Machine

The pipeline operates as a state machine:

1. **SEEKING_FREQUENCY** - Use FFT to find CW signal in spectrum
2. **LOCKING_FREQUENCY** - Verify signal stability and lock on
3. **SEEKING_WPM** - Detect sending speed using adaptive timing
4. **DECODING** - Full decode mode with continuous output

## Core Components

### 1. Data Models (`models.py`)

Immutable data structures representing pipeline data:

- **AudioSample** - Chunk of audio data with timestamp
- **ToneEvent** - Detected tone on/off event
- **MorseElement** - Enum: DOT, DASH, ELEMENT_GAP, CHAR_GAP, WORD_GAP
- **MorseSymbol** - Decoded Morse symbol with timing
- **DecodedCharacter** - Decoded character with confidence score
- **TimingStats** - Timing statistics (dot duration, WPM, etc.)

### 2. Protocols (`protocols.py`)

Protocol definitions for dependency injection and testing:

- **AudioSource** - Interface for audio input (soundcard, file, synthetic)
- **SignalProcessor** - Interface for signal processing
- **ToneDetector** - Interface for tone detection
- **TimingAnalyzer** - Interface for timing analysis
- **Decoder** - Interface for Morse decoding

### 3. Audio Sources (`audio/sources.py`)

#### SoundcardSource
- Reads from system audio input via `sounddevice`
- Async generator yielding audio chunks
- Configurable sample rate, channels, device

#### FileSource
- Reads from WAV files for testing
- Same interface as SoundcardSource

#### SyntheticSource
- Generates known CW signals for testing
- Controllable text, WPM, frequency, SNR
- Essential for reproducible tests

### 4. Noise Reduction (`signal/noise.py`)

#### AutomaticGainControl (AGC)
- Normalizes varying input signal levels
- Attack/release time constants
- Prevents clipping and maintains constant level

**Algorithm:**
- Track signal envelope
- Adjust gain to maintain target level
- Fast attack (10ms), slow release (100ms) for stability

#### AdaptiveBandpassFilter
- Narrow bandpass filter around detected frequency
- 4th-order Butterworth (good rolloff)
- Retune when frequency changes
- Uses SOS (second-order sections) for numerical stability

**Parameters:**
- Bandwidth: ~100 Hz (narrow for noise rejection)
- 4 WPM ≈ bandwidth in Hz (general rule)

#### SquelchGate
- Mutes output below threshold
- Prevents noise from triggering decoder
- Hysteresis prevents chattering

**Algorithm:**
- Open gate when signal > threshold + hysteresis
- Close gate when signal < threshold - hysteresis

### 5. Frequency Detection (`detection/frequency.py`)

#### AutoFrequencyDetector
Two-stage approach: **FFT for detection → Goertzel for tracking**

**FFT Detection Phase:**
- Compute power spectrum of audio chunk
- Find peak in CW frequency range (200-1200 Hz)
- Calculate SNR (peak vs. median of band)
- Require minimum SNR (6 dB) for confidence
- Track history for stability (low variance = lock)

**Why FFT for detection:**
- Sees entire spectrum at once
- Finds unknown frequencies
- Good for initial acquisition

#### FrequencyTracker
**Goertzel Algorithm** for efficient single-frequency tracking

**Why Goertzel after lock:**
- 30% faster than FFT for single frequency
- O(N) instead of O(N log N)
- Lower memory requirements
- Better for embedded/real-time

**Algorithm:**
```
k = round(N * f_target / f_sample)
coefficient = 2 * cos(2π * k / N)

For each sample:
  s = sample + coefficient * s_prev - s_prev2
  s_prev2 = s_prev
  s_prev = s

magnitude = sqrt(s_prev² + s_prev2² - coefficient * s_prev * s_prev2)
```

### 6. Tone Detection (`detection/tone.py`)

#### EnvelopeBasedToneDetector
Detects tone on/off transitions using envelope tracking

**Algorithm:**
- Compute amplitude envelope (Hilbert transform or simple rectify + smooth)
- Track envelope with attack/release time constants
- Detect state transitions (below → above threshold = tone on)
- Yield ToneEvent with timestamp

**Parameters:**
- Attack time: 1ms (fast response to tone onset)
- Release time: 5ms (debounce for clean trailing edge)
- Threshold: Adaptive based on AGC output

### 7. Adaptive WPM Detection (`timing/adaptive.py`)

#### AdaptiveWPMDetector
Automatically detects and tracks sending speed using PARIS standard

**PARIS Standard:**
- Standard word = "PARIS " (with trailing space)
- Duration = exactly 50 units
- WPM = 1200 / dot_duration_ms

**Algorithm:**

1. **Classification:**
   - Dot vs. Dash: threshold at 2× dot duration
   - Element gap: < 2× dot duration
   - Character gap: 2-5× dot duration
   - Word gap: > 5× dot duration

2. **Learning:**
   - Collect dot duration samples
   - Use median (robust to outliers)
   - Exponential moving average: `dot += α * (measured - dot)`
   - Learning rate α = 0.1 (smooth adaptation)

3. **Confidence:**
   - Based on sample consistency (low std deviation)
   - Require 10+ samples before lock
   - Confidence = 1.0 - (std / mean)

**Handles:**
- Variable sending speeds (5-55 WPM, extensible to 80+)
- Operator "fist" (individual style variations)
- Speed changes during transmission

### 8. Morse Decoding (`decoder/morse.py`)

#### MorseDecoder
Converts Morse symbols to text using lookup table

**International Morse Code Table:**
- A-Z: 26 letters
- 0-9: 10 digits
- Common punctuation
- Prosigns: SK, AR, BT, etc.

**Algorithm:**
1. Accumulate dots and dashes into pattern buffer
2. On character gap: lookup pattern in table
3. On word gap: insert space
4. Return decoded character with confidence score

**Confidence Scoring:**
- 1.0 if pattern found in table
- 0.0 if pattern unknown (returns "?")
- Future: Fuzzy matching for error correction

### 9. Pipeline Orchestration (`pipeline.py`)

#### ProductionCWPipeline
Orchestrates all components with automatic configuration

**Initialization:**
- Instantiate all components with dependency injection
- Allow overriding for testing
- Load configuration from CWConfig

**Main Loop:**
```python
async for audio_chunk in audio_source.read(chunk_size):
    # Stage 1: Noise reduction
    clean_audio = preprocessor.process(audio_chunk)

    # Stage 2: Frequency detection/tracking
    if state == SEEKING_FREQUENCY:
        detected_freq = freq_detector.detect(clean_audio)
        if freq_detector.is_locked:
            freq_tracker = FrequencyTracker(detected_freq)
            state = SEEKING_WPM

    # Stage 3: Tone detection
    tone_events = tone_detector.detect(clean_audio)

    # Stage 4: Timing analysis
    morse_symbols = timing_analyzer.analyze(tone_events)

    # Stage 5: Check WPM lock
    if state == SEEKING_WPM and timing_analyzer.is_locked:
        state = DECODING

    # Stage 6: Decode
    if state == DECODING:
        for character in decoder.decode(morse_symbols):
            yield character
```

## Performance Optimizations

### Sample Rate
- **Use 8 kHz instead of 44.1 kHz**
- CW signals < 4 kHz bandwidth
- 5× reduction in computational load
- Sufficient for 55 WPM at 1200 Hz

### Data Types
- **Use float32 instead of float64**
- 2× memory reduction
- Often faster on modern CPUs (SIMD)
- Sufficient precision for audio DSP

### Algorithm Choice
- **Goertzel > FFT** for single-frequency tracking
- 30% faster for tone detection after lock
- Lower memory footprint

### Vectorization
- **NumPy operations instead of Python loops**
- 10-100× speedup for array operations
- Example: Vectorized envelope detection

### Pre-allocation
- **Reuse buffers instead of allocating**
- Circular buffers for audio samples
- Buffer pools for intermediate results
- Reduces garbage collection pressure

### Optional Acceleration
- **Numba JIT** compilation for hot paths
  - Add `@jit(nopython=True)` decorator
  - Near-C performance for numeric code

- **Cython** for critical functions
  - Provide `.pyx` versions of Goertzel, envelope detection
  - 100-1000× speedup possible
  - Optional dependency

### Chunk Processing
- **Small chunks (256 samples) for low latency**
- 32ms latency at 8 kHz sample rate
- Balance between responsiveness and overhead

## Testing Strategy

### Unit Tests
- Test each component in isolation
- Mock dependencies using protocols
- Pure function tests (no side effects)
- Property-based testing with Hypothesis

**Example fixtures:**
```python
@pytest.fixture
def sample_audio_chunk():
    return AudioSample(
        data=np.random.randn(1024),
        sample_rate=8000,
        timestamp=0.0
    )

@pytest.fixture
def mock_audio_source():
    return Mock(spec=AudioSource)
```

### Integration Tests
- End-to-end pipeline tests
- Use SyntheticSource for known inputs
- Test with real audio files
- Verify decode accuracy

**Noise scenarios:**
- Variable SNR (0-20 dB)
- Frequency drift
- WPM variations
- Background QRM/QRN

### Performance Benchmarks
- pytest-benchmark for regression testing
- Target: Real-time decoding with <100ms latency
- Profile with `cProfile` and `line_profiler`
- Memory profiling with `memory_profiler`

### Test Generators
**SyntheticSource capabilities:**
- Generate known text at specified WPM
- Add white noise at specified SNR
- Simulate frequency drift
- Simulate variable sending speed
- Essential for reproducible tests

## Project Structure

```
continuous-wave/
├── src/
│   └── continuous_wave/
│       ├── __init__.py
│       ├── models.py              # Data models
│       ├── protocols.py           # Protocol definitions
│       ├── config.py              # Configuration classes
│       ├── audio/
│       │   ├── __init__.py
│       │   ├── sources.py         # Audio input sources
│       │   └── buffer.py          # Circular buffers
│       ├── signal/
│       │   ├── __init__.py
│       │   ├── processor.py       # Core DSP (FFT, Goertzel)
│       │   ├── filters.py         # Filtering (bandpass, etc.)
│       │   └── noise.py           # AGC, squelch, noise reduction
│       ├── detection/
│       │   ├── __init__.py
│       │   ├── tone.py            # Tone detection (envelope)
│       │   ├── frequency.py       # Auto frequency detection
│       │   └── envelope.py        # Envelope algorithms
│       ├── timing/
│       │   ├── __init__.py
│       │   ├── analyzer.py        # Basic timing
│       │   └── adaptive.py        # Auto WPM detection
│       ├── decoder/
│       │   ├── __init__.py
│       │   ├── morse.py           # Morse decoding
│       │   └── prosigns.py        # Prosign support
│       ├── performance/
│       │   ├── __init__.py
│       │   ├── optimizations.py   # Performance utilities
│       │   └── cython/            # Optional Cython modules
│       │       └── goertzel.pyx
│       ├── pipeline.py            # Pipeline orchestration
│       └── cli.py                 # Command-line interface
├── tests/
│   ├── conftest.py                # Pytest fixtures
│   ├── unit/                      # Unit tests for each module
│   │   ├── test_agc.py
│   │   ├── test_filters.py
│   │   ├── test_freq_detection.py
│   │   ├── test_wpm_detection.py
│   │   ├── test_goertzel.py
│   │   ├── test_envelope.py
│   │   └── test_decoder.py
│   ├── integration/               # Integration tests
│   │   ├── test_noise_scenarios.py
│   │   ├── test_auto_detection.py
│   │   └── test_pipeline.py
│   ├── performance/               # Performance benchmarks
│   │   ├── benchmark_goertzel.py
│   │   ├── benchmark_fft.py
│   │   └── benchmark_pipeline.py
│   └── fixtures/
│       ├── audio/                 # Real CW recordings
│       └── generators.py          # Synthetic signal generators
├── examples/
│   ├── basic_decode.py            # Simple decode example
│   ├── auto_detect.py             # Show auto-detection
│   ├── file_decode.py             # Decode from file
│   └── monitor_stats.py           # Real-time stats display
├── docs/
│   ├── index.md
│   ├── architecture.md
│   └── api/
├── pyproject.toml                 # Modern Python packaging
├── README.md
├── LICENSE
└── DESIGN.md                      # This document
```

## Dependencies

### Core Dependencies
```toml
[project]
name = "continuous-wave"
version = "0.1.0"
description = "Modern, testable CW (Morse code) decoder library"
requires-python = ">=3.11"
dependencies = [
    "numpy>=1.24.0",      # Array operations, DSP
    "scipy>=1.10.0",      # Signal processing, filters
    "sounddevice>=0.4.6", # Audio I/O
]
```

### Development Dependencies
```toml
[project.optional-dependencies]
dev = [
    "pytest>=7.4.0",
    "pytest-asyncio>=0.21.0",
    "pytest-cov>=4.1.0",
    "pytest-benchmark>=4.0.0",  # Performance testing
    "hypothesis>=6.82.0",        # Property-based testing
    "mypy>=1.5.0",
    "ruff>=0.0.280",
]

performance = [
    "numba>=0.57.0",             # JIT compilation
    "cython>=3.0.0",             # Optional C compilation
]
```

## Configuration

### CWConfig
Centralized configuration with sensible defaults:

```python
@dataclass
class CWConfig:
    # Audio settings
    sample_rate: int = 8000
    chunk_size: int = 256

    # Frequency detection
    freq_range: tuple[float, float] = (200.0, 1200.0)
    min_snr_db: float = 6.0

    # Filtering
    filter_bandwidth: float = 100.0

    # AGC
    agc_target: float = 0.5
    agc_attack_ms: float = 10.0
    agc_release_ms: float = 100.0

    # Squelch
    squelch_threshold: float = 0.05
    squelch_hysteresis: float = 0.02

    # Tone detection
    tone_threshold: float = 0.1

    # WPM detection
    initial_wpm: float = 20.0
    min_wpm: float = 5.0
    max_wpm: float = 55.0
    adaptive_timing: bool = True
```

## Implementation Phases

### Phase 1: Core + Noise Handling (Week 1)
- Data models, protocols, config
- AGC implementation
- Bandpass filtering
- Squelch gate
- Unit tests for each

**Deliverables:**
- `models.py`, `protocols.py`, `config.py`
- `signal/noise.py` with AGC, bandpass, squelch
- Comprehensive unit tests
- 90%+ test coverage

### Phase 2: Frequency Auto-Detection (Week 1-2)
- FFT-based frequency scanner
- Goertzel tracker
- Frequency lock logic
- Integration tests with synthetic signals

**Deliverables:**
- `detection/frequency.py`
- `signal/processor.py` (FFT, Goertzel)
- Test with known frequencies
- SNR sensitivity tests

### Phase 3: WPM Auto-Detection (Week 2)
- Adaptive timing analyzer
- PARIS standard implementation
- Learning algorithm
- Tests with variable-speed signals

**Deliverables:**
- `timing/adaptive.py`
- SyntheticSource with variable speed
- WPM accuracy tests (±1 WPM)

### Phase 4: Integration & Pipeline (Week 2-3)
- State machine pipeline
- Component integration
- End-to-end tests
- Real audio file testing

**Deliverables:**
- `pipeline.py` with state machine
- Full integration tests
- Example real CW audio files
- End-to-end accuracy validation

### Phase 5: Performance Optimization (Week 3)
- Benchmarking suite
- NumPy vectorization
- Optional Numba/Cython
- Memory profiling & optimization

**Deliverables:**
- `performance/` module
- Benchmark suite with regression tests
- Optional Cython modules
- Performance documentation

### Phase 6: Polish & Documentation (Week 4)
- CLI interface
- Examples
- API documentation
- CI/CD setup
- Performance regression tests

**Deliverables:**
- `cli.py` with rich output
- Complete examples/
- Full API docs
- GitHub Actions CI
- PyPI package

## Success Criteria

### Functional Requirements
- ✅ Decode CW from soundcard input
- ✅ Automatic frequency detection (200-1200 Hz)
- ✅ Automatic WPM detection (5-55 WPM)
- ✅ Handle noise (SNR ≥ 6 dB with >90% accuracy)
- ✅ Real-time performance (<100ms latency)

### Quality Requirements
- ✅ >90% test coverage
- ✅ 100% type hint coverage (mypy strict)
- ✅ All components mockable via protocols
- ✅ Zero public API without docstrings
- ✅ Clean ruff linting (no warnings)

### Performance Requirements
- ✅ Real-time decoding on modest hardware (Raspberry Pi 4+)
- ✅ <100ms total pipeline latency
- ✅ <50MB memory footprint
- ✅ CPU usage <25% on modern laptop

### Usability Requirements
- ✅ Simple API: `async for char in pipeline.decode_stream()`
- ✅ Sensible defaults (works out-of-box)
- ✅ Clear error messages
- ✅ Status monitoring API

## Research Findings

Based on analysis of successful CW decoder implementations:

### ggmorse (C++)
- Real-time decoding with automatic parameters
- Frequency range: 200-1200 Hz
- WPM range: 5-55
- WebAssembly support demonstrates portability

### RSCW (C)
- Optimized for weak signal recovery
- 8 kHz sample rate standard
- 2-second processing latency
- Manual WPM specification (no auto-detect)

### Deep Learning Approaches
- LSTM/CNN models for noise robustness
- Real-time capable even in Python
- Requires training data and complexity
- Traditional DSP approach preferred for this project

### Embedded Solutions (Arduino)
- WB7FHC decoder: automatic speed adjustment
- Goertzel algorithm common for resource constraints
- Noise impulse filters critical
- Proves real-time feasible on constrained hardware

### Key Insights
1. **Goertzel > FFT** for single-frequency detection (30% faster)
2. **Adaptive algorithms** essential for real-world signals
3. **AGC + narrow filtering** critical for noise handling
4. **Multi-stage approach** (detect → lock → decode) most robust
5. **8 kHz sample rate** sufficient and optimal
6. **Python + NumPy** can achieve real-time with proper optimization

## API Examples

### Basic Usage
```python
import asyncio
from continuous_wave import CWPipeline, CWConfig

async def main():
    config = CWConfig(
        adaptive_timing=True,
        min_snr_db=6.0,
    )

    pipeline = CWPipeline(config=config)

    print("Listening for CW...")
    async for character in pipeline.decode_stream():
        print(character.char, end='', flush=True)

asyncio.run(main())
```

### Monitoring Status
```python
async def main():
    pipeline = CWPipeline()

    async for character in pipeline.decode_stream():
        print(character.char, end='', flush=True)

        # Check status periodically
        status = pipeline.status
        if status['frequency_locked']:
            print(f"\nLocked: {status['frequency']:.1f} Hz, {status['wpm']:.1f} WPM")
```

### File Decoding
```python
from continuous_wave import CWPipeline, FileSource

async def decode_file(path: str):
    source = FileSource(path)
    pipeline = CWPipeline(audio_source=source)

    text = await pipeline.decode_text()
    return text
```

### Testing with Synthetic Signals
```python
from continuous_wave import CWPipeline, SyntheticSource

async def test_decode():
    source = SyntheticSource(
        text="THE QUICK BROWN FOX",
        wpm=20,
        frequency=600,
        snr_db=10,
    )

    pipeline = CWPipeline(audio_source=source)
    decoded = await pipeline.decode_text()

    assert decoded == "THE QUICK BROWN FOX"
```

## Future Enhancements

### Phase 2 Features (Post-MVP)
- Error correction with fuzzy matching
- Confidence-based character filtering
- QSK (full break-in) support
- Farnsworth spacing detection
- Prosign recognition (SK, AR, BT, etc.)
- Multiple simultaneous signals
- Waterfall display widget

### Advanced Features
- Machine learning for noise reduction
- Adaptive notch filters for QRM
- Frequency diversity (multi-tone CW)
- Network streaming (UDP/TCP)
- Integration with ham radio software (WSJT-X, Fldigi)

### Platform Support
- Browser version (WebAssembly via Emscripten)
- Mobile support (iOS/Android)
- Hardware acceleration (CUDA/OpenCL)
- FPGA implementation for ultra-low latency

## License

MIT License - suitable for use in open-source and commercial projects.

## Contributing

This library is designed for Claude Code development with the following priorities:

1. **Testability first** - Every component must be testable in isolation
2. **Type safety** - Full type hints, mypy strict mode
3. **Documentation** - Every public API must have docstrings
4. **Performance** - Benchmarks must pass before merging
5. **Code quality** - Clean ruff linting, no warnings

See CONTRIBUTING.md for detailed guidelines.

---

**Document Version:** 1.0
**Date:** 2025-11-15
**Status:** Ready for Implementation
