#!/usr/bin/env python3
"""Generate W2ASM with proper leader tone."""

import sys
import wave

import numpy as np

sys.path.insert(0, '/home/user/continuous-wave')

from scripts.generate_morse_wav import TEXT_TO_MORSE, generate_silence, generate_tone

# Parameters
sample_rate = 8000
wpm = 20.0
frequency = 700.0
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

# Generate W2ASM morse code
audio_samples = []

# W = .--
audio_samples.extend(generate_tone(frequency, dot_duration, sample_rate))
audio_samples.extend(generate_silence(element_gap, sample_rate))
audio_samples.extend(generate_tone(frequency, dash_duration, sample_rate))
audio_samples.extend(generate_silence(element_gap, sample_rate))
audio_samples.extend(generate_tone(frequency, dash_duration, sample_rate))
audio_samples.extend(generate_silence(char_gap, sample_rate))

# 2 = ..---
audio_samples.extend(generate_tone(frequency, dot_duration, sample_rate))
audio_samples.extend(generate_silence(element_gap, sample_rate))
audio_samples.extend(generate_tone(frequency, dot_duration, sample_rate))
audio_samples.extend(generate_silence(element_gap, sample_rate))
audio_samples.extend(generate_tone(frequency, dash_duration, sample_rate))
audio_samples.extend(generate_silence(element_gap, sample_rate))
audio_samples.extend(generate_tone(frequency, dash_duration, sample_rate))
audio_samples.extend(generate_silence(element_gap, sample_rate))
audio_samples.extend(generate_tone(frequency, dash_duration, sample_rate))
audio_samples.extend(generate_silence(char_gap, sample_rate))

# A = .-
audio_samples.extend(generate_tone(frequency, dot_duration, sample_rate))
audio_samples.extend(generate_silence(element_gap, sample_rate))
audio_samples.extend(generate_tone(frequency, dash_duration, sample_rate))
audio_samples.extend(generate_silence(char_gap, sample_rate))

# S = ...
audio_samples.extend(generate_tone(frequency, dot_duration, sample_rate))
audio_samples.extend(generate_silence(element_gap, sample_rate))
audio_samples.extend(generate_tone(frequency, dot_duration, sample_rate))
audio_samples.extend(generate_silence(element_gap, sample_rate))
audio_samples.extend(generate_tone(frequency, dot_duration, sample_rate))
audio_samples.extend(generate_silence(char_gap, sample_rate))

# M = --
audio_samples.extend(generate_tone(frequency, dash_duration, sample_rate))
audio_samples.extend(generate_silence(element_gap, sample_rate))
audio_samples.extend(generate_tone(frequency, dash_duration, sample_rate))

# Add trailing silence followed by a short tone to trigger gap detection and flush
trailing_silence_duration = 0.5  # 500ms trailing silence (word gap)
audio_samples.extend(generate_silence(trailing_silence_duration, sample_rate))
# Add a very short tone at the end to trigger the gap classification
audio_samples.extend(generate_tone(frequency, 0.01, sample_rate))  # 10ms tone

# Combine all
audio_data = np.concatenate([leader_tone, gap, np.array(audio_samples, dtype=np.float32)])

# Normalize
max_val = np.max(np.abs(audio_data))
if max_val > 0:
    audio_data = audio_data / max_val * 0.8

# Convert to int16
audio_int16 = (audio_data * 32767).astype(np.int16)

# Write
output_path = 'tests/integration/fixtures/wav_files/W2ASM.wav'
with wave.open(output_path, 'w') as wf:
    wf.setnchannels(1)
    wf.setsampwidth(2)
    wf.setframerate(sample_rate)
    wf.writeframes(audio_int16.tobytes())

print(f'Generated {output_path}')
print(f'Duration: {len(audio_data)/sample_rate:.2f}s')
print(f'WPM: {wpm}, frequency: {frequency}Hz')
