#!/usr/bin/env python3
"""Test frequency detector directly."""

import asyncio
from pathlib import Path

from continuous_wave.audio.file import WavFileSource
from continuous_wave.config import CWConfig
from continuous_wave.detection.frequency import FrequencyDetectorImpl


async def test_freq_detector():
    """Test frequency detection without noise pipeline."""
    config = CWConfig()
    config.sample_rate = 8000
    config.freq_range = (200, 1200)
    config.min_snr_db = 3.0

    audio_source = WavFileSource(config=config, file_path=Path("test_message.wav"))
    freq_detector = FrequencyDetectorImpl(config=config)

    print("Testing frequency detector directly (no noise pipeline)...")
    print("=" * 60)

    chunk_num = 0
    detections = []

    async for audio_sample in audio_source:
        chunk_num += 1
        freq_stats = freq_detector.detect(audio_sample)

        if freq_stats is not None:
            detections.append(freq_stats.frequency)
            if len(detections) <= 10:  # Show first 10 detections
                print(f"Chunk {chunk_num}:")
                print(f"  Frequency: {freq_stats.frequency:.1f} Hz")
                print(f"  SNR: {freq_stats.snr_db:.1f} dB")
                print(f"  Power: {freq_stats.power:.3f}")
                print(f"  Locked: {freq_detector.is_locked}")

    audio_source.close()

    print("\n" + "=" * 60)
    print(f"Total chunks: {chunk_num}")
    print(f"Detections: {len(detections)}")
    if detections:
        print(f"Average frequency: {sum(detections) / len(detections):.1f} Hz")
        print(f"Min frequency: {min(detections):.1f} Hz")
        print(f"Max frequency: {max(detections):.1f} Hz")


if __name__ == "__main__":
    asyncio.run(test_freq_detector())
