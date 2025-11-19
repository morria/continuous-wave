# continuous-wave

A modern, testable CW (Morse code) decoder library for Python.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)

## Features

- **Modular Pipeline Architecture**: Clean separation between audio processing, signal detection, and decoding stages
- **Immutable Data Models**: All data structures are frozen dataclasses for thread-safety and predictability
- **Comprehensive Testing**: High test coverage with unit, integration, and property-based tests
- **Type-Safe**: Full type hints with strict mypy checking
- **Configurable**: Flexible configuration with sensible defaults
- **Modern Python**: Built for Python 3.11+ with modern best practices

## Installation

### Using pip

Install the latest version from PyPI (when published):

```bash
pip install continuous-wave
```

### From source

For development or to use the latest version:

```bash
# Clone the repository
git clone https://github.com/morria/continuous-wave.git
cd continuous-wave

# Install in development mode
pip install -e .

# Or install with development dependencies
pip install -e ".[dev]"
```

### Using poetry

```bash
poetry add continuous-wave
```

### Using conda

```bash
# Create a new environment with the required Python version
conda create -n cw python=3.11
conda activate cw

# Install via pip in conda environment
pip install continuous-wave
```

## Quick Start

```python
from continuous_wave import CWConfig, AudioSample
import numpy as np

# Create a configuration
config = CWConfig(
    sample_rate=8000,
    initial_wpm=20.0,
    freq_range=(400.0, 1000.0)
)

# Create an audio sample
audio_data = np.random.randn(1024).astype(np.float32)
sample = AudioSample(
    data=audio_data,
    sample_rate=8000,
    timestamp=0.0
)

print(f"Sample duration: {sample.duration:.3f} seconds")
print(f"Number of samples: {sample.num_samples}")
```

## Dependencies

### Core Dependencies

- **numpy** (>=1.24.0): Numerical computing
- **scipy** (>=1.10.0): Signal processing
- **sounddevice** (>=0.4.6): Audio I/O

### Development Dependencies

Install with `pip install -e ".[dev]"`:

- **pytest** (>=7.4.0): Testing framework
- **pytest-asyncio** (>=0.21.0): Async test support
- **pytest-cov** (>=4.1.0): Code coverage
- **pytest-benchmark** (>=4.0.0): Performance benchmarking
- **hypothesis** (>=6.82.0): Property-based testing
- **mypy** (>=1.5.0): Static type checking
- **ruff** (>=0.0.280): Linting and formatting

### Optional Performance Dependencies

Install with `pip install -e ".[performance]"`:

- **numba** (>=0.57.0): JIT compilation
- **cython** (>=3.0.0): Compiled extensions

## Usage

### Configuration

The library uses a centralized configuration object:

```python
from continuous_wave import CWConfig

# Use defaults
config = CWConfig()

# Or customize settings
config = CWConfig(
    sample_rate=8000,
    chunk_size=256,
    freq_range=(200.0, 1200.0),
    initial_wpm=25.0,
    adaptive_timing=True
)

# Validate frequencies
if config.validate_frequency(800.0):
    print("800 Hz is in range")

# Check WPM range
if config.validate_wpm(20.0):
    print("20 WPM is valid")
```

### Working with Audio Data

```python
from continuous_wave import AudioSample
import numpy as np

# Create an audio sample
data = np.random.randn(1024).astype(np.float32)
sample = AudioSample(
    data=data,
    sample_rate=8000,
    timestamp=0.0
)

# Access properties
print(f"Duration: {sample.duration} seconds")
print(f"Samples: {sample.num_samples}")
```

### Morse Code Elements

```python
from continuous_wave import MorseElement, MorseSymbol

# Work with Morse elements
dot = MorseSymbol(
    element=MorseElement.DOT,
    duration=0.06,  # 60ms
    timestamp=0.0
)

dash = MorseSymbol(
    element=MorseElement.DASH,
    duration=0.18,  # 180ms
    timestamp=0.06
)

print(f"Dot: {dot.element.value}")
print(f"Dash: {dash.element.value}")
```

## Development

### Setting Up Development Environment

```bash
# Clone the repository
git clone https://github.com/morria/continuous-wave.git
cd continuous-wave

# Install with development dependencies
pip install -e ".[dev]"

# Install pre-commit hooks
pip install pre-commit
pre-commit install
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=continuous_wave --cov-report=html

# Run specific test file
pytest tests/unit/test_models.py

# Run with verbose output
pytest -v
```

### Code Quality

```bash
# Type checking
mypy src/continuous_wave

# Linting
ruff check src/continuous_wave

# Format code
ruff format src/continuous_wave

# Run all checks (via Makefile)
make lint
make test
```

## Architecture

The library is organized into modular components:

- **models.py**: Immutable data structures (AudioSample, ToneEvent, MorseSymbol, etc.)
- **config.py**: Configuration management with validation
- **protocols.py**: Protocol definitions for pipeline components
- **audio/**: Audio input/output handling
- **signal/**: Signal processing (filtering, AGC, noise reduction)
- **detection/**: Tone detection and frequency analysis
- **timing/**: WPM detection and timing analysis
- **decoder/**: Morse code decoding logic

See [DESIGN.md](docs/DESIGN.md) for detailed architecture documentation.

## Claude Code Integration

This project includes a comprehensive Claude Code setup for automated code review and quality checking:

### PR Review Agent

Before creating a pull request, use the PR review agent to ensure your code meets all quality standards:

```
/pre-pr
```

The agent will:
- ✅ Run all CI checks (formatting, linting, type checking, tests, build)
- ✅ Critically analyze code quality and maintainability
- ✅ Verify Pythonic patterns and best practices
- ✅ Check file organization and architecture
- ✅ Ensure contributor-friendliness

**Benefits:**
- Catch issues before CI runs
- Get immediate feedback on code quality
- Learn Python best practices
- Faster PR reviews

See [`.claude/README.md`](.claude/README.md) for complete documentation.

## Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](docs/CONTRIBUTING.md) for guidelines.

### Quick Contribution Guide

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run tests and linting (`make test lint`)
5. **(Recommended)** Run PR review if using Claude Code (`/pre-pr`)
6. Commit your changes (`git commit -m 'Add amazing feature'`)
7. Push to the branch (`git push origin feature/amazing-feature`)
8. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Designed for ham radio enthusiasts and Morse code practitioners
- Built with modern Python best practices
- Inspired by traditional CW decoder implementations with a focus on testability

## Links

- **Repository**: https://github.com/morria/continuous-wave
- **Issue Tracker**: https://github.com/morria/continuous-wave/issues
- **Documentation**: [README.md](README.md), [DESIGN.md](docs/DESIGN.md), [CONTRIBUTING.md](docs/CONTRIBUTING.md)
