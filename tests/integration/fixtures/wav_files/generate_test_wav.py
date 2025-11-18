#!/usr/bin/env python3
"""Generate morse code WAV files for integration testing.

This utility creates WAV files with morse code audio for testing the decoder.
The filename will automatically be formatted according to the test naming
convention (spaces replaced with underscores).

Usage:
    python generate_test_wav.py "MESSAGE TO ENCODE"
    python generate_test_wav.py "CQ CQ CQ DE W2ASM W2ASM K"
"""

import argparse
import sys
from pathlib import Path

import numpy as np
from scipy.io import wavfile

# International Morse Code mapping
MORSE_CODE = {
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
    "/": "-..-.",  # Slash
    "?": "..--..",  # Question mark
    ".": ".-.-.-",  # Period
    ",": "--..--",  # Comma
}


def text_to_morse(text: str) -> str:
    """Convert text to morse code pattern.

    Args:
        text: Text to convert (will be converted to uppercase)

    Returns:
        Morse code pattern with:
        - '.' for dot
        - '-' for dash
        - ' ' for character gap
        - '   ' (3 spaces) for word gap

    Raises:
        ValueError: If text contains characters not in morse code table
    """
    morse_words = []

    for word in text.strip().upper().split():
        morse_chars = []
        for char in word:
            if char not in MORSE_CODE:
                raise ValueError(
                    f"Character '{char}' is not supported in morse code.\n"
                    f"Supported: letters A-Z, numbers 0-9, and /?.,"
                )
            morse_chars.append(MORSE_CODE[char])

        # Join characters with single space (character gap)
        morse_words.append(" ".join(morse_chars))

    # Join words with three spaces (word gap)
    return "   ".join(morse_words)


def generate_morse_audio(
    morse_pattern: str,
    wpm: int = 20,
    frequency: int = 600,
    sample_rate: int = 8000,
    amplitude: float = 0.5,
) -> np.ndarray:
    """Generate audio samples for a morse code pattern.

    Args:
        morse_pattern: Morse code pattern (dots, dashes, spaces)
        wpm: Words per minute (determines timing)
        frequency: Tone frequency in Hz
        sample_rate: Audio sample rate in Hz
        amplitude: Signal amplitude (0.0 to 1.0)

    Returns:
        Audio samples as float32 array
    """
    # Calculate timing from WPM (PARIS standard)
    # dot_duration = 1200 / WPM milliseconds
    dot_duration = 1.2 / wpm  # in seconds
    dash_duration = 3 * dot_duration
    element_gap = dot_duration  # gap between dots/dashes within character
    char_gap = 3 * dot_duration  # gap between characters
    word_gap = 7 * dot_duration  # gap between words

    def generate_tone(duration: float) -> np.ndarray:
        """Generate a tone of specified duration."""
        num_samples = int(duration * sample_rate)
        t = np.linspace(0, duration, num_samples, endpoint=False)
        return amplitude * np.sin(2 * np.pi * frequency * t)

    def generate_silence(duration: float) -> np.ndarray:
        """Generate silence of specified duration."""
        num_samples = int(duration * sample_rate)
        return np.zeros(num_samples)

    # Build audio
    audio_segments: list[np.ndarray] = []

    i = 0
    while i < len(morse_pattern):
        char = morse_pattern[i]

        if char == ".":
            # Dot
            audio_segments.append(generate_tone(dot_duration))
            # Add element gap if next char is dot/dash
            if i + 1 < len(morse_pattern) and morse_pattern[i + 1] in ".-":
                audio_segments.append(generate_silence(element_gap))

        elif char == "-":
            # Dash
            audio_segments.append(generate_tone(dash_duration))
            # Add element gap if next char is dot/dash
            if i + 1 < len(morse_pattern) and morse_pattern[i + 1] in ".-":
                audio_segments.append(generate_silence(element_gap))

        elif char == " ":
            # Count consecutive spaces to determine gap type
            space_count = 1
            while i + space_count < len(morse_pattern) and morse_pattern[i + space_count] == " ":
                space_count += 1

            if space_count >= 3:
                # Word gap (7 dots, but we already have 1 from element gap)
                audio_segments.append(generate_silence(word_gap - element_gap))
                i += space_count - 1  # Skip the extra spaces
            else:
                # Character gap (3 dots, but we already have 1 from element gap)
                audio_segments.append(generate_silence(char_gap - element_gap))

        i += 1

    # Concatenate all segments
    audio = np.concatenate(audio_segments)

    # Add silence at beginning and end for clean detection
    silence_padding = generate_silence(0.5)  # 500ms padding
    audio = np.concatenate([silence_padding, audio, silence_padding])

    return audio.astype(np.float32)


def main() -> int:
    """Main entry point.

    Returns:
        Exit code (0 for success, 1 for error)
    """
    parser = argparse.ArgumentParser(
        description="Generate morse code WAV files for testing",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s "HELLO WORLD"
  %(prog)s "CQ CQ CQ DE W2ASM W2ASM K"
  %(prog)s "TEST" --wpm 25 --frequency 700
        """,
    )
    parser.add_argument("message", help="Message to encode in morse code")
    parser.add_argument("--wpm", type=int, default=20, help="Words per minute (default: 20)")
    parser.add_argument(
        "--frequency", type=int, default=600, help="Tone frequency in Hz (default: 600)"
    )
    parser.add_argument(
        "--sample-rate",
        type=int,
        default=8000,
        help="Audio sample rate in Hz (default: 8000)",
    )
    parser.add_argument(
        "--amplitude",
        type=float,
        default=0.5,
        help="Signal amplitude 0.0-1.0 (default: 0.5)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Output file path (default: auto-generated from message)",
    )

    args = parser.parse_args()

    # Validate amplitude
    if not 0.0 <= args.amplitude <= 1.0:
        print("Error: Amplitude must be between 0.0 and 1.0", file=sys.stderr)
        return 1

    try:
        # Convert message to morse
        morse_pattern = text_to_morse(args.message)
        print(f"Message: {args.message}")
        print(f"Morse:   {morse_pattern}")

        # Generate audio
        print(f"\nGenerating audio at {args.wpm} WPM, {args.frequency} Hz...")
        audio = generate_morse_audio(
            morse_pattern,
            wpm=args.wpm,
            frequency=args.frequency,
            sample_rate=args.sample_rate,
            amplitude=args.amplitude,
        )

        # Determine output filename
        if args.output:
            output_path = args.output
        else:
            # Auto-generate filename from message
            filename = args.message.strip().replace(" ", "_").upper() + ".wav"
            output_path = Path(__file__).parent / filename

        # Convert to 16-bit PCM
        audio_int16 = (audio * 32767).astype(np.int16)

        # Write WAV file
        wavfile.write(output_path, args.sample_rate, audio_int16)

        print(f"✓ Created: {output_path}")
        print(f"  Duration: {len(audio) / args.sample_rate:.2f} seconds")
        print(f"  Samples:  {len(audio)}")

        return 0

    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
