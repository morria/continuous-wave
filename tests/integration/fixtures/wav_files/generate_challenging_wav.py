#!/usr/bin/env python3
"""Generate challenging morse code WAV files for integration testing.

This utility creates WAV files with morse code audio with various challenging
characteristics like noise, fading, interference, and sloppy keying.

Usage:
    python generate_challenging_wav.py "MESSAGE" --noise --snr 10
    python generate_challenging_wav.py "TEST" --fading --fade-depth 0.5
    python generate_challenging_wav.py "HELLO" --interference --interference-freq 650
    python generate_challenging_wav.py "WORLD" --sloppy-keying --timing-error 0.1
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
    "/": "-..-.",
    "?": "..--..",
    ".": ".-.-.-",
    ",": "--..--",
}


def text_to_morse(text: str) -> str:
    """Convert text to morse code pattern.

    Args:
        text: Text to convert (will be converted to uppercase)

    Returns:
        Morse code pattern with dots, dashes, and spaces

    Raises:
        ValueError: If text contains unsupported characters
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

        morse_words.append(" ".join(morse_chars))

    return "   ".join(morse_words)


def generate_morse_audio(
    morse_pattern: str,
    wpm: int = 20,
    frequency: int = 600,
    sample_rate: int = 8000,
    amplitude: float = 0.5,
    timing_error: float = 0.0,
    rng: np.random.Generator | None = None,
) -> np.ndarray:
    """Generate audio samples for a morse code pattern.

    Args:
        morse_pattern: Morse code pattern (dots, dashes, spaces)
        wpm: Words per minute (determines timing)
        frequency: Tone frequency in Hz
        sample_rate: Audio sample rate in Hz
        amplitude: Signal amplitude (0.0 to 1.0)
        timing_error: Random timing variation (0.0 to 1.0, 0=perfect)
        rng: Random number generator for timing variations

    Returns:
        Audio samples as float32 array
    """
    if rng is None:
        rng = np.random.default_rng()

    # Calculate timing from WPM (PARIS standard)
    dot_duration = 1.2 / wpm  # in seconds
    dash_duration = 3 * dot_duration
    element_gap = dot_duration
    char_gap = 3 * dot_duration
    word_gap = 7 * dot_duration

    def add_timing_variation(duration: float) -> float:
        """Add random timing variation to duration."""
        if timing_error > 0:
            # Add random variation: +/- timing_error * duration
            variation = rng.uniform(-timing_error, timing_error) * duration
            return max(0.001, duration + variation)  # Ensure positive duration
        return duration

    def generate_tone(duration: float) -> np.ndarray:
        """Generate a tone with soft attack/release to avoid clicks."""
        duration = add_timing_variation(duration)
        num_samples = int(duration * sample_rate)
        t = np.linspace(0, duration, num_samples, endpoint=False)

        # Generate sine wave
        signal = amplitude * np.sin(2 * np.pi * frequency * t)

        # Apply soft envelope (5ms attack/release to avoid clicks)
        envelope_samples = min(int(0.005 * sample_rate), num_samples // 2)
        if envelope_samples > 0:
            attack = np.linspace(0, 1, envelope_samples)
            release = np.linspace(1, 0, envelope_samples)
            signal[:envelope_samples] *= attack
            signal[-envelope_samples:] *= release

        return signal

    def generate_silence(duration: float) -> np.ndarray:
        """Generate silence of specified duration."""
        duration = add_timing_variation(duration)
        num_samples = int(duration * sample_rate)
        return np.zeros(num_samples)

    # Build audio
    audio_segments: list[np.ndarray] = []

    i = 0
    while i < len(morse_pattern):
        char = morse_pattern[i]

        if char == ".":
            audio_segments.append(generate_tone(dot_duration))
            if i + 1 < len(morse_pattern) and morse_pattern[i + 1] in ".-":
                audio_segments.append(generate_silence(element_gap))

        elif char == "-":
            audio_segments.append(generate_tone(dash_duration))
            if i + 1 < len(morse_pattern) and morse_pattern[i + 1] in ".-":
                audio_segments.append(generate_silence(element_gap))

        elif char == " ":
            space_count = 1
            while i + space_count < len(morse_pattern) and morse_pattern[i + space_count] == " ":
                space_count += 1

            if space_count >= 3:
                audio_segments.append(generate_silence(word_gap - element_gap))
                i += space_count - 1
            else:
                audio_segments.append(generate_silence(char_gap - element_gap))

        i += 1

    # Concatenate all segments
    audio = np.concatenate(audio_segments)

    # Add silence at beginning and end
    silence_padding = generate_silence(0.5)
    audio = np.concatenate([silence_padding, audio, silence_padding])

    return audio.astype(np.float32)


def add_white_noise(audio: np.ndarray, snr_db: float, rng: np.random.Generator) -> np.ndarray:
    """Add white noise to achieve specified SNR.

    Args:
        audio: Clean audio signal
        snr_db: Desired signal-to-noise ratio in dB
        rng: Random number generator

    Returns:
        Audio with added noise
    """
    # Calculate signal power
    signal_power = np.mean(audio**2)

    # Calculate noise power for desired SNR
    # SNR(dB) = 10 * log10(signal_power / noise_power)
    # noise_power = signal_power / 10^(SNR/10)
    noise_power = signal_power / (10 ** (snr_db / 10))

    # Generate white noise
    noise = rng.normal(0, np.sqrt(noise_power), audio.shape)

    return audio + noise.astype(np.float32)


def add_fading(
    audio: np.ndarray,
    sample_rate: int,
    fade_rate: float = 0.5,
    fade_depth: float = 0.3,
    rng: np.random.Generator = None,
) -> np.ndarray:
    """Add amplitude fading to simulate propagation effects.

    Args:
        audio: Clean audio signal
        sample_rate: Audio sample rate in Hz
        fade_rate: Fading rate in Hz (cycles per second)
        fade_depth: Fading depth (0.0 to 1.0, amount of amplitude variation)
        rng: Random number generator

    Returns:
        Audio with fading applied
    """
    if rng is None:
        rng = np.random.default_rng()

    # Generate smooth fading envelope using sine wave with random phase
    t = np.arange(len(audio)) / sample_rate
    phase = rng.uniform(0, 2 * np.pi)

    # Fading envelope: 1.0 - fade_depth * sin(2*pi*fade_rate*t + phase)
    # This creates amplitude variations between (1-fade_depth) and 1.0
    envelope = 1.0 - fade_depth * (0.5 + 0.5 * np.sin(2 * np.pi * fade_rate * t + phase))

    return audio * envelope.astype(np.float32)


def add_interference(
    audio: np.ndarray,
    sample_rate: int,
    interference_freq: int,
    interference_amplitude: float,
) -> np.ndarray:
    """Add off-frequency interference tone.

    Args:
        audio: Clean audio signal
        sample_rate: Audio sample rate in Hz
        interference_freq: Frequency of interference tone in Hz
        interference_amplitude: Amplitude of interference (relative to signal)

    Returns:
        Audio with interference added
    """
    t = np.arange(len(audio)) / sample_rate
    interference = interference_amplitude * np.sin(2 * np.pi * interference_freq * t)

    return audio + interference.astype(np.float32)


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Generate challenging morse code WAV files for testing",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s "HELLO WORLD"
  %(prog)s "TEST" --noise --snr 10
  %(prog)s "SOS" --fading --fade-depth 0.5
  %(prog)s "CQ CQ" --interference --interference-freq 650
  %(prog)s "PARIS" --sloppy-keying --timing-error 0.15
  %(prog)s "QSO" --noise --snr 8 --fading --fade-depth 0.3
        """,
    )
    parser.add_argument("message", help="Message to encode in morse code")
    parser.add_argument("--wpm", type=int, default=20, help="Words per minute (default: 20)")
    parser.add_argument(
        "--frequency", type=int, default=600, help="Tone frequency in Hz (default: 600)"
    )
    parser.add_argument(
        "--sample-rate", type=int, default=8000, help="Sample rate in Hz (default: 8000)"
    )
    parser.add_argument(
        "--amplitude", type=float, default=0.5, help="Signal amplitude 0.0-1.0 (default: 0.5)"
    )

    # Challenging features
    parser.add_argument("--noise", action="store_true", help="Add white noise")
    parser.add_argument("--snr", type=float, default=15.0, help="SNR in dB (default: 15)")

    parser.add_argument("--fading", action="store_true", help="Add amplitude fading")
    parser.add_argument(
        "--fade-rate", type=float, default=0.5, help="Fade rate in Hz (default: 0.5)"
    )
    parser.add_argument(
        "--fade-depth", type=float, default=0.3, help="Fade depth 0.0-1.0 (default: 0.3)"
    )

    parser.add_argument(
        "--interference", action="store_true", help="Add off-frequency interference"
    )
    parser.add_argument(
        "--interference-freq", type=int, default=650, help="Interference freq Hz (default: 650)"
    )
    parser.add_argument(
        "--interference-amplitude",
        type=float,
        default=0.2,
        help="Interference amplitude (default: 0.2)",
    )

    parser.add_argument("--sloppy-keying", action="store_true", help="Add timing variations")
    parser.add_argument(
        "--timing-error",
        type=float,
        default=0.1,
        help="Timing error 0.0-1.0 (default: 0.1)",
    )

    parser.add_argument("--output", type=Path, help="Output file path (auto-generated if not set)")
    parser.add_argument("--seed", type=int, help="Random seed for reproducibility")
    parser.add_argument("--suffix", type=str, default="", help="Suffix to add to filename")

    args = parser.parse_args()

    # Validate parameters
    if not 0.0 <= args.amplitude <= 1.0:
        print("Error: Amplitude must be between 0.0 and 1.0", file=sys.stderr)
        return 1
    if args.fading and not 0.0 <= args.fade_depth <= 1.0:
        print("Error: Fade depth must be between 0.0 and 1.0", file=sys.stderr)
        return 1
    if args.sloppy_keying and not 0.0 <= args.timing_error <= 1.0:
        print("Error: Timing error must be between 0.0 and 1.0", file=sys.stderr)
        return 1

    # Initialize random number generator
    rng = np.random.default_rng(args.seed)

    try:
        # Convert message to morse
        morse_pattern = text_to_morse(args.message)
        print(f"Message: {args.message}")
        print(f"Morse:   {morse_pattern}")

        # Generate base audio
        print(f"\nGenerating audio at {args.wpm} WPM, {args.frequency} Hz...")
        audio = generate_morse_audio(
            morse_pattern,
            wpm=args.wpm,
            frequency=args.frequency,
            sample_rate=args.sample_rate,
            amplitude=args.amplitude,
            timing_error=args.timing_error if args.sloppy_keying else 0.0,
            rng=rng,
        )

        # Apply challenging features
        features = []

        if args.noise:
            print(f"  Adding white noise (SNR: {args.snr} dB)...")
            audio = add_white_noise(audio, args.snr, rng)
            features.append(f"noise_snr{args.snr}")

        if args.fading:
            print(f"  Adding fading (rate: {args.fade_rate} Hz, depth: {args.fade_depth})...")
            audio = add_fading(audio, args.sample_rate, args.fade_rate, args.fade_depth, rng)
            features.append(f"fading_depth{args.fade_depth}")

        if args.interference:
            print(
                f"  Adding interference (freq: {args.interference_freq} Hz, "
                f"amplitude: {args.interference_amplitude})..."
            )
            audio = add_interference(
                audio, args.sample_rate, args.interference_freq, args.interference_amplitude
            )
            features.append(f"interference_{args.interference_freq}hz")

        if args.sloppy_keying:
            print(f"  Applied sloppy keying (timing error: {args.timing_error})...")
            features.append(f"sloppy_{args.timing_error}")

        # Determine output filename
        if args.output:
            output_path = args.output
        else:
            # Auto-generate filename from message and features
            base_name = args.message.strip().replace(" ", "_").upper()
            if features:
                feature_str = "_".join(features)
                filename = f"{base_name}_{feature_str}"
            else:
                filename = base_name

            if args.suffix:
                filename += f"_{args.suffix}"

            filename += ".wav"
            output_path = Path(__file__).parent / filename

        # Normalize to prevent clipping
        max_val = np.max(np.abs(audio))
        if max_val > 1.0:
            print(f"  Normalizing (max: {max_val:.2f})...")
            audio = audio / max_val

        # Convert to 16-bit PCM
        audio_int16 = (audio * 32767).astype(np.int16)

        # Write WAV file
        wavfile.write(output_path, args.sample_rate, audio_int16)

        print(f"\n✓ Created: {output_path}")
        print(f"  Duration: {len(audio) / args.sample_rate:.2f} seconds")
        print(f"  Samples:  {len(audio)}")
        if features:
            print(f"  Features: {', '.join(features)}")

        return 0

    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
