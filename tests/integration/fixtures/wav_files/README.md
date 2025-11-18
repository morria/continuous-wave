# WAV Test Fixtures

This directory contains WAV files used for integration testing of the morse code decoder.

## File Naming Convention

WAV files should be named using the expected decoded message with underscores for spaces.

### Examples:
- `CQ_CQ_CQ_DE_W2ASM_W2ASM_K.wav` → Expected: "CQ CQ CQ DE W2ASM W2ASM K"
- `HELLO_WORLD.wav` → Expected: "HELLO WORLD"
- `TEST.wav` → Expected: "TEST"

## Generating Test Files

Use the `generate_test_wav.py` script to generate morse code WAV files:

```bash
# From the repository root
python tests/integration/fixtures/wav_files/generate_test_wav.py "CQ CQ CQ DE W2ASM W2ASM K"
python tests/integration/fixtures/wav_files/generate_test_wav.py "HELLO WORLD"
```

This will create appropriately named WAV files with morse code audio.

## Test Behavior

The integration tests will:
1. Automatically discover all `.wav` files in this directory
2. Extract the expected message from the filename
3. Decode the audio using both streaming and direct file mechanisms
4. Verify the decoded output matches the expected message

Simply adding a new `.wav` file to this directory will automatically include it in the test suite.
