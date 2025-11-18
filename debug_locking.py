#!/usr/bin/env python3
"""Debug frequency locking behavior."""

import asyncio
from pathlib import Path

from continuous_wave.audio.file import WavFileSource
from continuous_wave.config import CWConfig
from continuous_wave.detection.frequency import FrequencyDetectorImpl
from continuous_wave.signal.noise import NoiseReductionPipeline


async def debug_locking():
    """Debug frequency locking."""
    config = CWConfig()
    config.sample_rate = 8000
    config.freq_range = (200, 1200)
    config.min_snr_db = 3.0

    audio_source = WavFileSource(config=config, file_path=Path("test_message.wav"))
    noise_pipeline = NoiseReductionPipeline(config=config)
    freq_detector = FrequencyDetectorImpl(config=config)

    print("Debugging frequency locking...")
    print("=" * 60)

    chunk_num = 0
    was_locked = False

    async for audio_sample in audio_source:
        chunk_num += 1
        cleaned = noise_pipeline.process(audio_sample)
        freq_stats = freq_detector.detect(cleaned)

        is_locked = freq_detector.is_locked

        # Show lock state changes
        if is_locked != was_locked:
            if is_locked:
                print(f"\nChunk {chunk_num}: *** LOCKED ***")
                if freq_stats:
                    print(f"  Locked frequency: {freq_stats.frequency:.1f} Hz")
            else:
                print(f"\nChunk {chunk_num}: *** UNLOCKED ***")
            was_locked = is_locked

        # Show detections when not locked
        if not is_locked and freq_stats and chunk_num < 100:
            print(f"Chunk {chunk_num}: freq={freq_stats.frequency:.1f} Hz, "
                  f"SNR={freq_stats.snr_db:.1f} dB, "
                  f"lock_count={freq_detector._lock_count}")

    audio_source.close()

    print("\n" + "=" * 60)
    print(f"Total chunks: {chunk_num}")
    print(f"Final lock state: {'LOCKED' if is_locked else 'UNLOCKED'}")
    if freq_detector._current_frequency:
        print(f"Final frequency: {freq_detector._current_frequency:.1f} Hz")


if __name__ == "__main__":
    asyncio.run(debug_locking())
