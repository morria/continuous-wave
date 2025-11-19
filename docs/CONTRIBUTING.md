# Contributing to Continuous-Wave

Thank you for your interest in contributing to the Continuous-Wave CW parser library! This document provides guidelines and instructions for development.

## Development Environment Setup

### Prerequisites

- Python 3.11 or higher
- Git
- Make (optional, but recommended)

### Quick Start

```bash
# Clone the repository
git clone https://github.com/morria/continuous-wave.git
cd continuous-wave

# Install development dependencies
make install-dev

# Or manually:
pip install -r requirements-dev.txt
pip install -e .

# Verify setup
make test
```

The `.claude/SessionStart` hook will automatically configure your environment when starting a Claude Code session.

## Development Workflow

### Making Changes

1. Create a new branch from `main`:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. Make your changes following our coding standards

3. Run quality checks:
   ```bash
   make pre-commit
   ```

4. Commit your changes:
   ```bash
   git add .
   git commit -m "Add feature: description"
   ```

5. **(Recommended)** Before creating a PR, run the PR review:
   ```
   /pre-pr
   ```
   This catches issues early and ensures your PR will pass CI.

The pre-commit hook will automatically run all checks before allowing the commit.

### Claude Code PR Review Workflow (Recommended!)

**If you're using Claude Code**, we have a specialized PR review agent that catches issues before you create a PR:

1. After completing your task, run the pre-PR review:
   ```
   /pre-pr
   ```

2. The review agent will:
   - Run all CI checks (black, ruff, mypy, pytest, build)
   - Critically analyze your code for quality and maintainability
   - Check file organization and architecture
   - Verify Pythonic patterns and best practices
   - Assess contributor-friendliness

3. Fix any issues identified:
   - **Blocking issues**: Must be fixed before PR
   - **Important issues**: Should be fixed for code quality
   - **Suggestions**: Nice-to-have improvements

4. Create your PR once all checks pass

**Benefits:**
- ✅ Catches all issues that CI would catch
- ✅ Ensures high code quality and maintainability
- ✅ Faster PR reviews (reviewers see clean code)
- ✅ Consistent with project standards
- ✅ Learning tool for Python best practices

For more details, see [`.claude/README.md`](../.claude/README.md).

### Available Make Targets

```bash
make help          # Show all available targets
make install       # Install production dependencies
make install-dev   # Install development dependencies
make test          # Run tests with coverage
make test-verbose  # Run tests with detailed output
make lint          # Run linting checks
make lint-fix      # Auto-fix linting issues
make format        # Format code with black
make type-check    # Run mypy type checking
make pre-commit    # Run all pre-commit checks
make clean         # Clean up generated files
```

## Code Quality Standards

### Type Hints

All code must have complete type hints and pass `mypy` in strict mode:

```python
def process_audio(audio: AudioSample, config: CWConfig) -> AudioSample:
    """Process audio with proper type hints."""
    ...
```

### Code Formatting

- Use `black` for code formatting (line length: 100)
- Use `ruff` for linting
- Both are automatically applied by the pre-commit hook

### Testing

All code must have comprehensive tests:

- **Minimum 90% code coverage** (enforced by CI)
- Unit tests for all public functions
- Integration tests for end-to-end workflows
- Use descriptive test names

```python
def test_agc_normalizes_strong_signal(config: CWConfig) -> None:
    """Test that AGC reduces strong signals to target level."""
    agc = AutomaticGainControl(config)
    # ... test implementation
```

### Documentation

- All public functions must have docstrings
- Use Google-style docstrings:

```python
def process(self, audio: AudioSample) -> AudioSample:
    """Process audio through the filter.

    Args:
        audio: Input audio sample

    Returns:
        Filtered audio sample

    Raises:
        ValueError: If audio sample rate doesn't match filter
    """
    ...
```

### Logging

Use the structured logging module for all logging:

```python
from continuous_wave.logging import get_logger

logger = get_logger(__name__)

def process_data(data: np.ndarray) -> None:
    logger.debug(f"Processing {len(data)} samples")
    logger.info("Processing complete")
    logger.error("Failed to process data", exc_info=True)
```

## Architecture Principles

This library follows strict architectural principles:

### 1. Dependency Injection

All components accept dependencies via constructor:

```python
class NoiseReductionPipeline:
    def __init__(
        self,
        config: CWConfig,
        agc: Optional[AutomaticGainControl] = None,
    ) -> None:
        self.agc = agc or AutomaticGainControl(config)
```

### 2. Protocol-Based Interfaces

Use `typing.Protocol` for duck typing:

```python
class AudioSource(Protocol):
    async def read(self, chunk_size: int) -> AsyncIterator[AudioSample]:
        ...
```

### 3. Immutable Data Models

All data structures are frozen dataclasses:

```python
@dataclass(frozen=True)
class AudioSample:
    data: npt.NDArray[np.float32]
    sample_rate: int
    timestamp: float
```

### 4. Pure Functions

