# Decoder Fixes Required for Test Completion

## ✅ STATUS: COMPLETED (2025-11-19)

**This plan has been successfully completed.** The timing analyzer locking issue was fixed in commit 345dbcb "Fix timing analyzer locking issue in WAV file decoding". All 15 previously skipped integration tests now pass, and the decoder successfully performs end-to-end decoding from audio to characters.

This document is retained for historical reference and to document the debugging process that led to the solution.

---

## Executive Summary

The CW decoder has made significant progress with **critical bugs fixed** in frequency detection and tone detection. The pipeline now successfully:
- ✅ Detects signal frequencies across the full 200-1200 Hz range
- ✅ Locks onto detected frequencies (e.g., 593.75 Hz for 600 Hz signals)
- ✅ Generates tone ON/OFF events using adaptive thresholding
- ✅ Processes WAV files without crashes
- ✅ **Timing analyzer locks onto morse code timing patterns** (FIXED)
- ✅ **All 15 integration tests pass** (FIXED)

## Current Test Status (Updated: 2025-11-19)

**All Tests Passing (22 tests):** ✅
- `test_wav_fixtures_directory_exists` ✅
- `test_at_least_one_wav_file_exists` ✅
- `test_pipeline_processes_wav_file` (5 WAV files) ✅
- `test_decode_wav_streaming` (5 WAV files) ✅ (Previously skipped - NOW PASSING)
- `test_decode_wav_direct` (5 WAV files) ✅ (Previously skipped - NOW PASSING)
- `test_decode_consistency` (5 WAV files) ✅ (Previously skipped - NOW PASSING)

**Previous Skip Reason (Resolved):** Timing analyzer not locking - tone events are generated but timing patterns not detected. **FIXED in commit 345dbcb.**

## Root Cause Analysis

### Current Pipeline Flow

```
Audio Input
    ↓
Frequency Detection (✅ WORKING)
    ↓
Tone Detection (✅ WORKING - generates ON/OFF events)
    ↓
Timing Analyzer (❌ NOT LOCKING)
    ↓
Morse Decoder (❌ NO INPUT)
    ↓
Output (❌ EMPTY)
```

### The Problem

The `AdaptiveWPMDetector` (timing analyzer) receives `ToneEvent` objects but fails to:
1. Analyze the duration patterns between ON/OFF events
2. Detect the dot duration (fundamental morse timing unit)
3. Calculate WPM (words per minute)
4. Lock onto the timing pattern
5. Generate morse symbols (dots, dashes, gaps)

**Evidence from debugging:**
```
Decoded text: ''
Expected: 'TEST'
Match: False
Frequency locked: True    ✅
Timing locked: False      ❌
```

## Required Fixes

### 1. Investigate Timing Analyzer Event Processing

**File:** `src/continuous_wave/timing/adaptive.py`

**Investigation needed:**
- How does `AdaptiveWPMDetector.analyze(event: ToneEvent)` process events?
- What conditions must be met for `is_locked` to become `True`?
- Are timing measurements being collected correctly?
- Is the state machine transitioning properly?

**Likely issues:**
- Event timestamps may be incorrect (currently set to `0.0` in ToneEvent)
- Insufficient event history to establish timing patterns
- Lock thresholds too strict for test signals
- Duration calculation errors

### 2. Fix Timestamp Propagation

**Problem:** `ToneEvent` objects have `timestamp=0.0` when created, with a comment "Will be set by pipeline". The pipeline may not be setting these correctly.

**Files to check:**
- `src/continuous_wave/pipeline.py` - Does it update event timestamps?
- `src/continuous_wave/detection/tone.py` - Events created with `timestamp=0.0`

**Fix needed:**
```python
# In tone detector or pipeline:
event = replace(event, timestamp=current_audio_timestamp)
```

### 3. Verify Timing Analyzer Lock Logic

**File:** `src/continuous_wave/timing/adaptive.py`

**Check:**
- What is the required number of events before locking?
- What is the acceptable variance in timing measurements?
- Are there debug logs or state inspection methods?

**Suggested debug approach:**
```python
# Add detailed logging to timing analyzer:
- Log each ToneEvent received with timestamp and duration
- Log calculated dot duration candidates
- Log confidence scores for timing patterns
- Log why lock fails (not enough data? too much variance?)
```

### 4. Examine Test Signal Timing

**File:** `tests/integration/fixtures/wav_files/generate_test_wav.py`

**Verify test signals:**
- Default WPM: 20 WPM (dot = 60ms based on PARIS standard)
- Actual dot duration in samples: `1.2 / 20 * 8000 = 480 samples = 60ms` ✅
- Element gap: 60ms
- Character gap: 180ms
- Word gap: 420ms

**With 256-sample chunks at 8000 Hz:**
- Chunk duration: 32ms
- Dot duration: ~2 chunks (60ms / 32ms = 1.875)
- Dash duration: ~6 chunks (180ms / 32ms = 5.625)

