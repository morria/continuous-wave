#!/usr/bin/env python3
"""Generate a WAV file with morse code message."""

import wave
from pathlib import Path

import numpy as np

# Morse code lookup (character to morse pattern)
TEXT_TO_MORSE = {
    # Letters
    "A": ".-",
    "B": "-...",
    "C": "-.-.",
    "D": "-..",
    "E": ".",
    "F": "..-.",
    "G": "--.",
    "H": "....",
    "I": "..",
    "J": ".---",
    "K": "-.-",
    "L": ".-..",
    "M": "--",
    "N": "-.",
    "O": "---",
    "P": ".--.",
    "Q": "--.-",
    "R": ".-.",
    "S": "...",
    "T": "-",
    "U": "..-",
    "V": "...-",
    "W": ".--",
    "X": "-..-",
    "Y": "-.--",
    "Z": "--..",
    # Numbers
    "0": "-----",
    "1": ".----",
    "2": "..---",
    "3": "...--",
    "4": "....-",
    "5": ".....",
    "6": "-....",
    "7": "--...",
    "8": "---..",
    "9": "----.",
    # Punctuation
    ".": ".-.-.-",
    ",": "--..--",
    "?": "..--..",
    "'": ".----.",
    "!": "-.-.--",
    "/": "-..-.",
    "(": "-.--.",
    ")": "-.--.-",
    "&": ".-...",
    ":": "---...",
    ";": "-.-.-.",
    "=": "-...-",
    "-": "-....-",
    "_": "..--.-",
    '"': ".-..-.",
    "$": "...-..-",
    "@": ".--.-.",
}


def text_to_morse(text: str) -> str:
    """Convert text to morse code patterns.

    Args:
        text: Text to convert

    Returns:
        Morse code pattern string with spaces
    """
    morse_parts = []
    for char in text.upper():
        if char == " ":
            # Word gap - use 7 units of time (but we'll handle this specially)
            morse_parts.append("/")  # Use / as word separator
        elif char in TEXT_TO_MORSE:
            morse_parts.append(TEXT_TO_MORSE[char])
        else:
            # Skip unknown characters
            pass

    return " ".join(morse_parts)


def generate_morse_audio(
    text: str,
    output_file: str | Path,
    wpm: float = 20.0,
    frequency: float = 600.0,
    sample_rate: int = 8000,
    leader_silence_ms: float = 500.0,
) -> None:
    """Generate morse code audio and save as WAV file.

    Args:
        text: Text message to encode
        wpm: Words per minute (standard is 20)
        frequency: Tone frequency in Hz (standard is 600)
        sample_rate: Audio sample rate
        output_file: Output WAV file path
        leader_silence_ms: Silence at beginning in milliseconds (default 500ms)
    """
    # Calculate timing based on WPM
    # Standard: PARIS = 50 dot durations
    # dot_duration = 1.2 / WPM seconds
    dot_duration = 1.2 / wpm
    dash_duration = 3 * dot_duration
    element_gap = dot_duration  # Gap between dots/dashes in a character
    char_gap = 3 * dot_duration  # Gap between characters
    word_gap = 7 * dot_duration  # Gap between words

    # Convert text to morse
    morse = text_to_morse(text)
    print(f"Text: {text}")
    print(f"Morse: {morse}")
    print(f"WPM: {wpm}, Dot duration: {dot_duration*1000:.1f}ms")

    # Generate audio samples
    audio_samples = []

    # Add leader silence for detector to initialize
    if leader_silence_ms > 0:
        leader_duration = leader_silence_ms / 1000.0
        audio_samples.extend(generate_silence(leader_duration, sample_rate))

    for i, char in enumerate(morse):
        if char == ".":
            # Dot: short tone
            samples = generate_tone(frequency, dot_duration, sample_rate)
            audio_samples.extend(samples)
            # Add element gap (unless end of character)
            if i + 1 < len(morse) and morse[i + 1] not in [" ", "/"]:
                audio_samples.extend(generate_silence(element_gap, sample_rate))

        elif char == "-":
            # Dash: long tone
            samples = generate_tone(frequency, dash_duration, sample_rate)
            audio_samples.extend(samples)
            # Add element gap (unless end of character)
            if i + 1 < len(morse) and morse[i + 1] not in [" ", "/"]:
                audio_samples.extend(generate_silence(element_gap, sample_rate))

        elif char == " ":
            # Character gap
            audio_samples.extend(generate_silence(char_gap, sample_rate))

        elif char == "/":
            # Word gap
            audio_samples.extend(generate_silence(word_gap, sample_rate))

    # Convert to numpy array and normalize
    audio_data = np.array(audio_samples, dtype=np.float32)

    # Normalize to prevent clipping
    max_val = np.max(np.abs(audio_data))
    if max_val > 0:
        audio_data = audio_data / max_val * 0.8

    # Convert to 16-bit PCM
    audio_int16 = (audio_data * 32767).astype(np.int16)

    # Write WAV file
    with wave.open(str(output_file), "w") as wav_file:
        wav_file.setnchannels(1)  # Mono
        wav_file.setsampwidth(2)  # 2 bytes = 16 bit
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(audio_int16.tobytes())

    print(f"Generated {output_file}")
    print(f"Duration: {len(audio_data) / sample_rate:.2f} seconds")


def generate_tone(frequency: float, duration: float, sample_rate: int) -> np.ndarray:
    """Generate a sine wave tone.

    Args:
        frequency: Frequency in Hz
        duration: Duration in seconds
        sample_rate: Sample rate in Hz

    Returns:
        Audio samples as numpy array
    """
    num_samples = int(duration * sample_rate)
    t = np.arange(num_samples) / sample_rate

    # Generate sine wave with slight envelope to avoid clicks
    tone = np.sin(2 * np.pi * frequency * t)

    # Apply short attack/release envelope (5ms)
    envelope_samples = int(0.005 * sample_rate)
    if num_samples > 2 * envelope_samples:
        # Attack
        tone[:envelope_samples] *= np.linspace(0, 1, envelope_samples)
        # Release
        tone[-envelope_samples:] *= np.linspace(1, 0, envelope_samples)

    return tone.astype(np.float32)


def generate_silence(duration: float, sample_rate: int) -> np.ndarray:
    """Generate silence.

    Args:
        duration: Duration in seconds
        sample_rate: Sample rate in Hz

    Returns:
        Silence samples as numpy array
    """
    num_samples = int(duration * sample_rate)
    return np.zeros(num_samples, dtype=np.float32)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Generate morse code WAV file")
    parser.add_argument("text", help="Text message to encode")
    parser.add_argument("-o", "--output", default="morse_output.wav", help="Output WAV file")
    parser.add_argument("-w", "--wpm", type=float, default=20.0, help="Words per minute")
    parser.add_argument("-f", "--frequency", type=float, default=600.0, help="Tone frequency (Hz)")
    parser.add_argument("-s", "--sample-rate", type=int, default=8000, help="Sample rate (Hz)")

    args = parser.parse_args()

    generate_morse_audio(
        text=args.text,
        output_file=args.output,
        wpm=args.wpm,
        frequency=args.frequency,
        sample_rate=args.sample_rate,
    )
