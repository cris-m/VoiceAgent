from api.routes.v1.voice import _is_incomplete_utterance


class TestEmptyAndTrivial:
    def test_empty_string_is_incomplete(self):
        assert _is_incomplete_utterance("") is True

    def test_whitespace_only_is_incomplete(self):
        assert _is_incomplete_utterance("   ") is True

    def test_punctuation_only_is_incomplete(self):
        # Strip of ".!?," leaves nothing — treated as incomplete
        assert _is_incomplete_utterance("...") is True

    def test_single_word_is_NOT_incomplete(self):
        assert _is_incomplete_utterance("hello") is False


class TestHangingModals:
    def test_trailing_can(self):
        assert _is_incomplete_utterance("I can") is True

    def test_trailing_could(self):
        # The function checks the LAST word. "Could you" ends in "you" (not in
        # the incomplete set) — so the sentence is treated as complete. This is
        # a deliberate design tradeoff: checking only the final word keeps the
        # classifier O(1) but misses some patterns. We assert the actual behavior.
        assert _is_incomplete_utterance("Could you") is False
        assert _is_incomplete_utterance("I could") is True

    def test_trailing_would(self):
        assert _is_incomplete_utterance("I would") is True

    def test_trailing_should(self):
        assert _is_incomplete_utterance("We should") is True

    def test_trailing_will(self):
        assert _is_incomplete_utterance("She will") is True

    def test_trailing_might(self):
        assert _is_incomplete_utterance("It might") is True

    def test_trailing_must(self):
        assert _is_incomplete_utterance("You must") is True


class TestHangingConjunctions:
    def test_trailing_and(self):
        assert _is_incomplete_utterance("I want coffee and") is True

    def test_trailing_but(self):
        assert _is_incomplete_utterance("I like it but") is True

    def test_trailing_or(self):
        assert _is_incomplete_utterance("You can do this or") is True

    def test_trailing_because(self):
        assert _is_incomplete_utterance("I left because") is True

    def test_trailing_if(self):
        assert _is_incomplete_utterance("Let me know if") is True

    def test_trailing_when(self):
        assert _is_incomplete_utterance("Tell me when") is True

    def test_trailing_although(self):
        assert _is_incomplete_utterance("I agree although") is True

    def test_trailing_while(self):
        assert _is_incomplete_utterance("I was reading while") is True


class TestHangingPrepositions:
    def test_trailing_to(self):
        assert _is_incomplete_utterance("I need to") is True

    def test_trailing_of(self):
        assert _is_incomplete_utterance("A cup of") is True

    def test_trailing_in(self):
        assert _is_incomplete_utterance("Put it in") is True

    def test_trailing_at(self):
        assert _is_incomplete_utterance("I'll be at") is True

    def test_trailing_from(self):
        assert _is_incomplete_utterance("Take it from") is True

    def test_trailing_with(self):
        assert _is_incomplete_utterance("Come with") is True

    def test_trailing_about(self):
        assert _is_incomplete_utterance("Tell me about") is True

    def test_trailing_into(self):
        assert _is_incomplete_utterance("We ran into") is True


class TestHangingArticlesAndDeterminers:
    def test_trailing_a(self):
        assert _is_incomplete_utterance("I want a") is True

    def test_trailing_an(self):
        assert _is_incomplete_utterance("Give me an") is True

    def test_trailing_the(self):
        assert _is_incomplete_utterance("Open the") is True

    def test_trailing_this(self):
        assert _is_incomplete_utterance("Can you do this") is True

    def test_trailing_my(self):
        assert _is_incomplete_utterance("It is my") is True


class TestHangingFillers:
    def test_trailing_um(self):
        assert _is_incomplete_utterance("I want um") is True

    def test_trailing_uh(self):
        assert _is_incomplete_utterance("So uh") is True

    def test_trailing_like(self):
        assert _is_incomplete_utterance("It was like") is True

    def test_trailing_well(self):
        # single-word input bypasses the trailing-filler check
        assert _is_incomplete_utterance("Well") is False

    def test_trailing_well_after_prefix(self):
        assert _is_incomplete_utterance("I think well") is True


class TestCompleteSentences:
    def test_complete_statement(self):
        assert _is_incomplete_utterance("What time is it?") is False

    def test_complete_command(self):
        assert _is_incomplete_utterance("Play some music.") is False

    def test_complete_question(self):
        assert _is_incomplete_utterance("How does photosynthesis work") is False

    def test_complete_noun_ending(self):
        assert _is_incomplete_utterance("I need a coffee") is False

    def test_complete_verb_ending(self):
        assert _is_incomplete_utterance("Please summarize") is False

    def test_complete_proper_noun(self):
        assert _is_incomplete_utterance("My name is Alice") is False

    def test_yes_no(self):
        assert _is_incomplete_utterance("Yes") is False
        assert _is_incomplete_utterance("No") is False

    def test_complete_long_sentence(self):
        text = "Can you book me a flight from New York to London next Tuesday morning"
        assert _is_incomplete_utterance(text) is False


class TestPunctuationHandling:
    def test_trailing_and_with_comma(self):
        # comma is stripped before the trailing-word check
        assert _is_incomplete_utterance("hello, and") is True

    def test_complete_with_question_mark(self):
        assert _is_incomplete_utterance("Are you there?") is False
