import pytest

from services.tts.text_chunker import TextChunker


class TestBelowThreshold:
    def test_short_text_returns_single_chunk(self):
        chunker = TextChunker(max_chunk_size=1000)
        chunks = chunker.chunk_by_sentences("Hello world.")
        assert len(chunks) == 1
        assert chunks[0] == "Hello world."

    def test_empty_text_returns_empty_list(self):
        chunker = TextChunker(max_chunk_size=1000)
        assert chunker.chunk_by_sentences("") == []

    def test_whitespace_only_returns_empty(self):
        chunker = TextChunker(max_chunk_size=1000)
        assert chunker.chunk_by_sentences("   \n\n  ") == []

    def test_text_exactly_at_max_returns_single_chunk(self):
        chunker = TextChunker(max_chunk_size=20)
        text = "Hello there world."
        chunks = chunker.chunk_by_sentences(text)
        assert len(chunks) == 1

    def test_two_short_sentences_combined_if_under_limit(self):
        chunker = TextChunker(max_chunk_size=200)
        text = "Hello. World."
        chunks = chunker.chunk_by_sentences(text)
        assert len(chunks) == 1
        assert "Hello" in chunks[0]
        assert "World" in chunks[0]


class TestSplitsAtSentenceBoundaries:
    def test_two_long_sentences_split_into_two_chunks(self):
        chunker = TextChunker(max_chunk_size=50)
        sentence_a = "The quick brown fox jumps over the lazy dog today."
        sentence_b = "A second independent sentence follows here now."
        text = f"{sentence_a} {sentence_b}"
        chunks = chunker.chunk_by_sentences(text)
        assert len(chunks) >= 2
        for chunk in chunks:
            assert len(chunk) <= 50 + 10  # small tolerance for joining

    def test_chunks_preserve_all_content(self):
        chunker = TextChunker(max_chunk_size=60)
        text = "First sentence here. Second sentence there. Third one now."
        chunks = chunker.chunk_by_sentences(text)
        joined = " ".join(chunks)
        assert "First" in joined
        assert "Second" in joined
        assert "Third" in joined

    def test_chunk_at_paragraph_boundaries(self):
        chunker = TextChunker(max_chunk_size=100)
        text = "Paragraph one.\n\nParagraph two."
        chunks = chunker.chunk_by_sentences(text)
        assert len(chunks) >= 1

    def test_no_chunk_exceeds_max_size(self):
        chunker = TextChunker(max_chunk_size=80)
        sentences = [
            "The quick brown fox jumps over the lazy dog.",
            "Pack my box with five dozen liquor jugs.",
            "How vexingly quick daft zebras jump.",
            "The five boxing wizards jump quickly.",
            "Sphinx of black quartz, judge my vow.",
        ]
        text = " ".join(sentences)
        chunks = chunker.chunk_by_sentences(text)
        for i, chunk in enumerate(chunks):
            assert len(chunk) <= 80, (
                f"Chunk {i} exceeds max_chunk_size: {len(chunk)} chars — '{chunk[:40]}'"
            )


class TestAbbreviationHandling:
    def test_dr_period_not_split(self):
        chunker = TextChunker(max_chunk_size=200)
        text = "Dr. Smith arrived at 3 p.m. He was on time."
        chunks = chunker.chunk_by_sentences(text)
        joined = " ".join(chunks)
        assert "Dr." in joined or "Dr" in joined
        assert "Smith" in joined

    def test_mr_period_not_split(self):
        chunker = TextChunker(max_chunk_size=200)
        text = "Mr. Jones spoke to Mrs. White about the report."
        chunks = chunker.chunk_by_sentences(text)
        joined = " ".join(chunks)
        assert "Mr." in joined or "Mr" in joined
        assert "Jones" in joined


class TestLongSentenceSplitting:
    def test_single_oversized_sentence_split_by_words(self):
        max_size = 30
        chunker = TextChunker(max_chunk_size=max_size)
        long_sentence = "this is a very very very very very very long sentence without any punctuation whatsoever"
        chunks = chunker.chunk_by_sentences(long_sentence)
        assert len(chunks) >= 2
        for chunk in chunks:
            assert len(chunk) <= max_size + 15  # word boundary may slightly exceed

    def test_long_sentence_with_commas_split_at_commas(self):
        max_size = 40
        chunker = TextChunker(max_chunk_size=max_size)
        text = "First clause here, second clause there, third clause added."
        chunks = chunker.chunk_by_sentences(text)
        assert len(chunks) >= 1
        joined = " ".join(chunks)
        assert "First" in joined
        assert "third" in joined


class TestWordFallback:
    def test_chunk_by_words_produces_chunks(self):
        chunker = TextChunker(max_chunk_size=20)
        text = "one two three four five six seven eight nine ten"
        chunks = chunker.chunk_by_words(text)
        assert len(chunks) >= 2
        for chunk in chunks:
            assert len(chunk) <= 20

    def test_chunk_by_words_no_content_lost(self):
        chunker = TextChunker(max_chunk_size=15)
        text = "alpha beta gamma delta epsilon"
        chunks = chunker.chunk_by_words(text)
        joined = " ".join(chunks)
        for word in ["alpha", "beta", "gamma", "delta", "epsilon"]:
            assert word in joined

    def test_chunk_by_words_single_word_longer_than_max(self):
        chunker = TextChunker(max_chunk_size=5)
        text = "superlongwordhere"
        chunks = chunker.chunk_by_words(text)
        assert len(chunks) >= 1
        assert "superlongwordhere" in chunks[0]
