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


def test_code_heavy_prose_requires_ingredient_evidence():
    prose = """
    <p>Prepare the input, add a value, and combine the two elements. This
    instruction describes how to format and display each ingredient in a list
    while preserving the string representation of the original object.</p>
    <pre class="programlisting">print(format(value))</pre>
    """
    technical = BeautifulSoup(prose, "html.parser")
    assert not RecipeValidator.is_valid_recipe(
        technical, technical.get_text(" "), "Formatting a String"
    )

    with_ingredients = BeautifulSoup(
        prose + '<ul class="ingredients"><li>Salt to taste</li></ul>', "html.parser"
    )
    assert RecipeValidator.is_valid_recipe(
        with_ingredients, with_ingredients.get_text(" "), "Seasoning"
    )


def test_one_incidental_measurement_does_not_make_travel_prose_a_recipe():
    soup = BeautifulSoup(
        "<p>Watch the harbor, take the ferry, and continue along the coast. "
        "The statue has 11 heads. The route instruction explains how to add "
        "a side trip before you return.</p>",
        "html.parser",
    )
    assert not RecipeValidator.is_valid_recipe(soup, soup.get_text(), "Plan Your Time")


def test_unmeasured_ingredient_list_is_recipe_evidence():
    soup = BeautifulSoup(
        "<ul><li>Fresh tomatoes</li><li>Salt to taste</li></ul>"
        "<p>Slice the tomatoes, toss with salt, and serve immediately.</p>",
        "html.parser",
    )
    assert RecipeValidator.is_valid_recipe(soup, soup.get_text(" "), "Salted Tomatoes")