**Potential issue:** The 32ms chunk size may be too coarse for accurate timing measurement. The timing analyzer might need:
- Finer timestamp resolution
- Interpolation between chunks
- Multiple event accumulation before making decisions

### 5. Check Morse Symbol Generation

**File:** `src/continuous_wave/timing/adaptive.py`

**Verify:**
- Does `analyze()` return `list[MorseSymbol]` as expected?
- Are symbols only generated after lock?
- What happens to events received before lock?

**Required behavior:**
```python
def analyze(self, event: ToneEvent) -> list[MorseSymbol]:
    # Should track event timing
    # Should accumulate pattern data
    # Should generate symbols once locked
    # Should return dots/dashes/gaps based on durations
```

### 6. Review MorseDecoder Integration

**File:** `src/continuous_wave/decoder/morse.py`

**Verify:**
- Does decoder properly handle symbol streams?
- Are character gap and word gap symbols recognized?
- Does decoder maintain proper state between calls?

## Recommended Debug Process

### Step 1: Add Comprehensive Logging

```python
# In AdaptiveWPMDetector.analyze():
logger.debug(f"Received event: {event}, tone_on={event.is_tone_on}, ts={event.timestamp}")
logger.debug(f"Current state: locked={self.is_locked}, events_seen={self._event_count}")
logger.debug(f"Timing stats: {self.timing_stats}")
```

### Step 2: Create Minimal Test Case

```python
# Create simple test with known timing:
async def test_timing_analyzer_with_known_pattern():
    """Test timing analyzer with hand-crafted events."""
    analyzer = AdaptiveWPMDetector(config)

    # Simulate 20 WPM (dot = 60ms)
    events = [
        ToneEvent(True, 0.000, 0.5),   # Dot starts
        ToneEvent(False, 0.060, 0.1),  # Dot ends (60ms)
        ToneEvent(True, 0.120, 0.5),   # Dot starts
        ToneEvent(False, 0.180, 0.1),  # Dot ends (60ms)
        # ... more events
    ]

    for event in events:
        symbols = analyzer.analyze(event)
        print(f"Event: {event.is_tone_on}, Symbols: {symbols}, Locked: {analyzer.is_locked}")
```

### Step 3: Examine State Transitions

```python
# Track state machine transitions:
- What triggers transition from UNLOCKED → LOCKING?
- What triggers transition from LOCKING → LOCKED?
- What causes LOCKED → UNLOCKED (loss of lock)?
```

### Step 4: Validate Against Real Morse

Compare timing measurements against actual morse code standard:
- PARIS standard: "PARIS " = 50 dots
- At 20 WPM: 1 word/minute = 50 dots/60 seconds = dot = 1.2 seconds / word
- Therefore: dot_duration_ms = 1200 / WPM

## Expected Outcomes

Once timing analyzer is fixed:

1. **Timing lock achieved:**
   ```
   Timing locked: True ✅
   WPM: ~20.0
   Dot duration: ~60ms
   ```

2. **Morse symbols generated:**
   ```python
   [
       MorseSymbol.DOT,
       MorseSymbol.ELEMENT_GAP,
       MorseSymbol.DOT,
       MorseSymbol.CHAR_GAP,
       # etc.
   ]
   ```

3. **Characters decoded:**
   ```
   Decoded text: 'TEST'
   Expected:     'TEST'
   Match: True ✅
   ```

4. **All 15 skipped tests pass** 🎉

## Implementation Priority

1. **HIGH:** Fix timestamp propagation (quick win, may solve everything)
2. **HIGH:** Add debug logging to timing analyzer
3. **MEDIUM:** Create minimal timing analyzer test with known events
4. **MEDIUM:** Review lock thresholds and state machine logic
5. **LOW:** Consider chunk size implications (may need architectural change)

## Estimated Effort

- **Quick path** (if timestamp issue): 1-2 hours
- **Moderate path** (if lock logic tuning needed): 4-8 hours
- **Complex path** (if architectural changes needed): 1-2 days

## Success Criteria ✅ ALL COMPLETED

- [x] `test_decode_wav_streaming` passes for all 5 WAV files ✅
- [x] `test_decode_wav_direct` passes for all 5 WAV files ✅
- [x] `test_decode_wav_consistency` passes for all 5 WAV files ✅
- [x] Timing analyzer reliably locks on 20 WPM morse code ✅
- [x] Full end-to-end decoding: Audio → Characters ✅

**All success criteria met as of 2025-11-19 (commit 345dbcb)**

## References

- Pipeline architecture: `src/continuous_wave/pipeline.py`
- Timing analyzer: `src/continuous_wave/timing/adaptive.py`
- Tone detector: `src/continuous_wave/detection/tone.py`
- Test signal generator: `tests/integration/fixtures/wav_files/generate_test_wav.py`
- Design document: `DESIGN.md`
