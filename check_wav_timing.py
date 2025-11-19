#!/usr/bin/env python3
"""Check timing of WAV file."""

import wave

import numpy as np

wav_path = "/tmp/test_w2asm.wav"

with wave.open(wav_path, "rb") as wav:
    sample_rate = wav.getframerate()
    num_frames = wav.getnframes()
    frames = wav.readframes(num_frames)

    # Convert to float
    audio = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0

    duration = len(audio) / sample_rate

    print(f"Sample rate: {sample_rate} Hz")
    print(f"Duration: {duration:.3f} seconds")
    print(f"Samples: {len(audio)}")

    # Find first non-zero sample
    abs_audio = np.abs(audio)
    threshold = 0.01
    above_threshold = np.where(abs_audio > threshold)[0]

    if len(above_threshold) > 0:
        first_signal_sample = above_threshold[0]
        first_signal_time = first_signal_sample / sample_rate
        print(f"First signal at sample {first_signal_sample}, time {first_signal_time:.3f}s")

    # Check RMS over time in 100ms windows
    window_size = int(0.1 * sample_rate)
    print("\nRMS levels (100ms windows):")
    for i in range(0, len(audio), window_size):
        window = audio[i:i+window_size]
        rms = np.sqrt(np.mean(window**2))
        time = i / sample_rate
        if rms > 0.01:
            print(f"  {time:.3f}s: RMS={rms:.4f}")