Prefer stateless functions where possible. If state is needed, make it explicit.

### 5. Testability First

Design code to be easily testable with mocks and fixtures.

## Pre-Commit Checks

### Automatic GitHub Workflow Enforcement

**A git pre-commit hook is automatically active** at `.git/hooks/pre-commit` that runs the **exact same checks as GitHub CI**. This ensures that Claude Code and all developers cannot commit code that would fail in CI.

The pre-commit hook runs all 5 GitHub workflow checks:

1. **Black formatting check** - `black --check src/ tests/`
2. **Ruff linting** - `ruff check src/ tests/`
3. **MyPy type checking** - `python -m mypy src/continuous_wave --strict`
4. **Pytest with coverage** - `pytest tests/ -v --cov=continuous_wave --cov-report=term-missing --cov-report=xml --cov-fail-under=90`
5. **Package build** - `python -m build`

### What Happens When You Commit

When you run `git commit`, the hook will:
- ✅ Run all 5 checks automatically
- ✅ Show clear output for each check
- ✅ Allow the commit if all checks pass
- ❌ Block the commit if any check fails
- 💡 Suggest quick fixes (`make format`, `make lint-fix`, etc.)

### Example Output

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   Pre-Commit: Running GitHub Workflow Checks
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[Black Format Check] Running...
✓ [Black Format Check] Passed

[Ruff Linting] Running...
✓ [Ruff Linting] Passed

[MyPy Type Check] Running...
✓ [MyPy Type Check] Passed

[Pytest Coverage] Running...
✓ [Pytest Coverage] Passed

[Build Package] Running...
✓ [Build Package] Passed

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✓ All GitHub workflow checks passed!
✓ Commit is allowed to proceed.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### Bypassing the Hook (NOT Recommended)

If absolutely necessary, you can bypass the hook with:

```bash
git commit --no-verify
```

**WARNING:** Bypassing will result in CI failure and your PR cannot be merged.

## Continuous Integration

GitHub Actions runs automatically on:
- All pushes to `main`, `master`, `develop`
- All pull requests

The CI pipeline runs:
- Linting
- Type checking
- Tests on Python 3.11 and 3.12
- Package building

**Pull requests cannot be merged if CI fails.**

## Project Structure

```
continuous-wave/
├── src/continuous_wave/     # Source code
│   ├── models.py            # Data models
│   ├── protocols.py         # Protocol definitions
│   ├── config.py            # Configuration
│   ├── logging.py           # Logging setup
│   ├── signal/              # Signal processing
│   │   └── noise.py         # Noise reduction
│   ├── detection/           # Signal detection
│   ├── timing/              # Timing analysis
│   └── decoder/             # Morse decoding
├── tests/                   # Tests
│   ├── unit/                # Unit tests
│   ├── integration/         # Integration tests
│   ├── performance/         # Performance tests
│   └── conftest.py          # Pytest configuration
├── .claude/                 # Claude Code configuration
│   └── SessionStart         # Session initialization
├── .github/workflows/       # CI/CD workflows
└── docs/                    # Documentation
```

## Testing Guidelines

### Writing Tests

```python
class TestAutomaticGainControl:
    """Tests for AGC component."""

    def test_normalizes_strong_signal(self, config: CWConfig) -> None:
        """Test that AGC reduces strong signals."""
        # Arrange
        agc = AutomaticGainControl(config)
        strong_signal = np.ones(1000, dtype=np.float32) * 2.0

        # Act
        output = agc.process(AudioSample(...))

        # Assert
        assert np.max(np.abs(output.data)) < 1.5
```

### Running Tests

```bash
# Run all tests
make test

# Run specific test file
pytest tests/unit/test_agc.py -v

# Run specific test
pytest tests/unit/test_agc.py::TestAutomaticGainControl::test_normalizes_strong_signal -v

# Run with detailed output
make test-verbose

# Run with coverage report
pytest tests/ --cov=continuous_wave --cov-report=html
open htmlcov/index.html
```

## Debugging with Claude Code

The project is optimized for Claude Code:

1. **Detailed logging**: All operations log their progress
2. **Clear test output**: Test failures show exactly what went wrong
3. **Type hints**: Claude can understand the codebase structure
4. **Comprehensive docs**: All functions are well-documented

When debugging:
- Check test output for specific failure reasons
- Use `pytest -vv` for extra verbosity
- Check logs in test output
- Use `make test-verbose` for HTML coverage reports

## Release Process

1. Update version in `pyproject.toml`
2. Update `CHANGELOG.md`
3. Create a git tag:
   ```bash
   git tag -a v0.1.0 -m "Release v0.1.0"
   git push origin v0.1.0
   ```
4. GitHub Actions will build and publish to PyPI

## Getting Help

- Check the [DESIGN.md](DESIGN.md) for architecture details
- Review existing code for examples
- Ask questions in GitHub Issues

## Code of Conduct

- Be respectful and inclusive
- Focus on the technical merits
- Help others learn and improve

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
