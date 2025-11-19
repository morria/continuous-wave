#!/usr/bin/env python3
"""Regenerate all test WAV files with proper leader and trailer."""

import sys
import wave
from pathlib import Path

import numpy as np

sys.path.insert(0, '/home/user/continuous-wave')

from scripts.generate_morse_wav import TEXT_TO_MORSE, generate_silence, generate_tone

def generate_test_wav(text: str, output_path: Path, wpm: float = 20.0, frequency: float = 600.0):
    """Generate a test WAV file with leader and trailer.

    Args:
        text: Text to encode
        output_path: Output file path
        wpm: Words per minute
        frequency: Tone frequency in Hz
    """
    sample_rate = 8000
    dot_duration = 1.2 / wpm
    dash_duration = 3 * dot_duration
    element_gap = dot_duration
    char_gap = 3 * dot_duration
    word_gap = 7 * dot_duration

    # Generate leader tone (100ms - short enough to lock but minimize interference)
    leader_duration = 0.10
    leader_samples = int(leader_duration * sample_rate)
    t = np.arange(leader_samples) / sample_rate
    leader_tone = np.sin(2 * np.pi * frequency * t).astype(np.float32) * 0.8

    # Gap after leader (200ms - long enough to ensure tone detector resets)
    gap_duration = 0.2
    gap = generate_silence(gap_duration, sample_rate)

    # Generate morse code
    audio_samples = []
    words = text.upper().split()

    for word_idx, word in enumerate(words):
        for char_idx, char in enumerate(word):
            if char in TEXT_TO_MORSE:
                morse_pattern = TEXT_TO_MORSE[char]
                for symbol_idx, symbol in enumerate(morse_pattern):
                    if symbol == '.':
                        audio_samples.extend(generate_tone(frequency, dot_duration, sample_rate))
                    elif symbol == '-':
                        audio_samples.extend(generate_tone(frequency, dash_duration, sample_rate))

                    # Add element gap if not last symbol in character
                    if symbol_idx < len(morse_pattern) - 1:
                        audio_samples.extend(generate_silence(element_gap, sample_rate))

                # Add character gap if not last character in word
                if char_idx < len(word) - 1:
                    audio_samples.extend(generate_silence(char_gap, sample_rate))

        # Add word gap if not last word
        if word_idx < len(words) - 1:
            audio_samples.extend(generate_silence(word_gap, sample_rate))

    # Add trailing silence and flush tone
    trailing_silence_duration = 0.5
    audio_samples.extend(generate_silence(trailing_silence_duration, sample_rate))
    audio_samples.extend(generate_tone(frequency, 0.01, sample_rate))

    # Combine all
    audio_data = np.concatenate([leader_tone, gap, np.array(audio_samples, dtype=np.float32)])

    # Normalize
    max_val = np.max(np.abs(audio_data))
    if max_val > 0:
        audio_data = audio_data / max_val * 0.8

    # Convert to int16
    audio_int16 = (audio_data * 32767).astype(np.int16)

    # Write
    with wave.open(str(output_path), 'w') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(audio_int16.tobytes())

    print(f'Generated {output_path.name}: duration={len(audio_data)/sample_rate:.2f}s, wpm={wpm}, freq={frequency}Hz')


# Regenerate all test files
output_dir = Path('tests/integration/fixtures/wav_files')
output_dir.mkdir(parents=True, exist_ok=True)

test_files = [
    ("SOS", "SOS.wav", 20.0, 600.0),
    ("TEST", "TEST.wav", 20.0, 600.0),
    ("HELLO WORLD", "HELLO_WORLD.wav", 20.0, 600.0),
    ("PARIS", "PARIS.wav", 20.0, 600.0),
    ("CQ DE W2ASM", "CQ_DE_W2ASM.wav", 20.0, 600.0),
    ("W2ASM", "W2ASM.wav", 20.0, 700.0),  # Special case with 700Hz
]

for text, filename, wpm, freq in test_files:
    output_path = output_dir / filename
    generate_test_wav(text, output_path, wpm, freq)

print("\nAll test WAV files regenerated successfully!")
