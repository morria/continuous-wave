# Type Errors and Remediation Plan

This document details the type errors currently suppressed by mypy overrides in `pyproject.toml` and provides a plan for fixing them.

**Status**: 42 type errors across 8 modules
**Last Updated**: 2025-11-19

## Summary by Module

| Module | Errors | Severity | Effort |
|--------|--------|----------|--------|
| `cli.py` | 13 | Medium | Low |
| `audio/file.py` | 7 | High | Medium |
| `audio/soundcard.py` | 5 | High | Medium |
| `detection/tone.py` | 3 | High | Low |
| `timing/adaptive.py` | 2 | High | Medium |
| `decoder/morse.py` | 5 | High | Medium |
| `detection/frequency.py` | 4 | Medium | Low |
| `pipeline.py` | 3 | High | Medium |

---

## Category 1: Protocol Signature Mismatches (High Priority)

### Issue: Methods return `list` instead of `Iterator`

**Affected Files**:
- `timing/adaptive.py:30` - `analyze()` returns `list[MorseSymbol]` instead of `Iterator[MorseSymbol]`
- `decoder/morse.py:89` - `decode()` returns `list[DecodedCharacter]` instead of `Iterator[DecodedCharacter]`
- `detection/tone.py:55` - `detect()` returns `list[ToneEvent]` instead of `Iterator[ToneEvent]`

**Root Cause**: Implementations accumulate results in lists for batch processing, but protocols expect streaming iterators.

**Fix Strategy** (Choose one):
1. **Option A - Change implementations to yield**: Convert methods to generators that `yield` items instead of returning lists
   ```python
   # Before
   def detect(self, audio: AudioSample) -> list[ToneEvent]:
       events = []
       # ... processing ...
       return events

   # After
   def detect(self, audio: AudioSample) -> Iterator[ToneEvent]:
       # ... processing ...
       yield event
   ```

2. **Option B - Change protocols to accept lists**: Update protocol definitions to return `Sequence` instead of `Iterator`
   ```python
   # In protocols.py
   def detect(self, audio: AudioSample) -> Sequence[ToneEvent]:  # More flexible
   ```

**Recommendation**: **Option A** - Keep the streaming Iterator design for memory efficiency with large audio streams.

**Estimated Effort**: 4-6 hours

---

## Category 2: AudioSource.read() Signature Mismatches (High Priority)

### Issue: `read()` implementations don't match protocol

**Affected Files**:
- `audio/soundcard.py:38` - `read()` has no `chunk_size` parameter, returns `AudioSample` not `AsyncIterator[AudioSample]`
- `audio/file.py:56` - `read()` has no `chunk_size` parameter, returns `AudioSample | None` not `AsyncIterator[AudioSample]`

**Current Protocol**:
```python
async def read(self, chunk_size: int) -> AsyncIterator[AudioSample]:
```

**Current Implementations**:
```python
# soundcard.py
async def read(self) -> AudioSample:

# file.py
async def read(self) -> AudioSample | None:
```

**Root Cause**: Protocol expects async generator pattern, implementations use single-read pattern.

**Fix Strategy**:
1. **Update implementations** to be async generators:
   ```python
   async def read(self, chunk_size: int) -> AsyncIterator[AudioSample]:
       while True:
           # ... read chunk_size samples ...
           yield sample
   ```

2. **Update call sites** in `pipeline.py` and `cli.py` to use async iteration:
   ```python
   async for sample in audio_source.read(chunk_size=1024):
       # process sample
   ```

**Recommendation**: This is architectural - ensures consistent streaming API across all audio sources.

**Estimated Effort**: 6-8 hours (includes updating call sites and tests)

---

## Category 3: Missing Type Stubs (Low Priority)

### Issue: `sounddevice` library lacks type stubs

**Affected Files**:
- `audio/soundcard.py:79`

**Fix Strategy**:
1. Create local type stubs in `typings/sounddevice.pyi`
2. OR add `# type: ignore[import-untyped]` (temporary)
3. OR switch to `pyaudio` which has better typing support

**Recommendation**: Create minimal local stubs for the methods we actually use.

**Estimated Effort**: 1-2 hours

