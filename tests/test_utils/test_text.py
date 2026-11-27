"""Tests for text utilities."""

from epub_recipe_parser.utils.text import clean_text, normalize_whitespace


def test_clean_text_removes_brackets():
    """Test that clean_text removes curly brackets."""
    text = "Recipe {ingredient} with {notes}"
    result = clean_text(text)
    assert "{" not in result
    assert "}" not in result
    assert "Recipe" in result


def test_clean_text_removes_markdown_links():
    """Test that clean_text removes markdown link syntax."""
    text = "Check [this recipe](http://example.com) out"
    result = clean_text(text)
    assert "[" not in result
    assert "]" not in result
    assert "(" not in result
    assert "Check" in result


def test_clean_text_strips_whitespace():
    """Test that clean_text strips leading/trailing whitespace."""
    text = "  Recipe Title  "
    result = clean_text(text)
    assert result == "Recipe Title"


def test_normalize_whitespace():
    """Test whitespace normalization."""
    text = "Line 1\n\n\nLine 2\n  \nLine 3"
    result = normalize_whitespace(text)
    lines = result.split("\n")
    assert len(lines) == 3
    assert "Line 1" in lines
    assert "Line 2" in lines
    assert "Line 3" in lines


def test_normalize_whitespace_removes_empty_lines():
    """Test that empty lines are removed."""
    text = "Line 1\n\nLine 2\n  \nLine 3"
    result = normalize_whitespace(text)
    assert "\n\n" not in result
