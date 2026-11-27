"""Tests for data models."""

from epub_recipe_parser.core.models import Recipe, ExtractorConfig


def test_recipe_creation():
    """Test creating a Recipe instance."""
    recipe = Recipe(title="Test Recipe", book="Test Book")
    assert recipe.title == "Test Recipe"
    assert recipe.book == "Test Book"
    assert recipe.tags == []


def test_recipe_to_dict(sample_recipe):
    """Test converting recipe to dictionary."""
    recipe_dict = sample_recipe.to_dict()
    assert isinstance(recipe_dict, dict)
    assert recipe_dict["title"] == "Test Recipe"
    assert recipe_dict["book"] == "Test Cookbook"
    assert "ingredients" in recipe_dict
    assert "instructions" in recipe_dict


def test_recipe_optional_fields():
    """Test recipe with optional fields."""
    recipe = Recipe(
        title="Simple Recipe",
        book="Simple Book",
        serves="4",
        prep_time="10 min",
        cook_time="20 min",
    )
    assert recipe.serves == "4"
    assert recipe.prep_time == "10 min"
    assert recipe.cook_time == "20 min"
    assert recipe.author is None


def test_extractor_config_defaults():
    """Test ExtractorConfig default values."""
    config = ExtractorConfig()
    assert config.extract_toc is True
    assert config.validate_recipes is True
    assert config.split_by_headers is True
    assert config.include_raw_content is True


def test_extractor_config_custom():
    """Test ExtractorConfig with custom values."""
    config = ExtractorConfig(extract_toc=False, include_raw_content=False)
    assert config.extract_toc is False
    assert config.include_raw_content is False