---

## Category 4: CLI Type Annotations (Medium Priority)

### Issue: Missing type annotations and None checks

**Affected Files**: `cli.py`

**Errors**:
- Line 23, 230: Functions missing type annotations (`no-untyped-def`)
- Lines 81-164: Multiple `union-attr` errors for `window | None`

**Fix Strategy**:
1. Add type annotations to callback functions:
   ```python
   def audio_callback(indata: np.ndarray, frames: int, time: Any, status: Any) -> None:
   ```

2. Add None guards for window operations:
   ```python
   if window is not None:
       window.clear()
       window.box()
       # ... etc
   ```

**Recommendation**: Priority after fixing protocol mismatches.

**Estimated Effort**: 2-3 hours

---

## Category 5: NumPy Type Issues (Low Priority)

### Issue: Float32 vs Float64 type mismatches

**Affected Files**:
- `detection/frequency.py:46, 49` - float32 arrays passed to float64 functions
- `audio/file.py:85, 127, 132` - dtype assignment/conversion issues

**Fix Strategy**:
1. Standardize on `float32` throughout the pipeline (better performance)
2. Add explicit casts where needed:
   ```python
   data.astype(np.float32)
   ```
3. Update function signatures to accept both:
   ```python
   data: npt.NDArray[np.floating[Any]]
   ```

**Recommendation**: Audit the entire data flow and pick one float type consistently.

**Estimated Effort**: 3-4 hours

---

## Category 6: Miscellaneous Issues (Low Priority)

### Various small type issues

**Affected Files**:
- `decoder/morse.py:217` - Return type mismatch for tuple
- `decoder/morse.py:246` - Assignment type mismatch (range vs list)
- `audio/soundcard.py:31` - Field default incompatibility
- `audio/soundcard.py:90` - Missing generic type parameters
- `detection/tone.py:44, 131` - Unused `type: ignore` comments (cleanup)
- `detection/frequency.py:243` - Returning Any from float function
- `pipeline.py:47, 61, 90` - Various type mismatches

**Fix Strategy**: Address individually after main protocol issues are fixed.

**Estimated Effort**: 4-5 hours

---

## Recommended Implementation Plan

### Phase 1: Foundation (Week 1)
**Goal**: Fix protocol signature mismatches

1. ✅ Add `scipy-stubs` to dev dependencies
2. Fix `ToneDetector.detect()` to return Iterator (simplest, good test case)
3. Fix `Decoder.decode()` to return Iterator
4. Fix `TimingAnalyzer.analyze()` to return Iterator
5. Update all call sites to use iterators properly
6. Run full test suite after each change

**Deliverable**: 3 modules removed from overrides

### Phase 2: Audio Sources (Week 2)
**Goal**: Fix AudioSource implementations

1. Refactor `FileSource.read()` to async generator pattern
2. Refactor `SoundcardSource.read()` to async generator pattern
3. Update `pipeline.py` to consume async iterators
4. Update `cli.py` to consume async iterators
5. Add integration tests for async iteration
6. Create `sounddevice` type stubs

**Deliverable**: 2 more modules removed from overrides

### Phase 3: Polish (Week 3)
**Goal**: Clean up remaining issues

1. Fix NumPy type consistency
2. Add CLI type annotations and None guards
3. Fix miscellaneous issues in pipeline.py
4. Clean up unused type ignores
5. Final mypy validation

**Deliverable**: All overrides removed

---

## Testing Strategy

For each fix:
1. Run `mypy src/continuous_wave/<module>.py` to verify fix
2. Run module-specific tests: `pytest tests/test_<module>.py -v`
3. Run integration tests: `pytest tests/ -v`
4. Verify no runtime regressions

---

## Success Criteria

- [ ] All 42 type errors resolved
- [ ] All 8 modules removed from mypy overrides
- [ ] 100% test pass rate maintained
- [ ] No performance regressions
- [ ] Documentation updated

---

## Notes

- The overrides are currently **necessary** - do not remove until errors are fixed
- Protocol design is sound, implementations need refactoring
- Priority should be on high-severity protocol mismatches first
- Consider this a technical debt item, not a blocker
