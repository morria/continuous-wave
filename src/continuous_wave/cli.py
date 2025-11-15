"""Command-line interface for CW decoder."""

import argparse
import asyncio
import curses
import sys
from pathlib import Path
from typing import Optional

from continuous_wave.audio.file import WavFileSource
from continuous_wave.audio.soundcard import SoundcardSource
from continuous_wave.config import CWConfig
from continuous_wave.decoder.morse import MorseDecoder
from continuous_wave.detection.frequency import FrequencyDetectorImpl
from continuous_wave.detection.tone import EnvelopeDetector
from continuous_wave.pipeline import CWDecoderPipeline
from continuous_wave.signal.noise import NoiseReductionPipeline
from continuous_wave.timing.adaptive import AdaptiveWPMDetector


class CursesUI:
    """Curses-based UI for real-time CW decoding display."""

    def __init__(self, stdscr) -> None:
        """Initialize curses UI.

        Args:
            stdscr: Curses standard screen object
        """
        self.stdscr = stdscr
        self.status_win = None
        self.output_win = None
        self.output_buffer: list[str] = []
        self.max_output_lines = 100

        # Initialize curses
        curses.curs_set(0)  # Hide cursor
        self.stdscr.clear()

        # Get screen dimensions
        height, width = self.stdscr.getmaxyx()

        # Create two panels
        # Top panel: status (1/3 of screen)
        status_height = height // 3
        self.status_win = curses.newwin(status_height, width, 0, 0)
        self.status_win.box()

        # Bottom panel: decoded text (2/3 of screen)
        output_height = height - status_height
        self.output_win = curses.newwin(output_height, width, status_height, 0)
        self.output_win.box()
        self.output_win.scrollok(True)

        # Draw initial borders and labels
        self.status_win.addstr(0, 2, " Status ", curses.A_BOLD)
        self.output_win.addstr(0, 2, " Decoded Text ", curses.A_BOLD)

        self.stdscr.refresh()

    def update_status(
        self,
        frequency: Optional[float] = None,
        snr_db: Optional[float] = None,
        wpm: Optional[float] = None,
        dot_duration: Optional[float] = None,
        freq_locked: bool = False,
        timing_locked: bool = False,
        chars_decoded: int = 0,
    ) -> None:
        """Update status panel.

        Args:
            frequency: Detected frequency (Hz)
            snr_db: Signal-to-noise ratio (dB)
            wpm: Words per minute
            dot_duration: Dot duration (seconds)
            freq_locked: Frequency lock status
            timing_locked: Timing lock status
            chars_decoded: Number of characters decoded
        """
        self.status_win.clear()
        self.status_win.box()
        self.status_win.addstr(0, 2, " Status ", curses.A_BOLD)

        row = 2

        # Frequency info
        if frequency is not None:
            lock_str = "[LOCKED]" if freq_locked else "[SEARCHING]"
            self.status_win.addstr(
                row,
                2,
                f"Frequency: {frequency:7.1f} Hz  {lock_str}",
                curses.A_BOLD if freq_locked else curses.A_NORMAL,
            )
            row += 1

        if snr_db is not None:
            self.status_win.addstr(row, 2, f"SNR:       {snr_db:7.1f} dB")
            row += 1

        row += 1  # Blank line

        # Timing info
        if wpm is not None:
            lock_str = "[LOCKED]" if timing_locked else "[LEARNING]"
            self.status_win.addstr(
                row,
                2,
                f"Speed:     {wpm:7.1f} WPM  {lock_str}",
                curses.A_BOLD if timing_locked else curses.A_NORMAL,
            )
            row += 1

        if dot_duration is not None:
            self.status_win.addstr(row, 2, f"Dot Time:  {dot_duration*1000:7.1f} ms")
            row += 1

        row += 1  # Blank line

        # Statistics
        self.status_win.addstr(row, 2, f"Decoded:   {chars_decoded} characters")

        self.status_win.refresh()

    def add_output(self, text: str) -> None:
        """Add decoded text to output panel.

        Args:
            text: Text to add
        """
        # Add to buffer
        self.output_buffer.append(text)

        # Trim buffer if too long
        if len(self.output_buffer) > self.max_output_lines:
            self.output_buffer = self.output_buffer[-self.max_output_lines :]

        # Redraw output window
        self.output_win.clear()
        self.output_win.box()
        self.output_win.addstr(0, 2, " Decoded Text ", curses.A_BOLD)

        # Get window dimensions
        height, width = self.output_win.getmaxyx()

        # Display buffer (most recent at bottom)
        row = height - 2  # Start from bottom, leaving room for border
        for line in reversed(self.output_buffer):
            if row <= 1:  # Don't overwrite top border
                break

            # Wrap long lines
            for i in range(0, len(line), width - 4):
                chunk = line[i : i + width - 4]
                try:
                    self.output_win.addstr(row, 2, chunk)
                except curses.error:
                    pass  # Ignore errors from writing at edge
                row -= 1
                if row <= 1:
                    break

        self.output_win.refresh()


async def run_decoder_simple(pipeline: CWDecoderPipeline) -> None:
    """Run decoder in simple mode (text output only).

    Args:
        pipeline: Configured CW decoder pipeline
    """
    print("CW Decoder started. Press Ctrl+C to stop.")
    print("=" * 60)

    try:
        async for char, state in pipeline.run():
            # Print character immediately
            print(char.char, end="", flush=True)

            # Print newline for spaces occasionally
            if char.char == " ":
                # Every few words, add a newline for readability
                pass

    except KeyboardInterrupt:
        print("\n\nDecoder stopped.")
        print(f"Total characters decoded: {pipeline.get_state().characters_decoded}")


