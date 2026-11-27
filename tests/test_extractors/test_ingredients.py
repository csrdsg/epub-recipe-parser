"""Tests for ingredients extractor."""

from bs4 import BeautifulSoup
from epub_recipe_parser.extractors.ingredients import IngredientsExtractor
from epub_recipe_parser.utils.extraction import normalize_extraction_result


def test_extract_ingredients_by_header():
    """Test extracting ingredients using header strategy."""
    html = """
    <div>
        <h3>Ingredients</h3>
        <ul>
            <li>2 cups flour</li>
            <li>1 tablespoon sugar</li>
            <li>3 eggs</li>
        </ul>
    </div>
    """
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text()

    extraction_result = IngredientsExtractor.extract(soup, text)
    result, metadata = normalize_extraction_result(extraction_result)
    assert result is not None
    assert "flour" in result
    assert "sugar" in result
    assert "eggs" in result


def test_extract_ingredients_by_measurements():
    """Test extracting ingredients using measurement detection."""
    html = """
    <div>
        <ul>
            <li>2 pounds chicken breast</li>
            <li>1 teaspoon salt</li>
            <li>3 tablespoons olive oil</li>
        </ul>
    </div>
    """
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text()

    extraction_result = IngredientsExtractor.extract(soup, text)
    result, metadata = normalize_extraction_result(extraction_result)
    assert result is not None
    assert "chicken" in result
    assert "salt" in result
    assert "oil" in result


def test_extract_ingredients_returns_none_without_content():
    """Test that extractor returns None for content without ingredients."""
    html = """
    <div>
        <p>This is just a paragraph with no measurements or ingredients list.</p>
    </div>
    """
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text()

    extraction_result = IngredientsExtractor.extract(soup, text)
    result, metadata = normalize_extraction_result(extraction_result)
    assert result is None


def test_extract_ingredients_minimum_length():
    """Test that extracted ingredients meet minimum length requirement."""
    html = """
    <div>
        <h3>Ingredients</h3>
        <ul>
            <li>2 cups flour</li>
            <li>1 tablespoon sugar</li>
        </ul>
    </div>
    """
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text()

    extraction_result = IngredientsExtractor.extract(soup, text)
    result, metadata = normalize_extraction_result(extraction_result)
    assert result is not None
    assert len(result) > 20  # Should be formatted with bullets


def test_extract_ingredients_with_for_the_pattern():
    """Test extracting ingredients with 'For the X' section headers."""
    text = """
    Baklawa Bites

    For the Simple Sugar Syrup
    1 cup (200 g) granulated sugar
    ½ cup (120 ml) water
    2–3 cardamom pods, broken

    For the Bites
    8 oz (227 g) phyllo dough, thawed
    1 cup (120 g) walnuts, finely chopped
    1 cup (120 g) raw pistachios, finely chopped
    ¾ cup (200 g) unsalted butter, melted

    Preheat oven to 350°F (180°C).
    Remove the phyllo dough from the package.
    """
    soup = BeautifulSoup("<div></div>", "html.parser")

    extraction_result = IngredientsExtractor.extract(soup, text)
    result, metadata = normalize_extraction_result(extraction_result)
    assert result is not None
    assert "For the Simple Sugar Syrup" in result
    assert "For the Bites" in result
    assert "granulated sugar" in result
    assert "phyllo dough" in result
    assert "walnuts" in result
    # Should not include instructions
    assert "Preheat" not in result


def test_extract_ingredients_consecutive_measurements_fallback():
    """Test fallback extraction of consecutive lines with measurements."""
    text = """
    Delicious Cake Recipe

    2 cups all-purpose flour
    1 cup granulated sugar
    3 large eggs
    ½ cup milk
    1 teaspoon vanilla extract

    Mix all ingredients together. Bake at 350°F for 30 minutes.
    """
    soup = BeautifulSoup("<div></div>", "html.parser")

    extraction_result = IngredientsExtractor.extract(soup, text)
    result, metadata = normalize_extraction_result(extraction_result)
    assert result is not None
    assert "all-purpose flour" in result
    assert "granulated sugar" in result
    assert "eggs" in result
    assert "milk" in result
    assert "vanilla extract" in result
    # Should not include instructions
    assert "Mix all ingredients" not in result


def test_is_ingredient_header():
    """Test ingredient header detection."""
    assert IngredientsExtractor._is_ingredient_header("For the Dough")
    assert IngredientsExtractor._is_ingredient_header("For the Simple Syrup")
    assert IngredientsExtractor._is_ingredient_header("Ingredients")
    assert IngredientsExtractor._is_ingredient_header("What You Need")

    # Should not match ingredient lines
    assert not IngredientsExtractor._is_ingredient_header("2 cups flour")
    assert not IngredientsExtractor._is_ingredient_header("1 tablespoon sugar")

    # Should not match overly long lines
    assert not IngredientsExtractor._is_ingredient_header(
        "This is a very long line that is probably not a header but something else entirely"
    )


