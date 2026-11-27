"""Tests for metadata extractor."""

from bs4 import BeautifulSoup
from epub_recipe_parser.extractors.metadata import MetadataExtractor


def test_extract_serves():
    """Test extracting serving size."""
    html = "<div><p>Serves: 4-6 people</p></div>"
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text()

    metadata = MetadataExtractor.extract(soup, text)
    assert "serves" in metadata
    assert "4-6" in metadata["serves"]


def test_extract_prep_time():
    """Test extracting preparation time (now standardized to minutes)."""
    html = "<div><p>Prep time: 15 minutes</p></div>"
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text()

    metadata = MetadataExtractor.extract(soup, text)
    assert "prep_time" in metadata
    # Time is now standardized to minutes as an integer string
    assert metadata["prep_time"] == "15"


def test_extract_cook_time():
    """Test extracting cooking time (now standardized to minutes)."""
    html = "<div><p>Cook time: 30 minutes</p></div>"
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text()

    metadata = MetadataExtractor.extract(soup, text)
    assert "cook_time" in metadata
    # Time is now standardized to minutes as an integer string
    assert metadata["cook_time"] == "30"


def test_extract_cooking_method():
    """Test extracting cooking method from content."""
    html = "<div><h2>Grilled Chicken</h2><p>This grilled recipe is perfect.</p></div>"
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text()

    metadata = MetadataExtractor.extract(soup, text, title="Grilled Chicken")
    assert "cooking_method" in metadata
    assert metadata["cooking_method"] == "grill"


def test_extract_protein_type():
    """Test extracting protein type from content."""
    html = "<div><h2>Beef Steak</h2><p>A delicious beef recipe.</p></div>"
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text()

    metadata = MetadataExtractor.extract(soup, text, title="Beef Steak")
    assert "protein_type" in metadata
    assert metadata["protein_type"] == "beef"


def test_extract_multiple_metadata():
    """Test extracting multiple metadata fields."""
    html = """
    <div>
        <h2>Smoked Pork Ribs</h2>
        <p>Serves: 6</p>
        <p>Prep time: 20 minutes</p>
        <p>Cook time: 4 hours</p>
        <p>Delicious smoked pork ribs recipe.</p>
    </div>
    """
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text()

    metadata = MetadataExtractor.extract(soup, text, title="Smoked Pork Ribs")
    assert "serves" in metadata
    assert "prep_time" in metadata
    assert "cook_time" in metadata
    assert "cooking_method" in metadata
    assert metadata["cooking_method"] == "smoke"
    assert "protein_type" in metadata
    assert metadata["protein_type"] == "pork"


def test_extract_no_metadata():
    """Test extraction when no metadata is present."""
    html = "<div><p>Just some random text.</p></div>"
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text()

    metadata = MetadataExtractor.extract(soup, text)
    assert isinstance(metadata, dict)
    # Should return empty dict or dict with no metadata
    assert len(metadata) == 0 or all(key not in metadata for key in ["serves", "prep_time"])