async def run_decoder_curses(pipeline: CWDecoderPipeline, stdscr) -> None:
    """Run decoder in curses mode (with UI).

    Args:
        pipeline: Configured CW decoder pipeline
        stdscr: Curses standard screen
    """
    ui = CursesUI(stdscr)

    # Make getch non-blocking
    stdscr.nodelay(True)

    output_line = ""

    try:
        async for char, state in pipeline.run():
            # Check for quit key (q)
            try:
                key = stdscr.getch()
                if key == ord("q"):
                    break
            except:
                pass

            # Accumulate output
            output_line += char.char

            # Update status panel
            freq = state.frequency_stats.frequency if state.frequency_stats else None
            snr = state.frequency_stats.snr_db if state.frequency_stats else None
            wpm = state.timing_stats.wpm if state.timing_stats else None
            dot_dur = state.timing_stats.dot_duration if state.timing_stats else None

            ui.update_status(
                frequency=freq,
                snr_db=snr,
                wpm=wpm,
                dot_duration=dot_dur,
                freq_locked=state.is_frequency_locked,
                timing_locked=state.is_timing_locked,
                chars_decoded=state.characters_decoded,
            )

            # Update output panel when we have enough text or hit newline
            if len(output_line) >= 60 or char.char == " ":
                ui.add_output(output_line)
                output_line = ""

            # Small delay to prevent excessive CPU usage
            await asyncio.sleep(0.01)

    except KeyboardInterrupt:
        pass

    finally:
        # Add any remaining output
        if output_line:
            ui.add_output(output_line)


def main_soundcard() -> None:
    """Main entry point for soundcard decoder (cw-decode)."""
    parser = argparse.ArgumentParser(
        description="CW (Morse code) decoder - reads from soundcard"
    )
    parser.add_argument(
        "--curses",
        action="store_true",
        help="Use curses UI with real-time status display",
    )
    parser.add_argument(
        "--device",
        type=str,
        default=None,
        help="Audio input device (default: system default)",
    )
    parser.add_argument(
        "--sample-rate",
        type=int,
        default=8000,
        help="Audio sample rate in Hz (default: 8000)",
    )
    parser.add_argument(
        "--min-freq",
        type=int,
        default=200,
        help="Minimum frequency to search (Hz, default: 200)",
    )
    parser.add_argument(
        "--max-freq",
        type=int,
        default=1200,
        help="Maximum frequency to search (Hz, default: 1200)",
    )

    args = parser.parse_args()

    # Create configuration
    config = CWConfig()
    config.audio.sample_rate = args.sample_rate
    config.frequency.min_frequency = args.min_freq
    config.frequency.max_frequency = args.max_freq

    # Create pipeline components
    audio_source = SoundcardSource(config=config, device=args.device)
    noise_pipeline = NoiseReductionPipeline(config=config)
    freq_detector = FrequencyDetectorImpl(config=config)
    tone_detector = EnvelopeDetector(config=config)
    timing_analyzer = AdaptiveWPMDetector(config=config)
    decoder = MorseDecoder(config=config)

    # Create pipeline
    pipeline = CWDecoderPipeline(
        config=config,
        audio_source=audio_source,
        noise_pipeline=noise_pipeline,
        frequency_detector=freq_detector,
        tone_detector=tone_detector,
        timing_analyzer=timing_analyzer,
        decoder=decoder,
    )

    # Run decoder
    try:
        if args.curses:
            # Run with curses UI
            curses.wrapper(lambda stdscr: asyncio.run(run_decoder_curses(pipeline, stdscr)))
        else:
            # Run in simple mode
            asyncio.run(run_decoder_simple(pipeline))
    finally:
        audio_source.stop()


def main_file() -> None:
    """Main entry point for file decoder (cw-decode-file)."""
    parser = argparse.ArgumentParser(
        description="CW (Morse code) decoder - reads from WAV file"
    )
    parser.add_argument("file", type=Path, help="WAV file to decode")
    parser.add_argument(
        "--curses",
        action="store_true",
        help="Use curses UI with real-time status display",
    )
    parser.add_argument(
        "--sample-rate",
        type=int,
        default=8000,
        help="Processing sample rate in Hz (default: 8000)",
    )
    parser.add_argument(
        "--min-freq",
        type=int,
        default=200,
        help="Minimum frequency to search (Hz, default: 200)",
    )
    parser.add_argument(
        "--max-freq",
        type=int,
        default=1200,
        help="Maximum frequency to search (Hz, default: 1200)",
    )

    args = parser.parse_args()

    # Create configuration
    config = CWConfig()
    config.audio.sample_rate = args.sample_rate
    config.frequency.min_frequency = args.min_freq
    config.frequency.max_frequency = args.max_freq

    # Create pipeline components
    audio_source = WavFileSource(config=config, file_path=args.file)
    noise_pipeline = NoiseReductionPipeline(config=config)
    freq_detector = FrequencyDetectorImpl(config=config)
    tone_detector = EnvelopeDetector(config=config)
    timing_analyzer = AdaptiveWPMDetector(config=config)
    decoder = MorseDecoder(config=config)

    # Create pipeline
    pipeline = CWDecoderPipeline(
        config=config,
        audio_source=audio_source,
        noise_pipeline=noise_pipeline,
        frequency_detector=freq_detector,
        tone_detector=tone_detector,
        timing_analyzer=timing_analyzer,
        decoder=decoder,
    )

    # Run decoder
    try:
        if args.curses:
            # Run with curses UI
            curses.wrapper(lambda stdscr: asyncio.run(run_decoder_curses(pipeline, stdscr)))
        else:
            # Run in simple mode
            asyncio.run(run_decoder_simple(pipeline))
    finally:
        audio_source.close()


if __name__ == "__main__":
    # Determine which mode based on script name
    if "file" in sys.argv[0]:
        main_file()
    else:
        main_soundcard()
