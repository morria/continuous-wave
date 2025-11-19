# Claude Code Work Plan Index

This directory contains plans and tracking documents for Claude Code to complete the continuous-wave decoder project. Work items are organized by priority and complexity.

## How to Use This Index

Each plan file contains detailed information about specific work areas. Claude Code should:
1. Read the relevant plan file before starting work
2. Check off items in this index as they are completed
3. Focus on HIGH priority items first
4. Complete all items in a section before moving to the next

## Priority 1: CRITICAL BLOCKERS

These issues prevent the core functionality from working. Must be completed first.

### Decoder Fixes (DECODER_FIXES_NEEDED.md)

**Status:** Not Started
**Estimated Effort:** 1-2 days
**Blocking:** All integration tests (15 tests skipped)

- [ ] Investigate why timing analyzer fails to lock
- [ ] Fix timestamp propagation in ToneEvent objects
- [ ] Add debug logging to AdaptiveWPMDetector
- [ ] Create minimal test case with known timing patterns
- [ ] Verify lock thresholds and state machine logic
- [ ] Ensure timing analyzer generates morse symbols after lock
- [ ] Validate all 15 integration tests pass

**Key Files:**
- `src/continuous_wave/timing/adaptive.py` - Timing analyzer
- `src/continuous_wave/pipeline.py` - Event timestamp propagation
- `src/continuous_wave/detection/tone.py` - ToneEvent creation
- `tests/integration/test_wav_decoding.py` - Skipped tests

**Success Criteria:**
- Timing analyzer reliably locks on 20 WPM morse code
- All 15 skipped integration tests pass
- Full end-to-end decoding: Audio → Characters

---

## Priority 2: HIGH IMPACT IMPROVEMENTS

These improve code quality, maintainability, and developer experience.

### Type Safety (TYPING_ISSUES.md)

**Status:** Not Started
**Estimated Effort:** 2-3 weeks
**Blocking:** Strict type checking, code quality claims

**Phase 1: Protocol Signature Mismatches (Week 1)**
- [ ] Fix ToneDetector.detect() to return Iterator
- [ ] Fix Decoder.decode() to return Iterator
- [ ] Fix TimingAnalyzer.analyze() to return Iterator
- [ ] Update all call sites to use iterators properly
- [ ] Run full test suite after each change

**Phase 2: Audio Source Implementations (Week 2)**
- [ ] Refactor FileSource.read() to async generator pattern
- [ ] Refactor SoundcardSource.read() to async generator pattern
- [ ] Update pipeline.py to consume async iterators
- [ ] Update cli.py to consume async iterators
- [ ] Add integration tests for async iteration
- [ ] Create sounddevice type stubs

**Phase 3: Polish (Week 3)**
- [ ] Fix NumPy type consistency (float32 vs float64)
- [ ] Add CLI type annotations and None guards
- [ ] Fix miscellaneous issues in pipeline.py
- [ ] Clean up unused type ignores
- [ ] Final mypy validation
- [ ] Remove all modules from mypy overrides

**Key Files:**
- `src/continuous_wave/detection/tone.py`
- `src/continuous_wave/decoder/morse.py`
- `src/continuous_wave/timing/adaptive.py`
- `src/continuous_wave/audio/file.py`
- `src/continuous_wave/audio/soundcard.py`
- `src/continuous_wave/pipeline.py`
- `src/continuous_wave/cli.py`
- `pyproject.toml` - mypy configuration

**Success Criteria:**
- All 42 type errors resolved
- All 8 modules removed from mypy overrides
- 100% test pass rate maintained
- No performance regressions

---

## Priority 3: INFRASTRUCTURE & QUALITY

These ensure the project is maintainable and performs well.

### Performance Optimization

**Status:** Not Started
**Estimated Effort:** 8-12 hours
**Reference:** CODEBASE_REVIEW_REPORT.md Section 2.1

- [ ] Add pytest-benchmark performance tests
- [ ] Benchmark Goertzel algorithm (target: <10ms for 1024 samples)
- [ ] Optimize Goertzel with Numba JIT if needed
- [ ] Benchmark AGC processing
- [ ] Optimize AGC with vectorization if needed
- [ ] Document performance characteristics
- [ ] Add performance requirements to documentation

**Key Files:**
- `src/continuous_wave/detection/frequency.py` - Goertzel algorithm
- `src/continuous_wave/signal/noise.py` - AGC processing
- `tests/performance/` - Add benchmark tests

**Success Criteria:**
- Goertzel: <10ms for 1024 samples
- Full pipeline: <100ms for 1-second audio
- Performance tests in CI

### Project Organization

**Status:** Not Started
**Estimated Effort:** 1-2 hours
**Reference:** CODEBASE_REVIEW_REPORT.md Section 2.2

- [ ] Create examples/ directory
- [ ] Move debug scripts to examples/
- [ ] Create tools/ directory
- [ ] Move generate_morse_wav.py to tools/
- [ ] Move test_*.wav files to tests/integration/fixtures/wav_files/
- [ ] Delete redundant test scripts from root
- [ ] Update DESIGN.md references to examples/
- [ ] Update README.md with new structure

