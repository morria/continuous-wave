#!/usr/bin/env python3
"""Debug script to trace through the pipeline stages."""

import asyncio
from pathlib import Path

from continuous_wave.audio.file import WavFileSource
from continuous_wave.config import CWConfig
from continuous_wave.decoder.morse import MorseDecoder
from continuous_wave.detection.frequency import FrequencyDetectorImpl
from continuous_wave.detection.tone import EnvelopeDetector
from continuous_wave.signal.noise import NoiseReductionPipeline
from continuous_wave.timing.adaptive import AdaptiveWPMDetector


async def debug_pipeline():
    """Debug each stage of the pipeline."""
    # Create configuration with more lenient settings
    config = CWConfig()
    config.sample_rate = 8000
    config.freq_range = (200, 1200)
    config.min_snr_db = 3.0  # Lower SNR threshold
    config.squelch_threshold = 0.01  # Lower squelch threshold

    # Create components
    audio_source = WavFileSource(config=config, file_path=Path("test_message.wav"))
    noise_pipeline = NoiseReductionPipeline(config=config)
    freq_detector = FrequencyDetectorImpl(config=config)
    tone_detector = EnvelopeDetector(config=config)
    timing_analyzer = AdaptiveWPMDetector(config=config)
    decoder = MorseDecoder(config=config)

    print("Debugging pipeline stages...")
    print("=" * 60)

    chunk_num = 0
    freq_detections = 0
    tone_events = 0
    morse_symbols = 0
    decoded_chars = 0

    async for audio_sample in audio_source:
        chunk_num += 1

        # Stage 1: Noise reduction
        cleaned = noise_pipeline.process(audio_sample)

        # Stage 2: Frequency detection
        freq_stats = freq_detector.detect(cleaned)
        if freq_stats is not None:
            freq_detections += 1
            if freq_detections <= 3:  # Show first 3 detections
                print(f"\nChunk {chunk_num}: Frequency detected!")
                print(f"  Frequency: {freq_stats.frequency:.1f} Hz")
                print(f"  SNR: {freq_stats.snr_db:.1f} dB")
                print(f"  Power: {freq_stats.power:.3f}")
                print(f"  Locked: {freq_detector.is_locked}")

            # Stage 3: Tone detection (only if locked)
            if freq_detector.is_locked:
                events = tone_detector.detect(cleaned)
                if events:
                    tone_events += len(events)
                    if tone_events <= 5:  # Show first few events
                        for event in events:
                            state_str = "ON" if event.is_tone_on else "OFF"
                            print(f"  Tone event: {state_str}, amplitude: {event.amplitude:.3f}")

                    # Stage 4: Timing analysis
                    for event in events:
                        symbols = timing_analyzer.analyze(event)
                        if symbols:
                            morse_symbols += len(symbols)
                            if morse_symbols <= 10:  # Show first few symbols
                                for symbol in symbols:
                                    print(f"    Morse symbol: {symbol.element.value}")

                            # Stage 5: Decode
                            chars = decoder.decode(symbols)
                            if chars:
                                decoded_chars += len(chars)
                                for char in chars:
                                    print(f"      Decoded: '{char.char}' ({char.morse_pattern})")

    audio_source.close()

    print("\n" + "=" * 60)
    print("Pipeline Statistics:")
    print(f"  Total chunks processed: {chunk_num}")
    print(f"  Frequency detections: {freq_detections}")
    print(f"  Tone events: {tone_events}")
    print(f"  Morse symbols: {morse_symbols}")
    print(f"  Decoded characters: {decoded_chars}")


if __name__ == "__main__":
    asyncio.run(debug_pipeline())
