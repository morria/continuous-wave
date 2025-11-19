# Troubleshooting Guide

This guide covers common issues you might encounter when developing continuous-wave and how to resolve them.

## Table of Contents

- [Setup Issues](#setup-issues)
- [Pre-Commit Hook Issues](#pre-commit-hook-issues)
- [Type Checking Issues](#type-checking-issues)
- [Testing Issues](#testing-issues)
- [Build Issues](#build-issues)
- [Audio Device Issues](#audio-device-issues)
- [Platform-Specific Issues](#platform-specific-issues)

---

## Setup Issues

### Problem: `pip install -e .` fails with dependency errors

**Symptoms:**
```
ERROR: Could not find a version that satisfies the requirement numpy>=1.24.0
```

**Solution:**
1. Ensure you're using Python 3.11 or higher:
   ```bash
   python --version
   ```

2. Upgrade pip:
   ```bash
   pip install --upgrade pip
   ```

3. Install dependencies separately:
   ```bash
   pip install -r requirements-dev.txt
   pip install -e .
   ```

---

### Problem: Pre-commit hook not found after installation

**Symptoms:**
```bash
git commit
# No pre-commit checks run
```

**Solution:**
Manually reinstall the hooks:
```bash
./hooks/install-hooks.sh
```

Verify the hook is installed:
```bash
ls -la .git/hooks/pre-commit
```

---

### Problem: Virtual environment not activating

**Symptoms:**
```
Command 'python' not found
```

**Solution:**

**Linux/macOS:**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

**Windows:**
```bash
python -m venv .venv
.venv\Scripts\activate
```

---

## Pre-Commit Hook Issues

### Problem: Pre-commit checks take too long (>60 seconds)

**Solution:**
Use quick mode for faster commits during development:
```bash
QUICK_MODE=1 git commit -m "WIP: feature development"
```

Quick mode runs only formatting and linting (5-10 seconds), skipping type checking and tests.

Before creating a PR, always run full checks:
```bash
make pre-commit
```

---

### Problem: Hook fails with "command not found"

**Symptoms:**
```
./git/hooks/pre-commit: line 25: black: command not found
```

**Solution:**
1. Ensure you're in a virtual environment:
   ```bash
   which python
   # Should show: /path/to/continuous-wave/.venv/bin/python
   ```

2. Reinstall development dependencies:
   ```bash
   pip install -r requirements-dev.txt
   ```

3. If still failing, deactivate and reactivate your virtual environment:
   ```bash
   deactivate
   source .venv/bin/activate
   ```

---

### Problem: Want to bypass pre-commit hook temporarily

**Solution:**
```bash
git commit --no-verify -m "message"
```

**⚠️ WARNING:** Bypassing the hook will likely cause CI to fail. Only use this if you know what you're doing.

---

## Type Checking Issues

### Problem: MyPy reports type errors in my code

**Symptoms:**
```
src/continuous_wave/myfile.py:42: error: Argument 1 has incompatible type "float"; expected "int"
```

**Solution:**

1. **Fix the type issue** (preferred):
   ```python
   # Before
   def process(value: int) -> None:
       ...
   process(3.14)  # Type error!

   # After
   def process(value: float) -> None:  # Widen the type
       ...
   process(3.14)  # OK
   ```

2. **Add type narrowing** if you're sure the type is correct:
   ```python
   from typing import cast

   result = cast(int, some_value)
   ```

3. **Use type: ignore as a last resort**:
   ```python
   result = some_complex_function()  # type: ignore[return-value]
   ```

---

### Problem: MyPy complains about third-party library types

**Symptoms:**
```
error: Skipping analyzing "some_library": module is installed, but missing library stubs or py.typed marker
```

**Solution:**

1. Check if type stubs are available:
   ```bash
   pip search types-some-library
   ```

2. Install type stubs if available:
   ```bash
   pip install types-some-library
   ```

3. If no stubs exist, add to `pyproject.toml`:
   ```toml
   [[tool.mypy.overrides]]
   module = "some_library.*"
   ignore_missing_imports = true
   ```

---

### Problem: Too many type errors, want to check incrementally

**Solution:**
Use the granular type checking script:
```bash
# Check only files without existing overrides
./scripts/check-types.sh lenient

# Normal checking (current state)
./scripts/check-types.sh normal

# Strict checking (zero tolerance)
./scripts/check-types.sh strict
```

---

## Testing Issues

### Problem: Test coverage below 90%

**Symptoms:**
```
FAILED tests/ - AssertionError: Coverage is 87.5%, minimum is 90%
```

**Solution:**

1. **Identify uncovered lines**:
   ```bash
   make test-verbose
   open htmlcov/index.html  # View detailed coverage report
   ```

2. **Add tests for uncovered lines**:
   - Red lines in the HTML report need test coverage
   - Focus on branches (if/else) and error handling

3. **Run coverage for specific file**:
   ```bash
   pytest tests/test_myfile.py --cov=continuous_wave.mymodule --cov-report=term-missing
   ```

---

### Problem: Tests pass locally but fail in CI

**Common Causes:**

1. **Platform differences** (Linux vs macOS/Windows)
   - Use `sys.platform` checks if needed
   - Mock platform-specific code

2. **Missing test dependencies**
   - Ensure all test deps are in `requirements-dev.txt`

3. **Floating-point precision**
   - Use `pytest.approx()` for float comparisons:
     ```python
     assert result == pytest.approx(expected, rel=1e-6)
     ```

4. **Random test failures**
   - Set random seeds in tests
   - Use `hypothesis` for property-based testing

---

### Problem: Async tests failing with "RuntimeWarning: coroutine was never awaited"

**Solution:**
Ensure you're using `pytest-asyncio` decorators:
```python
import pytest

@pytest.mark.asyncio
async def test_async_function() -> None:
    result = await some_async_function()
    assert result == expected
```

---

### Problem: Audio device errors during testing

**Symptoms:**
```
sounddevice.PortAudioError: Error opening audio device
```

**Solution:**
Mock audio devices in tests:
```python
from unittest.mock import MagicMock, patch

@patch('sounddevice.InputStream')
def test_audio_processing(mock_stream: MagicMock) -> None:
    mock_stream.return_value.__enter__.return_value.read.return_value = (
        np.zeros((1024, 1), dtype=np.float32),
        False  # overflow flag
    )
    # Test code here
```

For integration tests, use the `--no-audio` flag if available.

---

## Build Issues

### Problem: Build fails with "No module named 'setuptools'"

**Solution:**
```bash
pip install --upgrade setuptools wheel build
```

---

### Problem: Build includes unwanted files

**Solution:**
Check `MANIFEST.in` and `.gitignore`:
```bash
# Clean build artifacts
make clean

# Rebuild
make build

# Inspect contents
tar -tzf dist/*.tar.gz
```

---

## Audio Device Issues

### Problem: No audio devices found

**Symptoms:**
```
sounddevice.PortAudioError: No input devices found
```

**Solution:**

**Linux:**
```bash
# Install ALSA development files
sudo apt-get install libasound2-dev portaudio19-dev

# Or PulseAudio
sudo apt-get install pulseaudio
```

**macOS:**
```bash
# Install PortAudio
brew install portaudio
```

**Windows:**
- Ensure microphone permissions are enabled in Windows Settings
- Update audio drivers

---

### Problem: Audio crackling or buffer underruns

**Solution:**
Increase buffer size in configuration:
```python
config = CWConfig(
    sample_rate=48000,
    chunk_size=2048,  # Increase from default 1024
)
```

---

## Platform-Specific Issues

### Linux: Permission denied for audio devices

**Solution:**
Add your user to the `audio` group:
```bash
sudo usermod -aG audio $USER
# Log out and log back in
```

---

### macOS: "ModuleNotFoundError" after installation

**Solution:**
Ensure `PYTHONPATH` is set correctly:
```bash
export PYTHONPATH="${PYTHONPATH}:$(pwd)/src"
```

Or use the installed package:
```bash
pip install -e .
python -c "import continuous_wave; print(continuous_wave.__version__)"
```

---

### Windows: Git pre-commit hook not executing

**Solution:**
Git for Windows should handle bash scripts automatically. If not:

1. Install Git Bash (included with Git for Windows)
2. Ensure line endings are correct:
   ```bash
   git config core.autocrlf input
   ```

3. Reinstall hooks:
   ```bash
   ./hooks/install-hooks.sh
   ```

---

## CI/CD Issues

### Problem: GitHub Actions failing but local checks pass

**Solution:**

1. **Run the same checks locally**:
   ```bash
   make ci
   ```

2. **Check Python version**:
   CI tests multiple Python versions (3.11, 3.12). Test with the failing version:
   ```bash
   pyenv install 3.12
   pyenv local 3.12
   make test
   ```

3. **Check GitHub Actions logs**:
   - Click on the failing workflow in GitHub
   - Expand the failing step
   - Look for specific error messages

---

### Problem: Pre-PR review identifies issues missed locally

**Solution:**
Always run the pre-PR review before creating a PR:
```bash
/pre-pr
```

This runs the same comprehensive checks as the PR review agent.

---

## Getting More Help

If you're still stuck:

1. **Check existing issues**: [GitHub Issues](https://github.com/morria/continuous-wave/issues)
2. **Search closed issues**: Someone may have had the same problem
3. **Create a new issue**: Include:
   - Python version (`python --version`)
   - OS and version
   - Full error message
   - Steps to reproduce
   - What you've already tried

---

## Quick Reference: Common Fixes

```bash
# Fix formatting issues
make format

# Fix linting issues
make lint-fix

# Fix all auto-fixable issues
make fix

# Clean build artifacts
make clean

# Reinstall everything
make clean
pip install -r requirements-dev.txt
pip install -e .
./hooks/install-hooks.sh

# Run all checks (what CI runs)
make ci

# Fast commit (development only)
QUICK_MODE=1 git commit -m "WIP: message"

# Full pre-commit (before PR)
make pre-commit
```

---

## Prevention Tips

1. **Always use a virtual environment**
2. **Keep dependencies up to date**: `pip install --upgrade -r requirements-dev.txt`
3. **Run tests frequently**: `make test` (or use `pytest-watch`)
4. **Use quick mode during development**: `QUICK_MODE=1 git commit`
5. **Run full pre-commit before PR**: `make pre-commit`
6. **Use the `/pre-pr` review** before creating pull requests

---

*Last updated: 2025-11-19*
