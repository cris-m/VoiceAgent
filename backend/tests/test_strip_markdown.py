import pytest

# Import only the pure function, not the route module so we avoid
# triggering model-loading side-effects at import time.
from api.routes.v1.voice import _strip_markdown


class TestBoldAndItalic:
    def test_bold_stripped(self):
        assert _strip_markdown("Hello **world** today") == "Hello world today"

    def test_italic_star_stripped(self):
        assert _strip_markdown("Hello *world* today") == "Hello world today"

    def test_italic_underscore_stripped(self):
        assert _strip_markdown("Hello __world__ today") == "Hello world today"

    def test_bold_and_italic_combined(self):
        assert _strip_markdown("**Bold** and *italic* text") == "Bold and italic text"

    def test_unbalanced_bold_preserved(self):
        # Unbalanced delimiters should not eat content
        result = _strip_markdown("Hello **world today")
        assert "world today" in result

    def test_no_dotall_across_lines(self):
        # Critical: multiline bold should NOT match across newlines.
        # If DOTALL were used, "**Line1\nLine2**" would collapse both lines.
        text = "**Line1\nLine2**"
        result = _strip_markdown(text)
        assert "Line1" in result
        assert "Line2" in result


class TestHeaders:
    def test_h1_stripped(self):
        assert _strip_markdown("# Introduction") == "Introduction"

    def test_h2_stripped(self):
        assert _strip_markdown("## Section Title") == "Section Title"

    def test_h3_stripped(self):
        assert _strip_markdown("### Subsection") == "Subsection"

    def test_header_with_trailing_text_inline(self):
        # sanitize_for_tts collapses to a single line before _strip_markdown runs
        result = _strip_markdown("## Title words here")
        assert result == "Title words here"

    def test_non_header_hash_preserved(self):
        result = _strip_markdown("Color #1 is blue")
        assert "#1" in result


class TestInlineCode:
    def test_inline_code_stripped(self):
        assert _strip_markdown("Run `ls -la` now") == "Run ls -la now"

    def test_inline_code_multiple(self):
        result = _strip_markdown("Use `foo` or `bar`")
        assert result == "Use foo or bar"

    def test_code_content_preserved(self):
        result = _strip_markdown("`python main.py`")
        assert "python main.py" in result


class TestLinks:
    def test_link_text_preserved(self):
        assert _strip_markdown("[Click here](https://example.com)") == "Click here"

    def test_link_url_removed(self):
        result = _strip_markdown("[docs](https://docs.example.com)")
        assert "https://docs.example.com" not in result
        assert "docs" in result

    def test_link_with_adjacent_text(self):
        result = _strip_markdown("See [this page](http://x.com) for more")
        assert result == "See this page for more"

    def test_no_dotall_link_across_lines(self):
        # Square-bracket [text](url) must NOT span newlines without DOTALL
        text = "[text1\ntext2](url)"
        result = _strip_markdown(text)
        assert "text1" in result or "text2" in result


class TestLists:
    def test_dash_list_stripped(self):
        result = _strip_markdown("- item one")
        assert result == "item one"

    def test_asterisk_list_stripped(self):
        result = _strip_markdown("* item two")
        assert result == "item two"

    def test_plus_list_stripped(self):
        result = _strip_markdown("+ item three")
        assert result == "item three"


class TestBlockquotes:
    def test_blockquote_stripped(self):
        result = _strip_markdown("> quoted text here")
        assert result == "quoted text here"


class TestHorizontalRules:
    def test_triple_dash_stripped(self):
        result = _strip_markdown("---")
        assert result == ""

    def test_inline_triple_dash_with_spaces_stripped(self):
        result = _strip_markdown("before --- after")
        assert "---" not in result
        assert "before" in result
        assert "after" in result


class TestMixedMarkdown:
    def test_realistic_response_cleaned(self):
        text = "**Key point**: use `pip install` and read [docs](https://example.com)."
        result = _strip_markdown(text)
        assert "**" not in result
        assert "`" not in result
        assert "https://example.com" not in result
        assert "Key point" in result
        assert "pip install" in result
        assert "docs" in result

    def test_empty_string(self):
        assert _strip_markdown("") == ""

    def test_plain_text_unchanged(self):
        text = "Hello world this is plain text."
        assert _strip_markdown(text) == text
