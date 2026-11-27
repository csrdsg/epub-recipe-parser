"""Tests for recipe database."""

from epub_recipe_parser.core.models import Recipe
from epub_recipe_parser.storage.database import RecipeDatabase


def test_database_init(temp_db):
    """Test database initialization."""
    RecipeDatabase(temp_db)
    assert temp_db.exists()


def test_save_recipes(temp_db, sample_recipe):
    """Test saving recipes to database."""
    db = RecipeDatabase(temp_db)
    saved = db.save_recipes([sample_recipe])
    assert saved == 1


def test_save_multiple_recipes(temp_db):
    """Test saving multiple recipes."""
    db = RecipeDatabase(temp_db)
    recipes = [
        Recipe(title=f"Recipe {i}", book="Test Book", ingredients="test", instructions="test")
        for i in range(5)
    ]
    saved = db.save_recipes(recipes)
    assert saved == 5


def test_query_all_recipes(temp_db, sample_recipe):
    """Test querying all recipes."""
    db = RecipeDatabase(temp_db)
    db.save_recipes([sample_recipe])
    recipes = db.query()
    assert len(recipes) == 1
    assert recipes[0].title == sample_recipe.title


def test_query_with_limit(temp_db):
    """Test querying with result limit."""
    db = RecipeDatabase(temp_db)
    recipes = [Recipe(title=f"Recipe {i}", book="Book") for i in range(10)]
    db.save_recipes(recipes)

    limited = db.query(limit=5)
    assert len(limited) == 5


def test_search_recipes(temp_db):
    """Test searching recipes by text."""
    db = RecipeDatabase(temp_db)
    recipes = [
        Recipe(title="Grilled Chicken", book="Book", ingredients="chicken breast"),
        Recipe(title="Beef Steak", book="Book", ingredients="beef"),
        Recipe(title="Chicken Soup", book="Book", ingredients="chicken thighs"),
    ]
    db.save_recipes(recipes)

    results = db.search("chicken")
    assert len(results) == 2
    assert all(
        "chicken" in r.title.lower() or "chicken" in (r.ingredients or "").lower() for r in results
    )


def test_count_recipes(temp_db):
    """Test counting recipes."""
    db = RecipeDatabase(temp_db)
    recipes = [Recipe(title=f"Recipe {i}", book="Book") for i in range(7)]
    db.save_recipes(recipes)

    count = db.count()
    assert count == 7


def test_count_with_filters(temp_db):
    """Test counting with filters."""
    db = RecipeDatabase(temp_db)
    recipes = [
        Recipe(title="Recipe 1", book="Book A"),
        Recipe(title="Recipe 2", book="Book A"),
        Recipe(title="Recipe 3", book="Book B"),
    ]
    db.save_recipes(recipes)

    count = db.count(filters={"book": "Book A"})
    assert count == 2