def test_is_ingredient_line():
    """Test ingredient line detection."""
    assert IngredientsExtractor._is_ingredient_line("2 cups all-purpose flour")
    assert IngredientsExtractor._is_ingredient_line("1 tablespoon olive oil")
    assert IngredientsExtractor._is_ingredient_line("½ teaspoon salt")
    assert IngredientsExtractor._is_ingredient_line("3 large eggs, beaten")

    # Should not match lines without measurements
    assert not IngredientsExtractor._is_ingredient_line("Salt and pepper to taste")

    # Should not match instruction lines (start with verbs)
    assert not IngredientsExtractor._is_ingredient_line("Add 2 cups of flour to the bowl")
    assert not IngredientsExtractor._is_ingredient_line("Mix 1 tablespoon sugar with water")

    # Should not match overly long lines
    long_instruction = "Place the dough in a large bowl with 2 cups flour and let it rise in a warm place for about 2 hours until doubled in size, covering with plastic wrap"
    assert not IngredientsExtractor._is_ingredient_line(long_instruction)


def test_is_instruction_line():
    """Test instruction line detection."""
    assert IngredientsExtractor._is_instruction_line("Preheat the oven to 350°F")
    assert IngredientsExtractor._is_instruction_line("Mix all ingredients together")
    assert IngredientsExtractor._is_instruction_line("Add the flour to the bowl")
    assert IngredientsExtractor._is_instruction_line("Heat the oil in a large skillet")

    # Long lines are likely instructions
    assert IngredientsExtractor._is_instruction_line(
        "Remove the phyllo dough from the package and cover it with a slightly damp cloth to prevent it from drying out"
    )

    # Should not match ingredient lines
    assert not IngredientsExtractor._is_instruction_line("2 cups flour")


def test_extract_ingredients_mixed_sections():
    """Test extraction with multiple ingredient sections interleaved."""
    text = """
    Grilled Chicken with Salad

    For the Chicken
    2 pounds chicken breast
    1 tablespoon olive oil
    1 teaspoon salt

    For the Salad
    4 cups mixed greens
    1 cup cherry tomatoes
    ½ cup sliced cucumbers

    For the Dressing
    ¼ cup olive oil
    2 tablespoons vinegar
    1 teaspoon honey

    Grill the chicken for 6-8 minutes per side.
    Toss the salad ingredients together.
    """
    soup = BeautifulSoup("<div></div>", "html.parser")

    extraction_result = IngredientsExtractor.extract(soup, text)
    result, metadata = normalize_extraction_result(extraction_result)
    assert result is not None
    assert "For the Chicken" in result
    assert "For the Salad" in result
    assert "For the Dressing" in result
    assert "chicken breast" in result
    assert "mixed greens" in result
    assert "cherry tomatoes" in result
    assert "vinegar" in result
    # Should not include instructions
    assert "Grill the chicken" not in result
    assert "Toss the salad" not in result


def test_extract_ingredients_stops_at_instructions():
    """Test that ingredient extraction stops when instructions begin."""
    text = """
    Simple Recipe

    For the Mixture
    2 cups flour
    1 cup sugar
    3 eggs

    Preheat oven to 350°F.
    Mix flour and sugar together.
    Add eggs one at a time.
    """
    soup = BeautifulSoup("<div></div>", "html.parser")

    extraction_result = IngredientsExtractor.extract(soup, text)
    result, metadata = normalize_extraction_result(extraction_result)
    assert result is not None
    assert "flour" in result
    assert "sugar" in result
    assert "eggs" in result
    # Should stop before instructions
    assert "Preheat" not in result
    assert "Mix flour" not in result


def test_extract_ingredients_no_false_positives():
    """Test that non-recipe content doesn't extract false ingredients."""
    text = """
    How to Clean Your Griddle

    Clean your griddle while it's hot. Scrape any excess oil or food debris.
    Use a beveled-edge scraper or a razor-blade-type paint scraper.

    Squirt the hot griddle with 1 tablespoon of water, bring to a boil.
    """
    soup = BeautifulSoup("<div></div>", "html.parser")

    result = IngredientsExtractor.extract(soup, text)
    # Should not extract ingredients from cleaning instructions
    # The measurement is part of an instruction, not an ingredient
    assert result is None or "Squirt" not in result
