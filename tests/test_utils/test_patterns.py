"""Tests for pattern matching utilities."""

from epub_recipe_parser.utils.patterns import (
    MEASUREMENT_PATTERN,
    COOKING_VERBS_PATTERN,
    SERVES_PATTERN,
    PREP_TIME_PATTERN,
    COOK_TIME_PATTERN,
    INGREDIENT_KEYWORDS,
    INSTRUCTION_KEYWORDS,
    EXCLUDE_KEYWORDS,
)


def test_measurement_pattern_matches():
    """Test that measurement pattern matches common measurements."""
    text = "2 cups flour, 1 tablespoon sugar, 3 teaspoons salt"
    matches = MEASUREMENT_PATTERN.findall(text)
    assert len(matches) >= 3


def test_measurement_pattern_with_fractions():
    """Test measurement pattern with fractions."""
    text = "1/2 cup milk, 2 1/2 pounds beef"
    matches = MEASUREMENT_PATTERN.findall(text)
    assert len(matches) >= 2


def test_cooking_verbs_pattern():
    """Test cooking verbs pattern."""
    text = "Heat the oil, add onions, stir and cook for 5 minutes, then serve"
    matches = COOKING_VERBS_PATTERN.findall(text)
    assert len(matches) >= 4
    assert "heat" in [m.lower() for m in matches]
    assert "cook" in [m.lower() for m in matches]


def test_serves_pattern():
    """Test serves pattern matching."""
    text1 = "Serves: 4"
    text2 = "Yield: 6-8"
    text3 = "Makes 12 servings"

    assert SERVES_PATTERN.search(text1) is not None
    assert SERVES_PATTERN.search(text2) is not None
    assert SERVES_PATTERN.search(text3) is not None


def test_prep_time_pattern():
    """Test prep time pattern matching."""
    text = "Prep time: 15 minutes"
    match = PREP_TIME_PATTERN.search(text)
    assert match is not None
    assert "15 minutes" in match.group(1)


def test_cook_time_pattern():
    """Test cook time pattern matching."""
    text = "Cook time: 30 minutes"
    match = COOK_TIME_PATTERN.search(text)
    assert match is not None
    assert "30 minutes" in match.group(1)


def test_ingredient_keywords():
    """Test that ingredient keywords list is defined."""
    assert isinstance(INGREDIENT_KEYWORDS, list)
    assert len(INGREDIENT_KEYWORDS) > 0
    assert "ingredient" in INGREDIENT_KEYWORDS


def test_instruction_keywords():
    """Test that instruction keywords list is defined."""
    assert isinstance(INSTRUCTION_KEYWORDS, list)
    assert len(INSTRUCTION_KEYWORDS) > 0
    assert "instruction" in INSTRUCTION_KEYWORDS or "direction" in INSTRUCTION_KEYWORDS


def test_exclude_keywords():
    """Test that exclude keywords list is defined."""
    assert isinstance(EXCLUDE_KEYWORDS, list)
    assert len(EXCLUDE_KEYWORDS) > 0
    assert "introduction" in EXCLUDE_KEYWORDS
    assert "index" in EXCLUDE_KEYWORDS
