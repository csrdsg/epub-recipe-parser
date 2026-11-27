"""Tests for recipe validator."""

from bs4 import BeautifulSoup
from epub_recipe_parser.core.validator import RecipeValidator


def test_is_valid_recipe_with_recipe():
    """Test validator identifies valid recipe content."""
    html = """
    <div>
        <h2>Grilled Chicken</h2>
        <p>2 cups flour, 1 tablespoon oil</p>
        <p>Heat the oil, add flour, mix well, cook for 20 minutes, serve hot</p>
    </div>
    """
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text()

    assert RecipeValidator.is_valid_recipe(soup, text, "Grilled Chicken") is True
    assert RecipeValidator.is_valid_recipe(soup, text, "RECIPE NOTES") is False


def test_is_valid_recipe_excludes_introduction():
    """Test validator excludes introduction pages."""
    html = "<div><p>Welcome to this cookbook. Enjoy!</p></div>"
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text()

    assert RecipeValidator.is_valid_recipe(soup, text, "Introduction") is False


def test_is_valid_recipe_excludes_index():
    """Test validator excludes index pages."""
    html = "<div><p>Page numbers and references</p></div>"
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text()

    assert RecipeValidator.is_valid_recipe(soup, text, "Index") is False


def test_is_valid_recipe_requires_minimum_content():
    """Test validator requires minimum content length."""
    html = "<div><p>Short text</p></div>"
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text()

    assert RecipeValidator.is_valid_recipe(soup, text, "Recipe") is False


def test_calculate_confidence_high():
    """Test confidence calculation for complete recipe."""
    text = "A" * 600
    ingredients = "B" * 250
    instructions = "C" * 350

    confidence = RecipeValidator.calculate_confidence(text, ingredients, instructions)
    assert confidence >= 0.8
    assert confidence <= 1.0


def test_calculate_confidence_low():
    """Test confidence calculation for incomplete recipe."""
    text = "A" * 100
    ingredients = "B" * 30
    instructions = ""

    confidence = RecipeValidator.calculate_confidence(text, ingredients, instructions)
    assert confidence < 0.5


def test_calculate_confidence_both_present_bonus():
    """Test bonus for having both ingredients and instructions."""
    text = "A" * 300
    ingredients = "B" * 150
    instructions = "C" * 200

    confidence = RecipeValidator.calculate_confidence(text, ingredients, instructions)
    # Should include the 0.2 bonus for both being present
    assert confidence >= 0.6
