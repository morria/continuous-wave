"""Pytest configuration and fixtures."""

import logging

import numpy as np
import pytest

from continuous_wave.config import CWConfig
from continuous_wave.logging import setup_logging
from continuous_wave.models import AudioSample


# Configure logging for tests
def pytest_configure(config: pytest.Config) -> None:
    """Configure pytest with enhanced logging for better visibility."""
    # Set up detailed logging for tests
    setup_logging(
        level=logging.DEBUG,
        format_string="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        use_color=True,
    )


@pytest.fixture
def config() -> CWConfig:
    """Provide a default configuration for testing."""
    return CWConfig()


@pytest.fixture
def sample_audio_chunk() -> AudioSample:
    """Provide a sample audio chunk for testing.

    Returns:
        AudioSample with random noise data
    """
    return AudioSample(
        data=np.random.randn(1024).astype(np.float32),
        sample_rate=8000,
        timestamp=0.0,
    )


@pytest.fixture
def sine_wave_audio(config: CWConfig) -> AudioSample:
    """Provide a sine wave audio sample for testing.

    Args:
        config: Configuration object

    Returns:
        AudioSample containing a 600 Hz sine wave
    """
    num_samples = 1024
    frequency = 600.0
    t = np.arange(num_samples) / config.sample_rate
    data = np.sin(2 * np.pi * frequency * t).astype(np.float32)

    return AudioSample(
        data=data,
        sample_rate=config.sample_rate,
        timestamp=0.0,
    )


@pytest.fixture
def silent_audio(config: CWConfig) -> AudioSample:
    """Provide a silent audio sample for testing.

    Args:
        config: Configuration object

    Returns:
        AudioSample containing zeros
    """
    return AudioSample(
        data=np.zeros(1024, dtype=np.float32),
        sample_rate=config.sample_rate,
        timestamp=0.0,
    )
