from typing import List

from utils import get_logger

logger = get_logger(__name__)

_ABBREVIATIONS = {
    "mr",
    "mrs",
    "ms",
    "dr",
    "sr",
    "jr",
    "st",
    "vs",
    "etc",
    "i.e",
    "e.g",
    "u.s",
    "u.k",
    "a.m",
    "p.m",
    "no",
    "prof",
    "Rev",
    "Gen",
    "col",
    "maj",
    "capt",
    "inc",
    "ltd",
    "co",
}


class TextChunker:
    """Splits text at sentence boundaries for TTS processing.

    Uses intelligent sentence detection that respects abbreviations and
    natural language patterns. Designed for streaming TTS where audio quality
    depends on chunk boundaries being at natural pauses.
    """

    def __init__(self, max_chunk_size: int = 1000):
        self.max_chunk_size = max_chunk_size

    def _extract_sentences(self, text: str) -> List[str]:
        paragraphs = text.split("\n\n")

        all_sentences = []
        for para in paragraphs:
            if not para.strip():
                continue

            sentences = self._split_paragraph_into_sentences(para.strip())
            all_sentences.extend(sentences)

        return all_sentences if all_sentences else [text.strip()]

    def _split_paragraph_into_sentences(self, para: str) -> List[str]:
        sentences = []
        current = ""
        i = 0

        while i < len(para):
            char = para[i]
            current += char

            if char in ".!?":
                if char == ".":
                    # Skip abbreviations: scan back to start of preceding word
                    word_start = len(current) - 2
                    while word_start >= 0 and current[word_start] not in " \n\t":
                        word_start -= 1
                    word = current[word_start + 1 : -1].lower()

                    # Skip abbreviations and decimal numbers
                    if word in _ABBREVIATIONS or (word.isdigit() and i + 1 < len(para) and para[i + 1].isdigit()):
                        i += 1
                        continue

                # Treat as continuation if next char is lowercase
                if i + 1 < len(para) and para[i + 1].islower():
                    i += 1
                    continue

                sentence = current.strip()
                if sentence:
                    sentences.append(sentence)
                current = ""

            i += 1

        if current.strip():
            sentences.append(current.strip())

        return sentences

    def chunk_by_sentences(self, text: str) -> List[str]:
        """Split text into ≤max_chunk_size chunks at sentence boundaries."""
        if not text or not text.strip():
            return []

        sentences = self._extract_sentences(text)

        if not sentences:
            logger.warning("No sentences extracted, returning original text")
            return [text.strip()]

        chunks = []
        current_chunk = ""

        for sentence in sentences:
            # If a single sentence is itself bigger than max_chunk_size,
            # split it at word boundaries before grouping. Without this,
            # one very long sentence (common in technical content) lands
            # in a chunk that exceeds the TTS token limit and gets words
            # silently dropped during synthesis.
            sub_sentences = self._split_long_sentence(sentence) if len(sentence) > self.max_chunk_size else [sentence]

            for sub in sub_sentences:
                if not current_chunk:
                    current_chunk = sub
                    continue
                proposed = current_chunk + " " + sub
                if len(proposed) <= self.max_chunk_size:
                    current_chunk = proposed
                else:
                    chunks.append(current_chunk)
                    current_chunk = sub

        if current_chunk:
            chunks.append(current_chunk)

        if not chunks:
            chunks = self.chunk_by_words(text)

        logger.info(
            f"Split text ({len(text)} chars) into {len(chunks)} chunks "
            f"(avg {len(text) // len(chunks) if chunks else 0} chars/chunk)"
        )
        return chunks

    def _split_long_sentence(self, sentence: str) -> List[str]:
        """Break a single oversized sentence into ≤max_chunk_size pieces.

        Prefers natural pause points: comma, semicolon, dash, parenthesis.
        Falls back to word boundaries if no such punctuation is available.
        """
        if len(sentence) <= self.max_chunk_size:
            return [sentence]

        # Comma/semicolon split preserves prosody better than word-level.
        import re as _re

        parts = _re.split(r"([,;:—–])", sentence)
        # Re-attach punctuation to the preceding fragment so we don't
        # produce orphan punctuation chunks.
        merged: List[str] = []
        for i in range(0, len(parts), 2):
            piece = parts[i].strip()
            if i + 1 < len(parts):
                piece = (piece + parts[i + 1]).strip()
            if piece:
                merged.append(piece)

        result: List[str] = []
        current = ""
        for piece in merged:
            if len(piece) > self.max_chunk_size:
                # Even the comma-split piece is too long — fall back to
                # word-level splitting on JUST this piece.
                if current:
                    result.append(current)
                    current = ""
                result.extend(self.chunk_by_words(piece))
                continue
            if not current:
                current = piece
                continue
            proposed = current + " " + piece
            if len(proposed) <= self.max_chunk_size:
                current = proposed
            else:
                result.append(current)
                current = piece
        if current:
            result.append(current)
        return result

    def chunk_by_words(self, text: str) -> List[str]:
        """Last-resort fallback when sentence/punctuation splitting fails."""
        words = text.split()
        chunks = []
        current_chunk = ""

        for word in words:
            if len(current_chunk) + len(word) + 1 > self.max_chunk_size and current_chunk:
                chunks.append(current_chunk.strip())
                current_chunk = word
            else:
                current_chunk += " " + word if current_chunk else word

        if current_chunk.strip():
            chunks.append(current_chunk.strip())

        return chunks if chunks else [text]
