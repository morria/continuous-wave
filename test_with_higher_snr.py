#!/usr/bin/env python3
"""Test decoding with higher SNR threshold."""

import asyncio
from pathlib import Path

from continuous_wave.audio.file import WavFileSource
from continuous_wave.config import CWConfig
from continuous_wave.decoder.morse import MorseDecoder
from continuous_wave.detection.frequency import FrequencyDetectorImpl
from continuous_wave.detection.tone import EnvelopeDetector
from continuous_wave.pipeline import CWDecoderPipeline
from continuous_wave.signal.noise import NoiseReductionPipeline
from continuous_wave.timing.adaptive import AdaptiveWPMDetector


async def test_decode():
    """Test decoding with higher SNR threshold."""
    # Create configuration with higher SNR threshold
    config = CWConfig()
    config.sample_rate = 8000
    config.freq_range = (200, 1200)
    config.min_snr_db = 20.0  # Much higher SNR threshold to ignore silence

    # Create pipeline components
    audio_source = WavFileSource(config=config, file_path=Path("test_message.wav"))
    noise_pipeline = NoiseReductionPipeline(config=config)
    freq_detector = FrequencyDetectorImpl(config=config)
    tone_detector = EnvelopeDetector(config=config)
    timing_analyzer = AdaptiveWPMDetector(config=config)
    decoder = MorseDecoder(config=config)

    # Create pipeline
    pipeline = CWDecoderPipeline(
        config=config,
        audio_source=audio_source,
        noise_pipeline=noise_pipeline,
        frequency_detector=freq_detector,
        tone_detector=tone_detector,
        timing_analyzer=timing_analyzer,
        decoder=decoder,
    )

    print("Starting decoder with SNR threshold = 20 dB...")
    print("Expected message: HELLO WORLD")
    print("=" * 60)

    decoded_text = ""
    char_count = 0

    try:
        async for char, state in pipeline.run():
            decoded_text += char.char
            char_count += 1
            print(f"{char.char}", end="", flush=True)

    except Exception as e:
        print(f"\nError during decoding: {e}")
        import traceback
        traceback.print_exc()

    finally:
        audio_source.close()

    print("\n" + "=" * 60)
    print(f"Decoded text: '{decoded_text}'")
    print(f"Expected:     'HELLO WORLD'")
    print(f"Match: {decoded_text.strip() == 'HELLO WORLD'}")
    print(f"Total characters: {char_count}")


if __name__ == "__main__":
    asyncio.run(test_decode())
