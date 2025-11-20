"""Morse code decoder with international morse code lookup."""

from dataclasses import dataclass, field

from continuous_wave.config import CWConfig
from continuous_wave.models import DecodedCharacter, MorseElement, MorseSymbol
from continuous_wave.protocols import Decoder

# International Morse Code lookup table
MORSE_CODE: dict[str, str] = {
    # Letters
    ".-": "A",
    "-...": "B",
    "-.-.": "C",
    "-..": "D",
    ".": "E",
    "..-.": "F",
    "--.": "G",
    "....": "H",
    "..": "I",
    ".---": "J",
    "-.-": "K",
    ".-..": "L",
    "--": "M",
    "-.": "N",
    "---": "O",
    ".--.": "P",
    "--.-": "Q",
    ".-.": "R",
    "...": "S",
    "-": "T",
    "..-": "U",
    "...-": "V",
    ".--": "W",
    "-..-": "X",
    "-.--": "Y",
    "--..": "Z",
    # Numbers
    "-----": "0",
    ".----": "1",
    "..---": "2",
    "...--": "3",
    "....-": "4",
    ".....": "5",
    "-....": "6",
    "--...": "7",
    "---..": "8",
    "----.": "9",
    # Punctuation
    ".-.-.-": ".",  # Period
    "--..--": ",",  # Comma
    "..--..": "?",  # Question mark
    ".----.": "'",  # Apostrophe
    "-.-.--": "!",  # Exclamation mark
    "-..-.": "/",  # Slash
    "-.--.": "(",  # Open parenthesis
    "-.--.-": ")",  # Close parenthesis
    ".-...": "&",  # Ampersand
    "---...": ":",  # Colon
    "-.-.-.": ";",  # Semicolon
    "-...-": "=",  # Equals
    "-....-": "-",  # Minus/hyphen
    "..--.-": "_",  # Underscore
    ".-..-.": '"',  # Quote
    "...-..-": "$",  # Dollar sign
    ".--.-.": "@",  # At sign
    # Prosigns (special signals)
    ".-.-": "<AA>",  # New line
    "-...-.-": "<BT>",  # Break
    ".-.-.": "<AR>",  # End of message (also interpreted as +)
    "-.-.-": "<KA>",  # Beginning of message
    "...-.-": "<SK>",  # End of contact
    "........": "<HH>",  # Error
}


@dataclass
class MorseDecoder(Decoder):
    """Morse code decoder using lookup table.

    Converts sequences of dots and dashes to characters with
    confidence scoring.
    """

    config: CWConfig
    _current_pattern: list[MorseElement] = field(default_factory=list, init=False)
    _decoded_chars: list[DecodedCharacter] = field(default_factory=list, init=False)

    def decode(self, symbols: list[MorseSymbol]) -> list[DecodedCharacter]:
        """Decode Morse symbols to characters.

        Args:
            symbols: List of MorseSymbol objects to decode

        Returns:
            List of decoded characters (may be empty)
        """
        characters: list[DecodedCharacter] = []

        for symbol in symbols:
            if symbol.element in (MorseElement.DOT, MorseElement.DASH):
                # Add to current pattern
                self._current_pattern.append(symbol.element)

            elif symbol.element == MorseElement.CHAR_GAP:
                # End of character - decode it
                if self._current_pattern:
                    char = self._decode_pattern(self._current_pattern)
                    if char is not None:
                        characters.append(char)
                    self._current_pattern.clear()

            elif symbol.element == MorseElement.WORD_GAP:
                # End of word - decode current char and add space
                if self._current_pattern:
                    char = self._decode_pattern(self._current_pattern)
                    if char is not None:
                        characters.append(char)
                    self._current_pattern.clear()

                # Add space character
                characters.append(
                    DecodedCharacter(
                        char=" ",
                        confidence=1.0,
                        morse_pattern="",
                        timestamp=symbol.timestamp,
                    )
                )

            # ELEMENT_GAP is just ignored - it's between dots/dashes within a character

        return characters

    def flush(self) -> list[DecodedCharacter]:
        """Flush any pending pattern at end of stream.

        Decodes any accumulated morse pattern that hasn't been finalized
        with a CHAR_GAP or WORD_GAP.

        Returns:
            List of DecodedCharacter instances for any pending pattern
        """
        characters: list[DecodedCharacter] = []

        # Decode any pending pattern
        if self._current_pattern:
            char = self._decode_pattern(self._current_pattern)
            if char is not None:
                characters.append(char)
            self._current_pattern.clear()

        return characters

    def reset(self) -> None:
        """Reset decoder state."""
        self._current_pattern.clear()
        self._decoded_chars.clear()

    def _decode_pattern(self, pattern: list[MorseElement]) -> DecodedCharacter | None:
        """Decode a morse pattern to a character.

        Args:
            pattern: List of DOT and DASH elements

        Returns:
            DecodedCharacter if pattern is valid, None otherwise
        """
        if not pattern:
            return None

        # Convert pattern to string representation
        pattern_str = ""
        for element in pattern:
            if element == MorseElement.DOT:
                pattern_str += "."
            elif element == MorseElement.DASH:
                pattern_str += "-"

        # Look up in morse code table
        if pattern_str in MORSE_CODE:
            char = MORSE_CODE[pattern_str]
            return DecodedCharacter(
                char=char,
                confidence=1.0,  # Exact match
                morse_pattern=pattern_str,
                timestamp=0.0,  # Will be set by pipeline
            )

        # Try fuzzy matching for close patterns
        fuzzy_match = self._fuzzy_match(pattern_str)
        if fuzzy_match is not None:
            char, confidence = fuzzy_match
            return DecodedCharacter(
                char=char,
                confidence=confidence,
                morse_pattern=pattern_str,
                timestamp=0.0,
            )

        # Unknown pattern - return as error marker
        return DecodedCharacter(
            char="�",  # Replacement character
            confidence=0.0,
            morse_pattern=pattern_str,
            timestamp=0.0,
        )

    def _fuzzy_match(self, pattern: str) -> tuple[str, float] | None:
        """Try to find a close match for an invalid pattern.

        Uses simple edit distance to find similar patterns.

        Args:
            pattern: Morse pattern string

        Returns:
            Tuple of (character, confidence) if close match found, None otherwise
        """
        if not pattern:
            return None

        min_distance = float("inf")
        best_match = None

        for morse_pattern, char in MORSE_CODE.items():
            distance = self._edit_distance(pattern, morse_pattern)

            if distance < min_distance:
                min_distance = distance
                best_match = char

        # Only accept fuzzy matches with small edit distance
        if min_distance <= 1 and best_match is not None:
            # Confidence decreases with edit distance
            confidence = 1.0 - (min_distance / 3.0)
            return best_match, max(0.3, confidence)

        return None

    def _edit_distance(self, s1: str, s2: str) -> int:
        """Calculate Levenshtein edit distance between two strings.

        Args:
            s1: First string
            s2: Second string

        Returns:
            Minimum number of edits to transform s1 into s2
        """
        if len(s1) < len(s2):
            return self._edit_distance(s2, s1)

        if len(s2) == 0:
            return len(s1)

        previous_row = list(range(len(s2) + 1))
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                # Cost of insertions, deletions, or substitutions
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row

        return previous_row[-1]
