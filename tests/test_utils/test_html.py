"""Tests for HTML utilities."""

from bs4 import BeautifulSoup
from epub_recipe_parser.utils.html import HTMLParser


def test_parse_html():
    """Test parsing HTML content."""
    content = b"<html><body><p>Test</p></body></html>"
    soup = HTMLParser.parse_html(content)
    assert soup is not None
    assert soup.find("p") is not None


def test_parse_html_removes_scripts():
    """Test that scripts are removed."""
    content = b"<html><body><script>alert('test')</script><p>Test</p></body></html>"
    soup = HTMLParser.parse_html(content)
    assert soup.find("script") is None
    assert soup.find("p") is not None


def test_extract_text():
    """Test text extraction from soup."""
    html = "<div><p>Line 1</p><p>Line 2</p></div>"
    soup = BeautifulSoup(html, "html.parser")
    text = HTMLParser.extract_text(soup)
    assert "Line 1" in text
    assert "Line 2" in text


def test_extract_from_list():
    """Test extracting items from HTML list."""
    html = "<ul><li>Item 1</li><li>Item 2</li><li>Item 3</li></ul>"
    soup = BeautifulSoup(html, "html.parser")
    ul = soup.find("ul")
    items = HTMLParser.extract_from_list(ul)
    assert len(items) == 3
    assert "Item 1" in items
    assert "Item 2" in items
    assert "Item 3" in items


def test_find_section_by_header():
    """Test finding content section by header."""
    html = """
    <div>
        <h3>Ingredients</h3>
        <ul>
            <li>Item 1</li>
            <li>Item 2</li>
        </ul>
    </div>
    """
    soup = BeautifulSoup(html, "html.parser")
    result = HTMLParser.find_section_by_header(soup, ["ingredients"])
    assert result is not None
    assert "Item 1" in result
    assert "Item 2" in result


def test_split_by_headers():
    """Test splitting document by headers."""
    html = """
    <html>
        <body>
            <h2>Recipe 1</h2>
            <p>Content 1</p>
            <h2>Recipe 2</h2>
            <p>Content 2</p>
            <h2>Recipe 3</h2>
            <p>Content 3</p>
        </body>
    </html>
    """
    soup = BeautifulSoup(html, "html.parser")
    sections = HTMLParser.split_by_headers(soup)
    assert len(sections) > 0
    titles = [title for title, _ in sections]
    assert "Recipe 1" in titles or "Recipe 2" in titles


def test_split_by_headers_no_headers():
    """Test split_by_headers with no headers - should extract title from content."""
    html = "<html><body><p>Just content</p></body></html>"
    soup = BeautifulSoup(html, "html.parser")
    sections = HTMLParser.split_by_headers(soup)
    assert len(sections) == 1
    # With enhanced title extraction, should extract "Just content" as title
    assert sections[0][0] == "Just content"
