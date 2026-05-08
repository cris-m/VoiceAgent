"""Professional TTS text sanitization.

Removes characters and patterns that Text-To-Speech engines struggle with:
- Emoji and Unicode symbols
- Control characters and zero-width characters
- Excessive punctuation
- HTML entities and tags
- Malformed brackets/parentheses
- Excessive whitespace

Preserves:
- Contractions (can't, don't, etc.)
- Hyphenated words (well-known, state-of-the-art)
- Numbers and decimal points
- Common punctuation (. ! ?)
- Ellipsis patterns (... or …)
"""

import re
import unicodedata


class TTSSanitizer:
    # Unicode categories to remove
    # See: https://www.unicode.org/reports/tr44/#General_Category
    REMOVE_CATEGORIES = {
        "Cc",  # Control characters (except tab, newline which we handle separately)
        "Cf",  # Format characters (zero-width, soft hyphen, etc.)
        "Cs",  # Surrogate characters
        "Co",  # Private use characters
        "Cn",  # Unassigned characters
    }

    # Emoji and symbol ranges (Unicode blocks)
    EMOJI_RANGES = [
        (0x1F300, 0x1F9FF),  # Emoticons, Symbols, Pictographs, etc.
        (0x2600, 0x27BF),    # Miscellaneous Symbols, Dingbats
        (0x2300, 0x23FF),    # Miscellaneous Technical
        (0x2B50, 0x2B55),    # Stars
        (0x1F900, 0x1F9FF),  # Supplemental Symbols and Pictographs
    ]

    # URLs and emails pattern (to warn or remove)
    URL_EMAIL_PATTERN = re.compile(
        r"(?:https?://[^\s]+|[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})",
        re.IGNORECASE,
    )

    # HTML entity references
    HTML_ENTITY_PATTERN = re.compile(r"&(?:[a-z]+|#\d+|#x[0-9a-f]+);", re.IGNORECASE)

    # Multiple consecutive punctuation (e.g., "!!!", "???")
    EXCESSIVE_PUNCTUATION_PATTERN = re.compile(r"([!?.]){3,}")

    # Whitespace normalization
    WHITESPACE_PATTERN = re.compile(r"\s+")

    # Bracket/parenthesis characters that often come in pairs
    BRACKET_PATTERN = re.compile(r"[\[\]{}⟨⟩«»「」『』【】]")

    # Zero-width characters
    ZERO_WIDTH_CHARS = {
        "\u200b",  # Zero-width space
        "\u200c",  # Zero-width non-joiner
        "\u200d",  # Zero-width joiner
        "\ufeff",  # Zero-width no-break space (BOM)
        "\u061c",  # Arabic letter mark
    }

    def __init__(self, keep_diacritics: bool = True, remove_urls: bool = False):
        self.keep_diacritics = keep_diacritics
        self.remove_urls = remove_urls

    def sanitize(self, text: str, aggressive: bool = False) -> str:
        if not text:
            return ""

        text = text.strip()

        text = self._remove_zero_width(text)
        text = self._remove_control_characters(text)
        text = self._decode_html_entities(text)
        text = self._remove_emoji_and_symbols(text)

        if self.remove_urls:
            text = self.URL_EMAIL_PATTERN.sub("", text)

        if aggressive:
            text = self.BRACKET_PATTERN.sub("", text)

        if not self.keep_diacritics:
            text = self._remove_diacritics(text)

        if aggressive:
            text = self._normalize_quotes(text)

        text = self.EXCESSIVE_PUNCTUATION_PATTERN.sub(r"\1\1", text)
        text = self.WHITESPACE_PATTERN.sub(" ", text)
        text = text.strip()

        return text

    def _remove_zero_width(self, text: str) -> str:
        return "".join(c for c in text if c not in self.ZERO_WIDTH_CHARS)

    def _remove_control_characters(self, text: str) -> str:
        result = []
        for char in text:
            cat = unicodedata.category(char)
            if char == "\n":
                result.append(" ")
            elif char == "\t":
                result.append(" ")
            elif char == "\r":
                continue
            elif cat not in self.REMOVE_CATEGORIES:
                result.append(char)
        return "".join(result)

    def _decode_html_entities(self, text: str) -> str:
        import html

        try:
            return html.unescape(text)
        except Exception:
            return text

    def _remove_emoji_and_symbols(self, text: str) -> str:
        result = []
        for char in text:
            code_point = ord(char)

            is_emoji = any(
                start <= code_point <= end for start, end in self.EMOJI_RANGES
            )

            # "So" = Symbol-other, "Sk" = Symbol-modifier
            cat = unicodedata.category(char)
            is_symbol = cat in ("So", "Sk")

            if not is_emoji and not is_symbol:
                result.append(char)

        return "".join(result)

    def _remove_diacritics(self, text: str) -> str:
        """Remove combining diacritical marks (e.g. café → cafe)."""
        nfd = unicodedata.normalize("NFD", text)
        return "".join(c for c in nfd if unicodedata.category(c) != "Mn")

    def _normalize_quotes(self, text: str) -> str:
        # Smart single quotes
        text = text.replace("'", "'")  # Left single quotation mark
        text = text.replace("'", "'")  # Right single quotation mark
        text = text.replace("‛", "'")  # Reversed single quotation mark

        # Smart double quotes
        text = text.replace(""", '"')  # Left double quotation mark
        text = text.replace(""", '"')  # Right double quotation mark
        text = text.replace("„", '"')  # Double low-9 quotation mark

        text = text.replace("′", "'")  # Prime
        text = text.replace("″", '"')  # Double prime

        return text


_default_sanitizer = TTSSanitizer(keep_diacritics=True, remove_urls=False)
_aggressive_sanitizer = TTSSanitizer(keep_diacritics=False, remove_urls=True)


def sanitize_for_tts(text: str, aggressive: bool = False) -> str:
    """Sanitize text for TTS. Aggressive mode also strips diacritics, URLs, brackets, quotes."""
    sanitizer = _aggressive_sanitizer if aggressive else _default_sanitizer
    return sanitizer.sanitize(text, aggressive=aggressive)


def get_sanitizer(
    keep_diacritics: bool = True, remove_urls: bool = False
) -> TTSSanitizer:
    return TTSSanitizer(keep_diacritics=keep_diacritics, remove_urls=remove_urls)
