#!/usr/bin/env python3
"""Analyze the generated WAV file to see what frequencies are present."""

import wave

import numpy as np
from scipy import fft


def analyze_wav(filename):
    """Analyze frequencies in a WAV file."""
    with wave.open(filename, 'rb') as wav_file:
        sample_rate = wav_file.getframerate()
        n_channels = wav_file.getnchannels()
        sample_width = wav_file.getsampwidth()
        n_frames = wav_file.getnframes()

        print(f"WAV File Analysis: {filename}")
        print("=" * 60)
        print(f"Sample rate: {sample_rate} Hz")
        print(f"Channels: {n_channels}")
        print(f"Sample width: {sample_width} bytes")
        print(f"Total frames: {n_frames}")
        print(f"Duration: {n_frames / sample_rate:.2f} seconds")
        print()

        # Read all audio data
        frames = wav_file.readframes(n_frames)

        # Convert to numpy array
        if sample_width == 2:
            audio = np.frombuffer(frames, dtype=np.int16).astype(np.float64)
            audio = audio / 32768.0
        else:
            raise ValueError(f"Unsupported sample width: {sample_width}")

        # Take a slice where we expect signal (skip first bit, take middle)
        start_sample = sample_rate // 2  # Skip first 0.5 seconds
        end_sample = start_sample + sample_rate  # Take 1 second
        signal_slice = audio[start_sample:end_sample]

        print(f"Analyzing signal from {start_sample/sample_rate:.2f}s to {end_sample/sample_rate:.2f}s")
        print(f"Signal max: {signal_slice.max():.3f}")
        print(f"Signal min: {signal_slice.min():.3f}")
        print(f"Signal mean: {signal_slice.mean():.3f}")
        print(f"Signal RMS: {np.sqrt(np.mean(signal_slice**2)):.3f}")
        print()

        # Perform FFT
        N = len(signal_slice)
        fft_result = fft.fft(signal_slice)
        freqs = fft.fftfreq(N, 1/sample_rate)

        # Get magnitude spectrum (only positive frequencies)
        magnitude = np.abs(fft_result[:N//2])
        positive_freqs = freqs[:N//2]

        # Find peaks in frequency spectrum
        print("Top 10 frequency components:")
        peak_indices = np.argsort(magnitude)[-10:][::-1]
        for i, idx in enumerate(peak_indices, 1):
            print(f"  {i}. Frequency: {positive_freqs[idx]:7.1f} Hz, Magnitude: {magnitude[idx]:.1f}")


if __name__ == "__main__":
    analyze_wav("test_message.wav")
