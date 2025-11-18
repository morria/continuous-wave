#!/usr/bin/env python3
"""Debug script to see what's happening in the decoder."""

import asyncio
from pathlib import Path

from continuous_wave.audio.file import WavFileSource
from continuous_wave.config import CWConfig


async def debug_audio():
    """Debug audio reading and basic processing."""
    config = CWConfig()
    config.sample_rate = 8000
    config.freq_range = (200, 1200)

    audio_source = WavFileSource(config=config, file_path=Path("test_message.wav"))

    chunk_count = 0
    total_samples = 0

    print("Reading audio chunks...")
    async for sample in audio_source:
        chunk_count += 1
        total_samples += sample.num_samples
        max_val = abs(sample.data).max()
        mean_val = abs(sample.data).mean()

        if chunk_count <= 5 or max_val > 0.1:  # Show first 5 chunks or chunks with signal
            print(f"Chunk {chunk_count}:")
            print(f"  Samples: {sample.num_samples}")
            print(f"  Duration: {sample.duration:.3f}s")
            print(f"  Max amplitude: {max_val:.3f}")
            print(f"  Mean amplitude: {mean_val:.3f}")
            print(f"  Timestamp: {sample.timestamp:.3f}")

    audio_source.close()

    print("\n" + "=" * 60)
    print(f"Total chunks: {chunk_count}")
    print(f"Total samples: {total_samples}")
    print(f"Total duration: {total_samples / config.sample_rate:.2f}s")


if __name__ == "__main__":
    asyncio.run(debug_audio())
