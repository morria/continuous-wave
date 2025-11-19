# WAV Test Fixtures

This directory contains WAV files used for integration testing of the morse code decoder.

## File Naming Convention

WAV files should be named using the expected decoded message with underscores for spaces.

### Examples:
- `CQ_CQ_CQ_DE_W2ASM_W2ASM_K.wav` → Expected: "CQ CQ CQ DE W2ASM W2ASM K"
- `HELLO_WORLD.wav` → Expected: "HELLO WORLD"
- `TEST.wav` → Expected: "TEST"
- `SOS.wav` → Expected: "SOS"

## Current Test Files

### Basic Clean Files
- `SOS.wav` - Classic distress signal
- `CQ_DE_W2ASM.wav` - Ham radio calling sequence
- `PARIS.wav` - Standard word for WPM calibration
- `HELLO_WORLD.wav` - Simple greeting
- `TEST.wav` - Simple test message

## Generating Test Files

### Basic Clean Files

Use the `generate_test_wav.py` script to generate clean morse code WAV files:

```bash
cd tests/integration/fixtures/wav_files
python generate_test_wav.py "YOUR MESSAGE HERE"
python generate_test_wav.py "CQ CQ CQ DE W2ASM W2ASM K"
```

### Challenging Test Files

Use the `generate_challenging_wav.py` script to generate WAV files with various real-world impairments:

```bash
cd tests/integration/fixtures/wav_files

# Add white noise (SNR in dB)
python generate_challenging_wav.py "SOS" --noise --snr 15

# Add amplitude fading
python generate_challenging_wav.py "CQ CQ" --fading --fade-depth 0.3

# Add off-frequency interference
python generate_challenging_wav.py "TEST" --interference --interference-freq 650

# Add sloppy keying (timing variations)
python generate_challenging_wav.py "PARIS" --sloppy-keying --timing-error 0.1

# Combine multiple challenges
python generate_challenging_wav.py "QSO" --noise --snr 12 --fading --fade-depth 0.25
```

Available options:
- `--noise --snr N`: Add white noise with SNR of N dB (lower = more noise)
- `--fading --fade-depth D --fade-rate R`: Add amplitude fading (D: 0.0-1.0, R: Hz)
- `--interference --interference-freq F --interference-amplitude A`: Add off-frequency tone
- `--sloppy-keying --timing-error E`: Add timing variations (E: 0.0-1.0)
- `--seed N`: Set random seed for reproducibility

## Test Behavior

The integration tests will:
1. Automatically discover all `.wav` files in this directory
2. Extract the expected message from the filename
3. Decode the audio using both streaming and direct file mechanisms
4. Verify the decoded output matches the expected message

Simply adding a new `.wav` file to this directory will automatically include it in the test suite.

## Known Issues

**Frequency Detector Bug**: The current decoder has a bug where it detects 218.8 Hz instead of the actual 600 Hz tone in all WAV files. The WAV files are correctly generated (verified via FFT analysis showing peak at 599.6 Hz). The actual decoding tests are marked as expected failures (`@pytest.mark.xfail`) until the decoder is fixed. The smoke tests (which verify the pipeline runs without crashing) continue to pass for all files.