**Success Criteria:**
- Clean root directory (only config files and essential docs)
- All scripts in appropriate directories
- Updated documentation

### Error Handling & Logging

**Status:** Not Started
**Estimated Effort:** 4-6 hours
**Reference:** CODEBASE_REVIEW_REPORT.md Section 3.2

- [ ] Add logging for soundcard callback status errors
- [ ] Add validation for audio sample size before DSP operations
- [ ] Add ValueError for invalid configuration combinations
- [ ] Add proper exception handling in async iterators
- [ ] Document expected exceptions in docstrings
- [ ] Test error paths with unit tests

**Key Files:**
- `src/continuous_wave/audio/soundcard.py` - Callback error handling
- All modules - Input validation

---

## Priority 4: DOCUMENTATION & POLISH

These improve the developer and user experience.

### Public API Design

**Status:** Not Started
**Estimated Effort:** 4-6 hours
**Reference:** CODEBASE_REVIEW_REPORT.md Section 2.3

- [ ] Design high-level CWDecoder API
- [ ] Implement convenience wrappers
- [ ] Export pipeline components in __init__.py
- [ ] Export factory functions for common configurations
- [ ] Create examples/library_usage.py
- [ ] Add library usage examples to README
- [ ] Update documentation with API examples

**Success Criteria:**
- Simple high-level API for common use cases
- Clear library usage examples
- Comprehensive __init__.py exports

### Documentation Improvements

**Status:** Not Started
**Estimated Effort:** 6-8 hours
**Reference:** CODEBASE_REVIEW_REPORT.md Section 3.4

- [ ] Set up Sphinx documentation
- [ ] Generate API reference from docstrings
- [ ] Create examples/basic_usage.py
- [ ] Create examples/custom_pipeline.py
- [ ] Create examples/synthetic_testing.py
- [ ] Document algorithm choices vs alternatives
- [ ] Add performance comparison table
- [ ] Publish documentation

**Success Criteria:**
- Complete API reference documentation
- Multiple working examples
- Algorithm design rationale documented

---

## Reference Documents

### Workflow Checks (WORKFLOW_CHECKS.md)

**Purpose:** Reference guide for running CI checks locally
**Use When:** Before committing changes, debugging CI failures

This document lists all GitHub CI checks and the exact local commands to reproduce them:
- Black formatting check
- Ruff linting
- MyPy type checking
- Pytest with coverage (90% minimum)
- Package build

**Quick Commands:**
```bash
make pre-commit      # Run all checks
make format          # Auto-fix Black issues
make lint-fix        # Auto-fix Ruff issues
make test            # Run tests with coverage
```

### Codebase Review (CODEBASE_REVIEW_REPORT.md)

**Purpose:** Comprehensive analysis of codebase quality and improvement areas
**Use When:** Planning major refactoring, understanding technical debt

This document contains:
- Executive summary of codebase quality
- Detailed analysis of all issues (Critical → Low priority)
- Comparison with industry standards (fldigi)
- 3-week implementation roadmap
- Metrics and success criteria

---

## Progress Tracking

### Overall Status

- **Critical Blockers:** 0/1 complete (0%)
- **Type Safety:** 0/15 complete (0%)
- **Infrastructure:** 0/3 sections complete (0%)
- **Documentation:** 0/2 sections complete (0%)

### Last Updated

2025-11-19 - Initial index created

---

## Notes for Claude Code

### Using the Next Task Agent

The **Next Task Agent** is an automated system that intelligently selects and executes the next most important task from this index.

**Quick Start:**
```bash
# See all available tasks
python scripts/next_task_agent.py --list

# Preview the next task
python scripts/next_task_agent.py --dry-run

# Execute the next task (in Claude Code)
/next-task
```

**Documentation:** See `.claude/NEXT_TASK_AGENT.md` for complete usage guide.

The agent will:
1. Select the highest priority "Not Started" task
2. Read the detailed plan file
3. Create and execute an implementation plan
4. Run all tests and validation
5. Update this INDEX.md with progress
6. Create a pull request

### Work Prioritization

1. **Start with DECODER_FIXES_NEEDED.md** - This is blocking all integration tests
2. **Then tackle TYPING_ISSUES.md Phase 1** - Quick wins for type safety
3. **Clean up project organization** - Low effort, high visibility improvement
4. **Add performance benchmarks** - Measure before optimizing
5. **Complete remaining type safety work** - Phases 2-3
6. **Polish and document** - Final touches

### When Starting a Task

1. Read the relevant plan file completely
2. Check prerequisites (are blocking tasks complete?)
3. Review the key files mentioned
4. Create a subtask list if the task is complex
5. Check off items in this index as you complete them

### When Completing a Task

1. Update this index with checkmarks
2. Run `make pre-commit` to verify all checks pass
3. Update "Last Updated" timestamp
4. Commit changes with descriptive message

### Getting Help

If you need clarification on any plan:
- Check CODEBASE_REVIEW_REPORT.md for context
- Check WORKFLOW_CHECKS.md for testing procedures
- Check docs/DESIGN.md for architecture details
- Check docs/CONTRIBUTING.md for contribution guidelines
