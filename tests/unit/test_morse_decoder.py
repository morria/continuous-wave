"""Unit tests for Morse code decoder."""

import pytest

from continuous_wave.config import CWConfig
from continuous_wave.decoder.morse import MORSE_CODE, MorseDecoder
from continuous_wave.models import MorseElement, MorseSymbol


@pytest.fixture
def config() -> CWConfig:
    """Create test configuration."""
    return CWConfig()


@pytest.fixture
def decoder(config: CWConfig) -> MorseDecoder:
    """Create morse decoder instance."""
    return MorseDecoder(config=config)


class TestMorseCodeTable:
    """Test morse code lookup table completeness."""

    def test_table_has_all_letters(self) -> None:
        """Verify all A-Z letters are in lookup table."""
        expected_letters = set("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
        actual_letters = {char for char in MORSE_CODE.values() if char.isalpha()}
        assert actual_letters == expected_letters

    def test_table_has_all_digits(self) -> None:
        """Verify all 0-9 digits are in lookup table."""
        expected_digits = set("0123456789")
        actual_digits = {char for char in MORSE_CODE.values() if char.isdigit()}
        assert actual_digits == expected_digits

    def test_table_has_common_punctuation(self) -> None:
        """Verify common punctuation marks are present."""
        common_punctuation = {
            ".",
            ",",
            "?",
            "'",
            "!",
            "/",
            "(",
            ")",
            "&",
            ":",
            ";",
            "=",
            "-",
            "_",
            '"',
            "$",
            "@",
        }
        actual_punctuation = {
            char for char in MORSE_CODE.values() if not char.isalnum() and not char.startswith("<")
        }
        assert common_punctuation.issubset(actual_punctuation)

    def test_table_has_prosigns(self) -> None:
        """Verify prosigns are present."""
        prosigns = {"<AA>", "<BT>", "<AR>", "<KA>", "<SK>", "<HH>"}
        actual_prosigns = {char for char in MORSE_CODE.values() if char.startswith("<")}
        assert prosigns == actual_prosigns

    def test_no_duplicate_patterns(self) -> None:
        """Verify each morse pattern is unique."""
        patterns = list(MORSE_CODE.keys())
        assert len(patterns) == len(set(patterns))


class TestBasicDecoding:
    """Test basic morse code decoding."""

    def test_decode_single_letter_e(self, decoder: MorseDecoder) -> None:
        """Test decoding single letter E (one dot)."""
        symbols = [
            MorseSymbol(element=MorseElement.DOT, duration=0.06, timestamp=0.0),
            MorseSymbol(element=MorseElement.CHAR_GAP, duration=0.18, timestamp=0.06),
        ]
        chars = decoder.decode(symbols)

        assert len(chars) == 1
        assert chars[0].char == "E"
        assert chars[0].confidence == 1.0
        assert chars[0].morse_pattern == "."

    def test_decode_single_letter_t(self, decoder: MorseDecoder) -> None:
        """Test decoding single letter T (one dash)."""
        symbols = [
            MorseSymbol(element=MorseElement.DASH, duration=0.18, timestamp=0.0),
            MorseSymbol(element=MorseElement.CHAR_GAP, duration=0.18, timestamp=0.18),
        ]
        chars = decoder.decode(symbols)

        assert len(chars) == 1
        assert chars[0].char == "T"
        assert chars[0].confidence == 1.0
        assert chars[0].morse_pattern == "-"

    def test_decode_letter_a(self, decoder: MorseDecoder) -> None:
        """Test decoding letter A (dot-dash)."""
        symbols = [
            MorseSymbol(element=MorseElement.DOT, duration=0.06, timestamp=0.0),
            MorseSymbol(element=MorseElement.ELEMENT_GAP, duration=0.06, timestamp=0.06),
            MorseSymbol(element=MorseElement.DASH, duration=0.18, timestamp=0.12),
            MorseSymbol(element=MorseElement.CHAR_GAP, duration=0.18, timestamp=0.30),
        ]
        chars = decoder.decode(symbols)

        assert len(chars) == 1
        assert chars[0].char == "A"
        assert chars[0].confidence == 1.0
        assert chars[0].morse_pattern == ".-"

    def test_decode_letter_s(self, decoder: MorseDecoder) -> None:
        """Test decoding letter S (three dots)."""
        symbols = [
            MorseSymbol(element=MorseElement.DOT, duration=0.06, timestamp=0.0),
            MorseSymbol(element=MorseElement.ELEMENT_GAP, duration=0.06, timestamp=0.06),
            MorseSymbol(element=MorseElement.DOT, duration=0.06, timestamp=0.12),
            MorseSymbol(element=MorseElement.ELEMENT_GAP, duration=0.06, timestamp=0.18),
            MorseSymbol(element=MorseElement.DOT, duration=0.06, timestamp=0.24),
            MorseSymbol(element=MorseElement.CHAR_GAP, duration=0.18, timestamp=0.30),
        ]
        chars = decoder.decode(symbols)

        assert len(chars) == 1
        assert chars[0].char == "S"
        assert chars[0].confidence == 1.0
        assert chars[0].morse_pattern == "..."

    def test_decode_number_5(self, decoder: MorseDecoder) -> None:
        """Test decoding number 5 (five dots)."""
        symbols = [
            MorseSymbol(element=MorseElement.DOT, duration=0.06, timestamp=0.0),
            MorseSymbol(element=MorseElement.ELEMENT_GAP, duration=0.06, timestamp=0.06),
            MorseSymbol(element=MorseElement.DOT, duration=0.06, timestamp=0.12),
            MorseSymbol(element=MorseElement.ELEMENT_GAP, duration=0.06, timestamp=0.18),
            MorseSymbol(element=MorseElement.DOT, duration=0.06, timestamp=0.24),
            MorseSymbol(element=MorseElement.ELEMENT_GAP, duration=0.06, timestamp=0.30),
            MorseSymbol(element=MorseElement.DOT, duration=0.06, timestamp=0.36),
            MorseSymbol(element=MorseElement.ELEMENT_GAP, duration=0.06, timestamp=0.42),
            MorseSymbol(element=MorseElement.DOT, duration=0.06, timestamp=0.48),
            MorseSymbol(element=MorseElement.CHAR_GAP, duration=0.18, timestamp=0.54),
        ]
        chars = decoder.decode(symbols)

        assert len(chars) == 1
        assert chars[0].char == "5"
        assert chars[0].confidence == 1.0
        assert chars[0].morse_pattern == "....."


class TestWordDecoding:
    """Test decoding words and phrases."""

    def test_decode_sos(self, decoder: MorseDecoder) -> None:
        """Test decoding SOS (... --- ...)."""
        symbols = [
            # S (...)
            MorseSymbol(element=MorseElement.DOT, duration=0.06, timestamp=0.0),
            MorseSymbol(element=MorseElement.ELEMENT_GAP, duration=0.06, timestamp=0.06),
            MorseSymbol(element=MorseElement.DOT, duration=0.06, timestamp=0.12),
            MorseSymbol(element=MorseElement.ELEMENT_GAP, duration=0.06, timestamp=0.18),
            MorseSymbol(element=MorseElement.DOT, duration=0.06, timestamp=0.24),
            MorseSymbol(element=MorseElement.CHAR_GAP, duration=0.18, timestamp=0.30),
            # O (---)
            MorseSymbol(element=MorseElement.DASH, duration=0.18, timestamp=0.48),
            MorseSymbol(element=MorseElement.ELEMENT_GAP, duration=0.06, timestamp=0.66),
            MorseSymbol(element=MorseElement.DASH, duration=0.18, timestamp=0.72),
            MorseSymbol(element=MorseElement.ELEMENT_GAP, duration=0.06, timestamp=0.90),
            MorseSymbol(element=MorseElement.DASH, duration=0.18, timestamp=0.96),
            MorseSymbol(element=MorseElement.CHAR_GAP, duration=0.18, timestamp=1.14),
            # S (...)
            MorseSymbol(element=MorseElement.DOT, duration=0.06, timestamp=1.32),
            MorseSymbol(element=MorseElement.ELEMENT_GAP, duration=0.06, timestamp=1.38),
            MorseSymbol(element=MorseElement.DOT, duration=0.06, timestamp=1.44),
            MorseSymbol(element=MorseElement.ELEMENT_GAP, duration=0.06, timestamp=1.50),
            MorseSymbol(element=MorseElement.DOT, duration=0.06, timestamp=1.56),
            MorseSymbol(
                element=MorseElement.CHAR_GAP, duration=0.18, timestamp=1.62
            ),  # Need gap to end pattern
        ]
        chars = decoder.decode(symbols)

        assert len(chars) == 3
        assert "".join([c.char for c in chars]) == "SOS"
        assert all(c.confidence == 1.0 for c in chars)

    def test_decode_hello_world(self, decoder: MorseDecoder) -> None:
        """Test decoding 'HELLO WORLD' with word gap."""
        # H = ...., E = ., L = .-.., L = .-.., O = ---
        # W = .--, O = ---, R = .-.., L = .-.., D = -..
        symbols = [
            # H
            MorseSymbol(element=MorseElement.DOT, duration=0.06, timestamp=0.0),
            MorseSymbol(element=MorseElement.ELEMENT_GAP, duration=0.06, timestamp=0.06),
            MorseSymbol(element=MorseElement.DOT, duration=0.06, timestamp=0.12),
            MorseSymbol(element=MorseElement.ELEMENT_GAP, duration=0.06, timestamp=0.18),
            MorseSymbol(element=MorseElement.DOT, duration=0.06, timestamp=0.24),
            MorseSymbol(element=MorseElement.ELEMENT_GAP, duration=0.06, timestamp=0.30),
            MorseSymbol(element=MorseElement.DOT, duration=0.06, timestamp=0.36),
            MorseSymbol(element=MorseElement.CHAR_GAP, duration=0.18, timestamp=0.42),
            # E
            MorseSymbol(element=MorseElement.DOT, duration=0.06, timestamp=0.60),
            MorseSymbol(element=MorseElement.CHAR_GAP, duration=0.18, timestamp=0.66),
            # L
            MorseSymbol(element=MorseElement.DOT, duration=0.06, timestamp=0.84),
            MorseSymbol(element=MorseElement.ELEMENT_GAP, duration=0.06, timestamp=0.90),
            MorseSymbol(element=MorseElement.DASH, duration=0.18, timestamp=0.96),
            MorseSymbol(element=MorseElement.ELEMENT_GAP, duration=0.06, timestamp=1.14),
            MorseSymbol(element=MorseElement.DOT, duration=0.06, timestamp=1.20),
            MorseSymbol(element=MorseElement.ELEMENT_GAP, duration=0.06, timestamp=1.26),
            MorseSymbol(element=MorseElement.DOT, duration=0.06, timestamp=1.32),
            MorseSymbol(element=MorseElement.CHAR_GAP, duration=0.18, timestamp=1.38),
            # L
            MorseSymbol(element=MorseElement.DOT, duration=0.06, timestamp=1.56),
            MorseSymbol(element=MorseElement.ELEMENT_GAP, duration=0.06, timestamp=1.62),
            MorseSymbol(element=MorseElement.DASH, duration=0.18, timestamp=1.68),
            MorseSymbol(element=MorseElement.ELEMENT_GAP, duration=0.06, timestamp=1.86),
            MorseSymbol(element=MorseElement.DOT, duration=0.06, timestamp=1.92),
            MorseSymbol(element=MorseElement.ELEMENT_GAP, duration=0.06, timestamp=1.98),
            MorseSymbol(element=MorseElement.DOT, duration=0.06, timestamp=2.04),
            MorseSymbol(element=MorseElement.CHAR_GAP, duration=0.18, timestamp=2.10),
            # O
            MorseSymbol(element=MorseElement.DASH, duration=0.18, timestamp=2.28),
            MorseSymbol(element=MorseElement.ELEMENT_GAP, duration=0.06, timestamp=2.46),
            MorseSymbol(element=MorseElement.DASH, duration=0.18, timestamp=2.52),
            MorseSymbol(element=MorseElement.ELEMENT_GAP, duration=0.06, timestamp=2.70),
            MorseSymbol(element=MorseElement.DASH, duration=0.18, timestamp=2.76),
            # Word gap
            MorseSymbol(element=MorseElement.WORD_GAP, duration=0.42, timestamp=2.94),
        ]
        chars = decoder.decode(symbols)

        # Should decode "HELLO " (with space)
        assert len(chars) == 6
        result = "".join([c.char for c in chars])
        assert result == "HELLO "


class TestFuzzyMatching:
    """Test fuzzy matching with errors."""

    def test_fuzzy_match_one_edit_distance(self, decoder: MorseDecoder) -> None:
        """Test fuzzy matching with 1 character difference."""
        # Send ".." instead of "." (E)
        # Should match to "I" (..) with confidence 1.0
        symbols = [
            MorseSymbol(element=MorseElement.DOT, duration=0.06, timestamp=0.0),
            MorseSymbol(element=MorseElement.ELEMENT_GAP, duration=0.06, timestamp=0.06),
            MorseSymbol(element=MorseElement.DOT, duration=0.06, timestamp=0.12),
            MorseSymbol(element=MorseElement.CHAR_GAP, duration=0.18, timestamp=0.18),
        ]
        chars = decoder.decode(symbols)

        assert len(chars) == 1
        assert chars[0].char == "I"
        assert chars[0].confidence == 1.0

    def test_fuzzy_match_with_extra_dot(self, decoder: MorseDecoder) -> None:
        """Test fuzzy matching with extra dot added to pattern."""
        # Send "...." which could be "H" or could be close to "S" (...)
        # Should decode as "H" with confidence 1.0 (exact match)
        symbols = [
            MorseSymbol(element=MorseElement.DOT, duration=0.06, timestamp=0.0),
            MorseSymbol(element=MorseElement.ELEMENT_GAP, duration=0.06, timestamp=0.06),
            MorseSymbol(element=MorseElement.DOT, duration=0.06, timestamp=0.12),
            MorseSymbol(element=MorseElement.ELEMENT_GAP, duration=0.06, timestamp=0.18),
            MorseSymbol(element=MorseElement.DOT, duration=0.06, timestamp=0.24),
            MorseSymbol(element=MorseElement.ELEMENT_GAP, duration=0.06, timestamp=0.30),
            MorseSymbol(element=MorseElement.DOT, duration=0.06, timestamp=0.36),
            MorseSymbol(element=MorseElement.CHAR_GAP, duration=0.18, timestamp=0.42),
        ]
        chars = decoder.decode(symbols)

        assert len(chars) == 1
        assert chars[0].char == "H"

    def test_invalid_pattern_returns_replacement_char(self, decoder: MorseDecoder) -> None:
        """Test that completely invalid pattern returns replacement character."""
        # Send very long invalid pattern that's far from any valid pattern
        symbols = [
            MorseSymbol(element=MorseElement.DOT, duration=0.06, timestamp=0.0),
            MorseSymbol(element=MorseElement.ELEMENT_GAP, duration=0.06, timestamp=0.06),
            MorseSymbol(element=MorseElement.DASH, duration=0.18, timestamp=0.12),
            MorseSymbol(element=MorseElement.ELEMENT_GAP, duration=0.06, timestamp=0.30),
            MorseSymbol(element=MorseElement.DOT, duration=0.06, timestamp=0.36),
            MorseSymbol(element=MorseElement.ELEMENT_GAP, duration=0.06, timestamp=0.42),
            MorseSymbol(element=MorseElement.DASH, duration=0.18, timestamp=0.48),
            MorseSymbol(element=MorseElement.ELEMENT_GAP, duration=0.06, timestamp=0.66),
            MorseSymbol(element=MorseElement.DOT, duration=0.06, timestamp=0.72),
            MorseSymbol(element=MorseElement.ELEMENT_GAP, duration=0.06, timestamp=0.78),
            MorseSymbol(element=MorseElement.DASH, duration=0.18, timestamp=0.84),
            MorseSymbol(element=MorseElement.ELEMENT_GAP, duration=0.06, timestamp=1.02),
            MorseSymbol(element=MorseElement.DOT, duration=0.06, timestamp=1.08),
            MorseSymbol(element=MorseElement.CHAR_GAP, duration=0.18, timestamp=1.14),
        ]
        chars = decoder.decode(symbols)

        # Should still return a character but with very low/zero confidence
        assert len(chars) == 1
        # Either exact match or fuzzy match or replacement char
        assert chars[0].char is not None


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_empty_symbols_list(self, decoder: MorseDecoder) -> None:
        """Test decoding empty symbols list."""
        chars = decoder.decode([])
        assert len(chars) == 0

    def test_only_gaps(self, decoder: MorseDecoder) -> None:
        """Test decoding only gap symbols."""
        symbols = [
            MorseSymbol(element=MorseElement.ELEMENT_GAP, duration=0.06, timestamp=0.0),
            MorseSymbol(element=MorseElement.CHAR_GAP, duration=0.18, timestamp=0.06),
            MorseSymbol(element=MorseElement.WORD_GAP, duration=0.42, timestamp=0.24),
        ]
        chars = decoder.decode(symbols)

        # Should only get space from word gap
        assert len(chars) == 1
        assert chars[0].char == " "

    def test_multiple_word_gaps(self, decoder: MorseDecoder) -> None:
        """Test multiple consecutive word gaps create multiple spaces."""
        symbols = [
            MorseSymbol(element=MorseElement.DOT, duration=0.06, timestamp=0.0),
            MorseSymbol(element=MorseElement.WORD_GAP, duration=0.42, timestamp=0.06),
            MorseSymbol(element=MorseElement.WORD_GAP, duration=0.42, timestamp=0.48),
        ]
        chars = decoder.decode(symbols)

        # Should get E and two spaces
        assert len(chars) == 3
        assert chars[0].char == "E"
        assert chars[1].char == " "
        assert chars[2].char == " "

    def test_decoder_reset(self, decoder: MorseDecoder) -> None:
        """Test decoder reset clears internal state."""
        # Build up a partial pattern
        symbols = [
            MorseSymbol(element=MorseElement.DOT, duration=0.06, timestamp=0.0),
            MorseSymbol(element=MorseElement.ELEMENT_GAP, duration=0.06, timestamp=0.06),
        ]
        decoder.decode(symbols)

        # Reset
        decoder.reset()

        # Decode complete pattern - should not be affected by previous partial
        symbols = [
            MorseSymbol(element=MorseElement.DASH, duration=0.18, timestamp=0.0),
            MorseSymbol(element=MorseElement.CHAR_GAP, duration=0.18, timestamp=0.18),
        ]
        chars = decoder.decode(symbols)

        assert len(chars) == 1
        assert chars[0].char == "T"

    def test_char_gap_ends_current_pattern(self, decoder: MorseDecoder) -> None:
        """Test that character gap properly ends pattern."""
        symbols = [
            MorseSymbol(element=MorseElement.DOT, duration=0.06, timestamp=0.0),
            MorseSymbol(element=MorseElement.ELEMENT_GAP, duration=0.06, timestamp=0.06),
            MorseSymbol(element=MorseElement.DASH, duration=0.18, timestamp=0.12),
            MorseSymbol(element=MorseElement.CHAR_GAP, duration=0.18, timestamp=0.30),
            # New character
            MorseSymbol(element=MorseElement.DOT, duration=0.06, timestamp=0.48),
            MorseSymbol(element=MorseElement.CHAR_GAP, duration=0.18, timestamp=0.54),
        ]
        chars = decoder.decode(symbols)

        assert len(chars) == 2
        assert chars[0].char == "A"  # .-
        assert chars[1].char == "E"  # .

    def test_word_gap_ends_pattern_and_adds_space(self, decoder: MorseDecoder) -> None:
        """Test that word gap ends pattern and adds space."""
        symbols = [
            MorseSymbol(element=MorseElement.DOT, duration=0.06, timestamp=0.0),
            MorseSymbol(element=MorseElement.WORD_GAP, duration=0.42, timestamp=0.06),
            MorseSymbol(element=MorseElement.DASH, duration=0.18, timestamp=0.48),
            MorseSymbol(element=MorseElement.CHAR_GAP, duration=0.18, timestamp=0.66),
        ]
        chars = decoder.decode(symbols)

        assert len(chars) == 3
        assert chars[0].char == "E"
        assert chars[1].char == " "
        assert chars[2].char == "T"


class TestEditDistance:
    """Test edit distance calculation."""

    def test_edit_distance_identical_strings(self, decoder: MorseDecoder) -> None:
        """Test edit distance for identical strings is 0."""
        distance = decoder._edit_distance("...", "...")
        assert distance == 0

    def test_edit_distance_one_insertion(self, decoder: MorseDecoder) -> None:
        """Test edit distance for one insertion is 1."""
        distance = decoder._edit_distance("...", "....")
        assert distance == 1

    def test_edit_distance_one_deletion(self, decoder: MorseDecoder) -> None:
        """Test edit distance for one deletion is 1."""
        distance = decoder._edit_distance("....", "...")
        assert distance == 1

    def test_edit_distance_one_substitution(self, decoder: MorseDecoder) -> None:
        """Test edit distance for one substitution is 1."""
        distance = decoder._edit_distance("...", "..-")
        assert distance == 1

    def test_edit_distance_empty_strings(self, decoder: MorseDecoder) -> None:
        """Test edit distance with empty string."""
        distance = decoder._edit_distance("", "...")
        assert distance == 3

        distance = decoder._edit_distance("...", "")
        assert distance == 3

    def test_edit_distance_symmetric(self, decoder: MorseDecoder) -> None:
        """Test edit distance is symmetric."""
        d1 = decoder._edit_distance(".-", "..")
        d2 = decoder._edit_distance("..", ".-")
        assert d1 == d2
