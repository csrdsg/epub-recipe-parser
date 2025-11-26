"""Pytest configuration and fixtures."""

import pytest
from epub_recipe_parser.core.models import Recipe, ExtractorConfig


@pytest.fixture
def sample_recipe():
    """Create a sample recipe for testing."""
    return Recipe(
        title="Test Recipe",
        book="Test Cookbook",
        author="Test Author",
        chapter="Chapter 1",
        epub_section="section1.xhtml",
        ingredients="- 2 cups flour\n- 1 cup sugar\n- 3 eggs",
        instructions="1. Mix ingredients\n2. Bake at 350F\n3. Serve warm",
        serves="4-6",
        prep_time="15 minutes",
        cook_time="30 minutes",
        cooking_method="bake",
        protein_type="chicken",
        quality_score=85,
    )


@pytest.fixture
def sample_html_with_recipe():
    """Sample HTML content with a recipe."""
    return b"""
    <html>
        <body>
            <h2>Grilled Chicken</h2>
            <h3>Ingredients</h3>
            <ul>
                <li>2 pounds chicken breast</li>
                <li>1 tablespoon olive oil</li>
                <li>1 teaspoon salt</li>
            </ul>
            <h3>Instructions</h3>
            <ol>
                <li>Heat the grill to medium-high heat</li>
                <li>Season chicken with salt and oil</li>
                <li>Grill for 6-7 minutes per side</li>
                <li>Remove and let rest 5 minutes</li>
            </ol>
            <p>Serves: 4</p>
            <p>Prep time: 10 minutes</p>
            <p>Cook time: 15 minutes</p>
        </body>
    </html>
    """


@pytest.fixture
def sample_html_without_recipe():
    """Sample HTML content without a recipe."""
    return b"""
    <html>
        <body>
            <h2>Introduction</h2>
            <p>This is an introduction to the cookbook.</p>
            <p>Thank you for purchasing this book.</p>
        </body>
    </html>
    """


@pytest.fixture
def extractor_config():
    """Create a default extractor configuration."""
    return ExtractorConfig(
        min_quality_score=20,
        extract_toc=True,
        validate_recipes=True,
        include_raw_content=True,
    )


@pytest.fixture
def temp_db(tmp_path):
    """Create a temporary database path."""
    return tmp_path / "test_recipes.db"
